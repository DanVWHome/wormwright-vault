"""Offline FIDO2 hmac-secret enrollment and verified authentication.
No OTP slots, device PINs, or existing credentials are modified.
"""
import os
import sys
import threading
import time
from contextlib import closing, contextmanager
from fido2.client import DefaultClientDataCollector, Fido2Client, UserInteraction
from fido2.ctap2.extensions import HmacSecretExtension, AuthenticationExtensionProcessor
from dataclasses import replace
from fido2.utils import websafe_encode
from fido2.hid import CtapHidDevice
from fido2.server import Fido2Server
from fido2.webauthn import AttestedCredentialData

class PerCredentialHmacSecretExtension(HmacSecretExtension):
    """Use the SDK-selected credential's original raw salt, without PRF hashing."""
    def __init__(self):super().__init__(allow_hmac_secret=True)
    def get_assertion(self, ctap, options, pin_protocol):
        salts=(options.extensions or {}).get('wormwrightRawSalts')
        if salts is None:return super().get_assertion(ctap,options,pin_protocol)
        owner=self
        class Selected(AuthenticationExtensionProcessor):
            processor=None
            def prepare_inputs(self, selected, pin_token):
                salt=salts.get(websafe_encode(selected.id)) if selected else None
                if not isinstance(salt,bytes) or len(salt)!=32:
                    raise ValueError('The connected key does not match this account.')
                chosen=replace(options,extensions={'hmacGetSecret':{'salt1':salt}})
                self.processor=super(PerCredentialHmacSecretExtension,owner).get_assertion(ctap,chosen,pin_protocol)
                if self.processor is None:raise ValueError('Key lacks offline vault support.')
                return self.processor.prepare_inputs(selected,pin_token)
            def prepare_outputs(self,response,pin_token):
                if self.processor is None:raise ValueError('Credential was not selected.')
                return self.processor.prepare_outputs(response,pin_token)
        return Selected()


RP_ID = 'atlas-portable.local'
ORIGIN = 'https://' + RP_ID


class KeyInteraction(UserInteraction):
    def __init__(self, pin, cancelled):
        self.pin = pin
        self.cancelled = cancelled
        self.requested = False

    def prompt_up(self):
        if self.cancelled.is_set():
            raise ValueError('YubiKey request cancelled.')

    def request_pin(self, permissions, rp_id):
        if self.cancelled.is_set():
            return None
        if self.requested:
            raise ValueError('PIN rejected. Check your PIN before trying again; retries are limited by the YubiKey.')
        self.requested = True
        return self.pin

    def request_uv(self, permissions, rp_id):
        return False  # Require a PIN rather than substituting built-in biometrics.


def server():
    instance = Fido2Server({'id': RP_ID, 'name': 'VanWormAI Vault'}, attestation='none',
                           verify_origin=lambda origin: origin == ORIGIN)
    instance.timeout = 60000
    return instance


def open_device():
    devices = list(CtapHidDevice.list_devices())
    if len(devices) != 1:
        for device in devices:
            device.close()
        if not devices:
            if sys.platform == 'win32':
                raise ValueError('No accessible FIDO2 key found. Plug in your YubiKey and use the Windows security-key prompt.')
            raise ValueError('No accessible FIDO2 key found. Plug in your YubiKey. If it is connected, check Linux device permissions; do not run VanWormAI with sudo.')
        raise ValueError('Connect only the YubiKey you want to use, then try again.')
    return devices[0]


def client_for(device, pin, cancelled):
    interaction = KeyInteraction(pin, cancelled)
    client = Fido2Client(device, client_data_collector=DefaultClientDataCollector(ORIGIN),
                         user_interaction=interaction,
                         extensions=[PerCredentialHmacSecretExtension()])
    if 'hmac-secret' not in client.info.extensions:
        raise ValueError('This key does not support offline vault unlocking.')
    if not client.info.options.get('clientPin'):
        raise ValueError('Set a FIDO2 PIN using Yubico Authenticator before enrolling this key. VanWormAI will not set or reset your PIN.')
    return client, interaction


class WindowsCancellation:
    """Keep native WebAuthn completion separate from user cancellation."""
    def __init__(self, cancelled):
        self.cancelled = cancelled
        self.completed = threading.Event()

    def set(self):
        self.completed.set()

    def wait(self, timeout=None):
        deadline = None if timeout is None else time.monotonic() + timeout
        while not self.cancelled.is_set() and not self.completed.is_set():
            if deadline is not None and time.monotonic() >= deadline:
                return False
            self.completed.wait(.05)
        return True


class NativeWindowsClient:
    def __init__(self, client):
        self.client = client

    def make_credential(self, options, event):
        native_event = WindowsCancellation(event)
        try:
            return self.client.make_credential(options, event=native_event)
        finally:
            native_event.set()

    def get_assertion(self, options, event):
        native_event = WindowsCancellation(event)
        try:
            if options.get("extensions",{}).get("wormwrightRawSalts"):
                from yubikey_windows import get_assertion
                return get_assertion(self.client,options,native_event)
            return self.client.get_assertion(options, event=native_event)
        finally:
            native_event.set()


@contextmanager
def client_session(pin, cancelled):
    if sys.platform == 'win32':
        from fido2.client.windows import WindowsClient
        if not WindowsClient.is_available():
            raise ValueError('Windows security-key support is unavailable. Update Windows or use your vault password.')
        # Native WebAuthn handles PIN/touch without administrator access. Use
        # raw hmac-secret salts, retaining compatibility with enrolled keys.
        client = NativeWindowsClient(WindowsClient(DefaultClientDataCollector(ORIGIN), allow_hmac_secret=True))
        yield client, KeyInteraction(None, cancelled)
    else:
        with closing(open_device()) as device:
            yield client_for(device, pin, cancelled)


def authenticate(client, service, credential, salt, cancelled):
    options, state = service.authenticate_begin([credential], user_verification='required')
    options = {**options['publicKey'], 'hints': ['security-key'], 'extensions': {'hmacGetSecret': {'salt1': salt}}}
    assertion = client.get_assertion(options, event=cancelled).get_response(0)
    service.authenticate_complete(state, [credential], assertion)
    output = assertion.client_extension_results.hmac_get_secret
    if output is None or output.output1 is None or len(output.output1) != 32:
        raise ValueError('The key did not return the required offline unlocking secret.')
    return output.output1


def enroll(pin, cancelled):
    with client_session(pin, cancelled) as (client, interaction):
        service = server()
        options, state = service.register_begin(
            {'id': os.urandom(32), 'name': 'VanWormAI vault', 'displayName': 'VanWormAI vault'},
            resident_key_requirement='discouraged', user_verification='required',
            authenticator_attachment='cross-platform')
        options = {**options['publicKey'], 'extensions': {'hmacCreateSecret': True}}
        try:
            registration = client.make_credential(options, event=cancelled)
            auth_data = service.register_complete(state, registration)
            if not registration.client_extension_results.get('hmacCreateSecret'):
                raise ValueError('The key did not enable the required offline unlocking feature.')
            credential = auth_data.credential_data
            if credential is None:
                raise ValueError('The key did not create a credential.')
            salt = os.urandom(32)
            # A second verified assertion checks that the new credential works.
            # The PIN may be requested once again for this distinct operation.
            interaction.requested = False
            response = authenticate(client, service, credential, salt, cancelled)
            return bytes(credential), salt, response
        finally:
            interaction.pin = None


def unlock(settings, pin, cancelled):
    credential = AttestedCredentialData(settings['credential'])
    with client_session(pin, cancelled) as (client, interaction):
        try:
            return authenticate(client, server(), credential, settings['salt'], cancelled)
        finally:
            interaction.pin = None


def authenticate_any(client, service, settings, cancelled):
    if not 1 <= len(settings) <= 4:raise ValueError('Enroll between one and four keys for this account.')
    credentials=[AttestedCredentialData(s['credential']) for s in settings]
    ids=[c.credential_id for c in credentials]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate credential enrollment.')
    if any(len(s['salt'])!=32 for s in settings):raise ValueError('Invalid key salt.')
    options,state=service.authenticate_begin(credentials,user_verification='required')
    request={**options['publicKey'],'hints':['security-key'],'extensions':{
        'wormwrightRawSalts':{websafe_encode(c.credential_id):s['salt'] for c,s in zip(credentials,settings)}}}
    assertion=client.get_assertion(request,event=cancelled).get_response(0)
    service.authenticate_complete(state,credentials,assertion)
    selected=next((s for c,s in zip(credentials,settings) if c.credential_id==assertion.raw_id),None)
    output=assertion.client_extension_results.hmac_get_secret
    if selected is None or output is None or output.output1 is None or len(output.output1)!=32:
        raise ValueError('The key did not return a valid enrolled credential and unlocking secret.')
    return selected,output.output1


def unlock_any(settings, pin, cancelled):
    with client_session(pin,cancelled) as (client,interaction):
        try:return authenticate_any(client,server(),settings,cancelled)
        except Exception as error:
            message=pin_failure_message(error)
            if message:raise ValueError(message) from error
            raise
        finally:interaction.pin=None


def pin_failure_message(error):
    from fido2.ctap import CtapError
    seen=set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error,CtapError):
            if error.code==CtapError.ERR.PIN_INVALID:return 'The YubiKey PIN was rejected. This attempt stopped without an automatic retry. Check the PIN before trying again.'
            if error.code==CtapError.ERR.PIN_BLOCKED:return 'The key FIDO2 PIN is blocked. Stop trying PINs and use another enrolled key or your vault password.'
            if error.code==CtapError.ERR.PIN_AUTH_BLOCKED:return 'The key has temporarily blocked PIN authentication. Remove and reconnect it before using a known correct PIN.'
        error=getattr(error,'cause',None) or getattr(error,'__cause__',None)
    return None

"""Offline FIDO2 hmac-secret enrollment and verified authentication.
No OTP slots, device PINs, or existing credentials are modified.
"""
import os
from contextlib import closing
from fido2.client import DefaultClientDataCollector, Fido2Client, UserInteraction
from fido2.ctap2.extensions import HmacSecretExtension
from fido2.hid import CtapHidDevice
from fido2.server import Fido2Server
from fido2.webauthn import AttestedCredentialData

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
            raise ValueError('No accessible FIDO2 key found. Plug in your YubiKey. If it is connected, check Linux device permissions; do not run VanWormAI with sudo.')
        raise ValueError('Connect only the YubiKey you want to use, then try again.')
    return devices[0]


def client_for(device, pin, cancelled):
    interaction = KeyInteraction(pin, cancelled)
    client = Fido2Client(device, client_data_collector=DefaultClientDataCollector(ORIGIN),
                         user_interaction=interaction,
                         extensions=[HmacSecretExtension(allow_hmac_secret=True)])
    if 'hmac-secret' not in client.info.extensions:
        raise ValueError('This key does not support offline vault unlocking.')
    if not client.info.options.get('clientPin'):
        raise ValueError('Set a FIDO2 PIN using Yubico Authenticator before enrolling this key. VanWormAI will not set or reset your PIN.')
    return client, interaction


def authenticate(client, service, credential, salt, cancelled):
    options, state = service.authenticate_begin([credential], user_verification='required')
    options = {**options['publicKey'], 'extensions': {'hmacGetSecret': {'salt1': salt}}}
    assertion = client.get_assertion(options, event=cancelled).get_response(0)
    service.authenticate_complete(state, [credential], assertion)
    output = assertion.client_extension_results.hmac_get_secret
    if output is None or output.output1 is None or len(output.output1) != 32:
        raise ValueError('The key did not return the required offline unlocking secret.')
    return output.output1


def enroll(pin, cancelled):
    with closing(open_device()) as device:
        client, interaction = client_for(device, pin, cancelled)
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
    with closing(open_device()) as device:
        client, interaction = client_for(device, pin, cancelled)
        try:
            return authenticate(client, server(), credential, settings['salt'], cancelled)
        finally:
            interaction.pin = None

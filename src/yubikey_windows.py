"""Native Windows assertion with per-credential RAW hmac-secret salts.
Uses python-fido2's WebAuthn API bindings, avoiding direct HID/admin access.
Windows installers are built/tested separately from the Mint release.
"""
def get_assertion(client, request, event):
    import ctypes
    from fido2.client import windows as w
    from fido2.client import win_api as api
    from fido2.ctap2.extensions import HMACGetSecretOutput
    from fido2.utils import websafe_decode
    from fido2.webauthn import PublicKeyCredentialRequestOptions, AuthenticatorData
    from fido2.ctap2 import AssertionResponse
    options=PublicKeyCredentialRequestOptions.from_dict(request)
    data,rp=client._client_data_collector.collect_client_data(options)
    salts=options.extensions['wormwrightRawSalts']
    values=api.WebAuthNHmacSecretSaltValues(None,[api.WebAuthNCredWithHmacSecretSalt(websafe_decode(identifier),api.WebAuthNHmacSecretSalt(salt,None)) for identifier,salt in salts.items()])
    timer=w.CancelThread(event) if event else None
    if timer:timer.start()
    pointer=ctypes.POINTER(api.WebAuthNAssertion)()
    try:
        native=api.WebAuthNGetAssertionOptions(options.timeout or 60000,
            api.WebAuthNAuthenticatorAttachment.CROSS_PLATFORM,
            api.WebAuthNUserVerificationRequirement.REQUIRED,
            w._cbor_list(options.allow_credentials),timer.guid if timer else None,
            api.WebAuthNLargeBlobOperation.NONE,None,values,[],0x00100000,None,api.BOOL(False))
        api.WEBAUTHN.WebAuthNAuthenticatorGetAssertion(client.handle,rp,ctypes.byref(api.WebAuthNClientData(data)),ctypes.byref(native),ctypes.byref(pointer))
        obj=pointer.contents
        if obj.dwVersion<3 or not obj.pHmacSecret:raise ValueError('Windows did not return the required key secret.')
        secret=obj.pHmacSecret.contents.first
        if len(secret)!=32:raise ValueError('Invalid Windows key response.')
        response=AssertionResponse(credential={'type':obj.Credential.pwszCredentialType,'id':obj.Credential.id},auth_data=AuthenticatorData(obj.auth_data),signature=obj.signature,user={'id':obj.user_id} if obj.user_id else None)
        return w.AssertionSelection(data,[response],{'hmacGetSecret':HMACGetSecretOutput(output1=secret)})
    finally:
        if timer:timer.complete()

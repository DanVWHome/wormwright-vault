from pathlib import Path
SOURCE = Path(__file__).resolve().parents[2] / 'src'
import sys,os,threading
from types import SimpleNamespace
sys.path.insert(0, str(SOURCE))
from yubikey_auth import authenticate,server,ORIGIN,KeyInteraction
from fido2.webauthn import (AttestedCredentialData,AuthenticatorData,CollectedClientData,AuthenticationResponse,AuthenticatorAssertionResponse,AuthenticationExtensionsClientOutputs)
from fido2.cose import ES256
from fido2.ctap2.extensions import HMACGetSecretOutput
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
private=ec.generate_private_key(ec.SECP256R1())
credential=AttestedCredentialData.create(b'\0'*16,os.urandom(32),ES256.from_cryptography_key(private.public_key()))
secret=os.urandom(32)
class Client:
 def __init__(self,flags=5,bad_signature=False): self.flags=flags;self.bad_signature=bad_signature
 def get_assertion(self,options,event):
  assert options['userVerification']=='required'
  data=CollectedClientData.create('webauthn.get',options['challenge'],ORIGIN)
  auth=AuthenticatorData.create(server().rp.id_hash,self.flags,1)
  signature=private.sign(auth+data.hash,ec.ECDSA(hashes.SHA256()))
  if self.bad_signature: signature=b'bad signature'
  response=AuthenticationResponse(raw_id=credential.credential_id,response=AuthenticatorAssertionResponse(client_data=data,authenticator_data=auth,signature=signature),client_extension_results=AuthenticationExtensionsClientOutputs({'hmacGetSecret':HMACGetSecretOutput(output1=secret)}))
  return SimpleNamespace(get_response=lambda index:response)
assert authenticate(Client(),server(),credential,os.urandom(32),threading.Event())==secret
for client in [Client(flags=1),Client(flags=4),Client(bad_signature=True)]:
 try:authenticate(client,server(),credential,os.urandom(32),threading.Event());raise AssertionError('unverified assertion accepted')
 except ValueError:pass
interaction=KeyInteraction('dummy-pin',threading.Event())
assert interaction.request_pin(None,None)=='dummy-pin'
try:interaction.request_pin(None,None);raise AssertionError('automatic PIN retry allowed')
except ValueError:pass
print('PASS: signed FIDO2 assertion, required PIN verification and touch flags, tampered-signature rejection, bounded PIN retry')

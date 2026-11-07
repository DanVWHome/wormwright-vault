import os,sys,pathlib,hashlib,threading,unittest
from unittest.mock import patch,Mock
from types import SimpleNamespace
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from fido2.cose import ES256
from fido2.webauthn import AttestedCredentialData,CollectedClientData,AuthenticatorData,PublicKeyCredentialRequestOptions
from fido2.ctap2 import AssertionResponse
from fido2.ctap2.extensions import HMACGetSecretOutput
from fido2.client import AssertionSelection
from fido2.utils import websafe_encode
import yubikey_auth as auth
class AutoKeyTests(unittest.TestCase):
 def setUp(self):
  self.private=[ec.generate_private_key(ec.SECP256R1()) for _ in range(4)]
  self.credentials=[AttestedCredentialData.create(b'\0'*16,os.urandom(32),ES256.from_cryptography_key(k.public_key())) for k in self.private]
  self.keys=[dict(id=str(i),label='Key '+str(i),credential=bytes(c),salt=os.urandom(32)) for i,c in enumerate(self.credentials)]
 def client(self,index,flags=5,wrong_id=False,tamper=False):
  def assertion(request,event):
   options=PublicKeyCredentialRequestOptions.from_dict(request)
   self.assertEqual([x.id for x in options.allow_credentials],[c.credential_id for c in self.credentials])
   self.assertEqual(options.extensions['wormwrightRawSalts'][websafe_encode(self.credentials[index].credential_id)],self.keys[index]['salt'])
   data=CollectedClientData.create('webauthn.get',options.challenge,auth.ORIGIN)
   signed=AuthenticatorData(hashlib.sha256(auth.RP_ID.encode()).digest()+bytes([flags])+b'\0\0\0\1')
   signature=self.private[index].sign(bytes(signed)+data.hash,ec.ECDSA(hashes.SHA256()))
   if tamper:signature=signature[:-1]+bytes([signature[-1]^1])
   response=AssertionResponse(credential={'type':'public-key','id':os.urandom(32) if wrong_id else self.credentials[index].credential_id},auth_data=signed,signature=signature)
   return AssertionSelection(data,[response],{'hmacGetSecret':HMACGetSecretOutput(output1=b'x'*32)})
  return Mock(get_assertion=Mock(side_effect=assertion))
 def test_every_key_is_matched_with_one_public_assertion_call(self):
  for i in range(4):
   client=self.client(i);selected,value=auth.authenticate_any(client,auth.server(),self.keys,threading.Event())
   self.assertEqual(selected,self.keys[i]);self.assertEqual(value,b'x'*32);client.get_assertion.assert_called_once()
 def test_unknown_id_and_invalid_signature_and_missing_uv_fail(self):
  for args in [dict(wrong_id=True),dict(tamper=True),dict(flags=1)]:
   client=self.client(2,**args)
   with self.assertRaises(Exception):auth.authenticate_any(client,auth.server(),self.keys,threading.Event())
   client.get_assertion.assert_called_once()
 def test_duplicate_credentials_rejected_before_contacting_key(self):
  client=self.client(0)
  with self.assertRaises(ValueError):auth.authenticate_any(client,auth.server(),[self.keys[0]]*2,threading.Event())
  client.get_assertion.assert_not_called()
 def test_pin_failure_is_clear_and_does_not_retry(self):
  from fido2.ctap import CtapError
  from fido2.client import ClientError
  failure=ClientError(ClientError.ERR.BAD_REQUEST,CtapError(CtapError.ERR.PIN_INVALID))
  self.assertIn('PIN was rejected',auth.pin_failure_message(failure))
  self.assertIn('without an automatic retry',auth.pin_failure_message(failure))
 def test_extension_uses_selected_raw_salt_without_prf_hash(self):
  options=PublicKeyCredentialRequestOptions.from_dict({'challenge':os.urandom(32),'rpId':auth.RP_ID,'allowCredentials':[{'type':'public-key','id':c.credential_id} for c in self.credentials],'extensions':{'wormwrightRawSalts':{websafe_encode(c.credential_id):k['salt'] for c,k in zip(self.credentials,self.keys)}}})
  inner=Mock();inner.prepare_inputs.return_value={'hmac-secret':'synthetic'}
  with patch('fido2.ctap2.extensions.HmacSecretExtension.get_assertion',return_value=inner) as parent:
   processor=auth.PerCredentialHmacSecretExtension().get_assertion(Mock(),options,Mock())
   processor.prepare_inputs(options.allow_credentials[2],b'token')
   chosen=parent.call_args.args[1];self.assertEqual(chosen.extensions['hmacGetSecret']['salt1'],self.keys[2]['salt'])
   processor.prepare_outputs('response',b'token');inner.prepare_outputs.assert_called_once()
   with self.assertRaises(ValueError):processor.prepare_inputs(None,b'token')
if __name__=='__main__':unittest.main()

package ai.wormwright.notes.hardware;

import com.yubico.yubikit.core.util.Pair;
import com.yubico.yubikit.fido.client.extensions.Extension;
import com.yubico.yubikit.fido.ctap.*;
import com.yubico.yubikit.fido.webauthn.*;
import java.nio.ByteBuffer;
import java.util.*;

/** Raw CTAP hmac-secret salts, matching python-fido2 allow_hmac_secret=True.
 * Deliberately does NOT apply the WebAuthn PRF domain-prefix hash to raw salts.
 * Uses YubiKit's PIN-protocol ECDH/encryption/MAC implementations, not custom crypto. */
public final class RawHmacSecretExtension extends Extension {
    public RawHmacSecretExtension(){super("hmac-secret");}
    @Override public RegistrationProcessor makeCredential(Ctap2Session session,PublicKeyCredentialCreationOptions options,PinUvAuthProtocol protocol){
        if(!isSupported(session)||options.getExtensions()==null||!Boolean.TRUE.equals(options.getExtensions().get("hmacCreateSecret")))return null;
        return new RegistrationProcessor(token->Collections.singletonMap(name,true),(attestation,token)->type->{
            Map<String,?> ext=attestation.getAuthenticatorData().getExtensions();
            return Collections.singletonMap("hmacCreateSecret",ext!=null&&Boolean.TRUE.equals(ext.get(name)));
        });
    }
    @Override public AuthenticationProcessor getAssertion(Ctap2Session session,PublicKeyCredentialRequestOptions options,PinUvAuthProtocol protocol){
        if(!isSupported(session)||options.getExtensions()==null)return null;
        @SuppressWarnings("unchecked") Map<String,Object> ext=(Map<String,Object>)options.getExtensions().get("hmacGetSecret");
        if(ext==null)return null;
        @SuppressWarnings("unchecked") Map<String,?> salts=(Map<String,?>)ext.get("saltByCredential");
        byte[] fixed=salts==null?com.yubico.yubikit.core.internal.codec.Base64.fromUrlSafeString((String)ext.get("salt1")):null;
        if(fixed!=null&&fixed.length!=32)throw new IllegalArgumentException("Expected raw 32-byte salt");
        final Pair<Map<Integer,?>,byte[]> agreement;
        try{agreement=new ClientPin(session,protocol).getSharedSecret();}catch(Exception e){throw new IllegalStateException("Key agreement failed");}
        return new AuthenticationProcessor((selected,token)->{
            byte[] salt=salts==null?fixed:CredentialSaltSelector.select(salts,selected==null?null:selected.getId());
            byte[] enc=protocol.encrypt(agreement.second,salt);
            Map<Integer,Object> input=new HashMap<>();input.put(1,agreement.first);input.put(2,enc);input.put(3,protocol.authenticate(agreement.second,enc));input.put(4,protocol.getVersion());
            return Collections.singletonMap(name,input);
        },(assertion,token)->{
            Map<String,?> outputs=AuthenticatorData.parseFrom(ByteBuffer.wrap(assertion.getAuthenticatorData())).getExtensions();
            if(outputs==null || !(outputs.get(name) instanceof byte[]))throw new IllegalStateException("Missing hmac-secret output");
            byte[] secret=protocol.decrypt(agreement.second,(byte[])outputs.get(name));
            Arrays.fill(agreement.second,(byte)0);
            if(secret.length!=32)throw new IllegalStateException("Invalid hmac-secret output length");
            return type->Collections.singletonMap("hmacGetSecret",Collections.singletonMap("output1",type==SerializationType.CBOR?secret:com.yubico.yubikit.core.internal.codec.Base64.toUrlSafeString(secret)));
        });
    }
}

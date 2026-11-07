package ai.wormwright.hardware;
import java.util.*;
/** Select only the original raw salt for the credential chosen by the SDK. */
public final class CredentialSaltSelector {
    public static String id(byte[] id){return Base64.getUrlEncoder().withoutPadding().encodeToString(id);}
    public static byte[] select(Map<String,?> salts,byte[] selectedId){
        Object value=selectedId==null?null:salts.get(id(selectedId));
        if(!(value instanceof String))throw new IllegalArgumentException("Key is not enrolled for this account");
        byte[] salt=Base64.getUrlDecoder().decode((String)value);
        if(salt.length!=32)throw new IllegalArgumentException("Invalid credential salt");
        return salt;
    }
    private CredentialSaltSelector(){}
}

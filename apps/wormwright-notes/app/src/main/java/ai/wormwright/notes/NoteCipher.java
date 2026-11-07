package ai.wormwright.notes;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Authenticated encryption with a separate context for each database row. */
public final class NoteCipher {
    public interface KeySource { SecretKey get() throws Exception; }
    private final KeySource source;
    public NoteCipher(KeySource source) { this.source=source; }
    private static byte[] context(long id) { return ("wormwright-notes-secret-v1:"+id).getBytes(StandardCharsets.UTF_8); }
    public String encrypt(long id,String text) throws Exception {
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE,source.get());cipher.updateAAD(context(id));
        return "v1:"+Base64.getEncoder().encodeToString(cipher.getIV())+":"+Base64.getEncoder().encodeToString(cipher.doFinal(text.getBytes(StandardCharsets.UTF_8)));
    }
    public String decrypt(long id,String envelope) throws Exception {
        String[] parts=envelope.split(":",-1);
        if(parts.length!=3||!"v1".equals(parts[0]))throw new GeneralSecurityException("Invalid secret envelope");
        byte[] iv=Base64.getDecoder().decode(parts[1]);
        if(iv.length!=12)throw new GeneralSecurityException("Invalid secret IV");
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE,source.get(),new GCMParameterSpec(128,iv));cipher.updateAAD(context(id));
        return new String(cipher.doFinal(Base64.getDecoder().decode(parts[2])),StandardCharsets.UTF_8);
    }
}

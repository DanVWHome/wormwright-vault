package ai.wormwright.notes;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.Arrays;
import javax.crypto.Cipher;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;

/** Portable password-protected backup, independent of the phone's Keystore. */
public final class BackupEnvelope {
    private static final byte[] MAGIC="WWNOTES2\n".getBytes(StandardCharsets.US_ASCII);
    private static final int ITERATIONS=600000, HEADER=MAGIC.length+4+16+12;
    public static boolean isEncrypted(byte[] bytes){
        return bytes.length>=MAGIC.length&&Arrays.equals(MAGIC,Arrays.copyOf(bytes,MAGIC.length));
    }
    private static SecretKeySpec key(char[] password,byte[] salt,int iterations)throws Exception{
        PBEKeySpec spec=new PBEKeySpec(password,salt,iterations,256);
        byte[] bytes=null;
        try{bytes=SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded();return new SecretKeySpec(bytes,"AES");}
        finally{spec.clearPassword();if(bytes!=null)Arrays.fill(bytes,(byte)0);}
    }
    public static byte[] encrypt(byte[] plaintext,char[] password)throws Exception{
        if(password.length<12)throw new GeneralSecurityException("Use at least 12 characters");
        byte[] salt=new byte[16],iv=new byte[12];SecureRandom random=new SecureRandom();random.nextBytes(salt);random.nextBytes(iv);
        byte[] header=ByteBuffer.allocate(HEADER).put(MAGIC).putInt(ITERATIONS).put(salt).put(iv).array();
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key(password,salt,ITERATIONS),new GCMParameterSpec(128,iv));cipher.updateAAD(header);
        byte[] encrypted=cipher.doFinal(plaintext);return ByteBuffer.allocate(header.length+encrypted.length).put(header).put(encrypted).array();
    }
    public static byte[] decrypt(byte[] envelope,char[] password)throws Exception{
        if(!isEncrypted(envelope)||envelope.length<HEADER+16)throw new GeneralSecurityException("Invalid backup envelope");
        ByteBuffer b=ByteBuffer.wrap(envelope);b.position(MAGIC.length);int iterations=b.getInt();
        if(iterations!=ITERATIONS)throw new GeneralSecurityException("Unsupported backup parameters");
        byte[] salt=new byte[16],iv=new byte[12];b.get(salt);b.get(iv);
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,key(password,salt,iterations),new GCMParameterSpec(128,iv));
        cipher.updateAAD(Arrays.copyOf(envelope,HEADER));return cipher.doFinal(envelope,HEADER,envelope.length-HEADER);
    }
}

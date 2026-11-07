package ai.wormwright.notes;

import org.junit.Test;
import static org.junit.Assert.*;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public class CryptoTest {
    interface Checked {void run()throws Exception;}
    void rejects(Checked code)throws Exception{try{code.run();fail("Invalid encrypted content accepted");}catch(java.security.GeneralSecurityException|IllegalArgumentException expected){}}
    SecretKey key()throws Exception{KeyGenerator g=KeyGenerator.getInstance("AES");g.init(256);return g.generateKey();}
    @Test public void noteContentEncryptedAndBoundToItsRow()throws Exception{
        SecretKey key=key();NoteCipher c=new NoteCipher(()->key);String text="private title / milk and oranges ✓";
        String sealed=c.encrypt(7,text);assertFalse(sealed.contains("oranges"));assertEquals(text,c.decrypt(7,sealed));
        assertNotEquals(sealed,c.encrypt(7,text));rejects(()->c.decrypt(8,sealed));
        NoteCipher other=new NoteCipher(this::key);rejects(()->other.decrypt(7,sealed));
        String[] parts=sealed.split(":");byte[] bytes=java.util.Base64.getDecoder().decode(parts[2]);bytes[0]^=1;
        rejects(()->c.decrypt(7,parts[0]+":"+parts[1]+":"+java.util.Base64.getEncoder().encodeToString(bytes)));
    }
    @Test public void portableBackupNeedsPasswordAndAuthenticatesHeaderAndBody()throws Exception{
        byte[] plain="{private checklist: apples and pears}".getBytes(StandardCharsets.UTF_8);char[] password="A separate backup password!".toCharArray();
        byte[] envelope=BackupEnvelope.encrypt(plain,password);assertTrue(BackupEnvelope.isEncrypted(envelope));
        assertArrayEquals(plain,BackupEnvelope.decrypt(envelope,password));assertFalse(new String(envelope,StandardCharsets.UTF_8).contains("apples"));
        assertFalse(Arrays.equals(envelope,BackupEnvelope.encrypt(plain,password)));
        rejects(()->BackupEnvelope.decrypt(envelope,"wrong password".toCharArray()));
        byte[] corrupt=envelope.clone();corrupt[corrupt.length-1]^=1;rejects(()->BackupEnvelope.decrypt(corrupt,password));
        byte[] badHeader=envelope.clone();badHeader[20]^=1;rejects(()->BackupEnvelope.decrypt(badHeader,password));
        byte[] cost=envelope.clone();cost[9]=127;rejects(()->BackupEnvelope.decrypt(cost,password));
        rejects(()->BackupEnvelope.decrypt(Arrays.copyOf(envelope,15),password));
        rejects(()->BackupEnvelope.encrypt(plain,"short".toCharArray()));
    }
}

package ai.wormwright.pocket;
import org.junit.Test;
import static org.junit.Assert.*;
import java.io.*;
import java.util.Arrays;
public class NasBackupTest {
 @Test public void safePathsAndRoot() throws Exception {assertEquals("",NasBackup.folder(""));assertEquals("Backups\\Pocket",NasBackup.folder("Backups/Pocket"));}
 @Test public void unsafePaths() {for(String path:new String[]{"../Vault","Vault/../Other","/Vault","Vault/","C:/Vault"})assertThrows(IOException.class,()->NasBackup.folder(path));}
 @Test public void acceptsTheSameAddressFieldsAsNotes() throws Exception {for(String host:new String[]{"192.168.1.144","192.168.0.1","nas.local","fd00::144"})NasBackup.validate(new org.json.JSONObject().put("host",host).put("share","share").put("folder","PasswordVault/Dans-Vault").put("user","fixture"));}
 @Test public void safeErrorsIdentifyStageWithoutLeakingServerText(){Exception server=new IOException("SecretPassword@NAS");for(NasBackup.Stage stage:NasBackup.Stage.values()){NasBackup.Failure f=new NasBackup.Failure(stage,server);assertEquals(stage,f.stage);assertFalse(f.getMessage().contains("SecretPassword"));assertFalse(f.getMessage().contains("@NAS"));}assertTrue(NasBackup.message(NasBackup.Stage.LOGIN).contains("login"));assertTrue(NasBackup.message(NasBackup.Stage.SHARE).contains("share"));}
 @Test public void readbackDetectsCorruption() throws Exception {byte[] data=new byte[25000];for(int i=0;i<data.length;i++)data[i]=(byte)(i%251);NasBackup.verify(new ByteArrayInputStream(data),data);assertThrows(IOException.class,()->NasBackup.verify(new ByteArrayInputStream(Arrays.copyOf(data,24999)),data));assertThrows(IOException.class,()->NasBackup.verify(new ByteArrayInputStream(Arrays.copyOf(data,25001)),data));byte[] damaged=data.clone();damaged[17000]^=1;assertThrows(IOException.class,()->NasBackup.verify(new ByteArrayInputStream(damaged),data));}
}

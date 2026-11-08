package ai.wormwright.pocket;
import org.junit.Test;
import static org.junit.Assert.*;
import java.io.*;
import java.util.Arrays;
public class NasBackupTest {
 @Test public void safePathsAndRoot() throws Exception {assertEquals("",NasBackup.folder(""));assertEquals("Backups\\Pocket",NasBackup.folder("Backups/Pocket"));}
 @Test public void unsafePaths() {for(String path:new String[]{"../Vault","Vault/../Other","/Vault","Vault/","C:/Vault","a//b","a/./b","a?b","a\u0000b","a.","a "})assertThrows(IOException.class,()->NasBackup.folder(path));}
 @Test public void readbackDetectsCorruption() throws Exception {byte[] data=new byte[25000];for(int i=0;i<data.length;i++)data[i]=(byte)(i%251);NasBackup.verify(new ByteArrayInputStream(data),data);assertThrows(IOException.class,()->NasBackup.verify(new ByteArrayInputStream(Arrays.copyOf(data,24999)),data));assertThrows(IOException.class,()->NasBackup.verify(new ByteArrayInputStream(Arrays.copyOf(data,25001)),data));byte[] damaged=data.clone();damaged[17000]^=1;assertThrows(IOException.class,()->NasBackup.verify(new ByteArrayInputStream(damaged),data));}
}

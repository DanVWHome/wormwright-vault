package ai.wormwright.notes;
import java.io.*;
import java.util.Arrays;
public final class NasBackupTest {
    interface Checked { void run() throws Exception; }
    static int checks=0;
    static void fails(Checked action)throws Exception{try{action.run();}catch(IOException expected){checks++;return;}throw new AssertionError("Unsafe input accepted");}
    public static void main(String[] args)throws Exception{
        if(!NasBackup.folder("PasswordVault/Dans-Vault").equals("PasswordVault\\Dans-Vault"))throw new AssertionError();checks++;
        for(String path:new String[]{"../Vault","Vault/../Other","/Vault","Vault/","C:/Vault"})fails(()->NasBackup.folder(path));
        byte[] data=new byte[25000];for(int i=0;i<data.length;i++)data[i]=(byte)(i%251);
        NasBackup.verify(new ByteArrayInputStream(data),data);checks++;
        fails(()->NasBackup.verify(new ByteArrayInputStream(Arrays.copyOf(data,24999)),data));
        fails(()->NasBackup.verify(new ByteArrayInputStream(Arrays.copyOf(data,25001)),data));
        byte[] corrupt=data.clone();corrupt[17000]^=1;fails(()->NasBackup.verify(new ByteArrayInputStream(corrupt),data));
        System.out.println(checks+" NAS path and backup integrity checks passed");
    }
}

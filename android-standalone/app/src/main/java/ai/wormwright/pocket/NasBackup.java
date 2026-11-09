package ai.wormwright.pocket;

import com.hierynomus.msdtyp.AccessMask;
import com.hierynomus.msfscc.FileAttributes;
import com.hierynomus.mssmb2.*;
import com.hierynomus.smbj.*;
import com.hierynomus.smbj.auth.AuthenticationContext;
import com.hierynomus.smbj.connection.Connection;
import com.hierynomus.smbj.session.Session;
import com.hierynomus.smbj.share.DiskShare;
import org.json.JSONObject;
import java.io.*;
import java.util.*;
import java.util.concurrent.TimeUnit;

/** Explicit, verified snapshots; uploads only an already encrypted portable export. */
public final class NasBackup {
    static String folder(String input) throws IOException {
        String f=input.replace('/', '\\');
        if(f.startsWith("\\")||f.endsWith("\\")||Arrays.asList(f.split("\\\\",-1)).contains("..")||f.indexOf(':')>=0)throw new IOException("Invalid folder");
        return f;
    }
    static void verify(InputStream in, byte[] snapshot) throws IOException {
        int offset=0,n;byte[] buffer=new byte[8192];
        while((n=in.read(buffer))!=-1){
            if(offset+n>snapshot.length)throw new IOException("Backup verification failed");
            for(int i=0;i<n;i++)if(buffer[i]!=snapshot[offset+i])throw new IOException("Backup verification failed");
            offset+=n;
        }
        if(offset!=snapshot.length)throw new IOException("Incomplete backup");
    }
    static void validate(JSONObject settings) throws Exception {
        for(String key:new String[]{"host","share","user"})if(settings.optString(key).trim().isEmpty())throw new IOException("Enter NAS address, share and username");
        folder(settings.optString("folder"));
    }
    enum Stage { CONNECT, LOGIN, SHARE, FOLDER, WRITE, VERIFY, RENAME, CLEANUP }
    static final class Failure extends IOException {
        final Stage stage;
        Failure(Stage stage,Exception cause){super(message(stage),cause);this.stage=stage;}
    }
    static String message(Stage stage) {
        switch(stage){
            case CONNECT:return "Cannot reach the NAS. Check Pocket’s Network permission, Wi-Fi, VPN rules and NAS IP address.";
            case LOGIN:return "The NAS rejected the login. Re-enter the NAS username, password and optional domain in NAS backup settings.";
            case SHARE:return "Cannot open the NAS share. Check NAS shared folder name and this NAS account’s access to that share.";
            case FOLDER:return "Cannot open Subfolder path. Check that this folder exists and the NAS account can access it.";
            case WRITE:return "Cannot write the NAS backup file. Check free space and this NAS account’s write permissions.";
            case VERIFY:return "The NAS backup could not be read back and verified. Check read permissions and connection stability.";
            case RENAME:return "Cannot finish the NAS backup. The NAS account needs permission to rename files in the backup folder.";
            default:return "Cannot remove the connection-test file. Check delete permissions in the backup folder.";
        }
    }
    public static String upload(JSONObject settings,byte[] snapshot) throws Exception {return transfer(settings,snapshot,false);}
    public static String test(JSONObject settings) throws Exception {
        byte[] probe=new byte[64];new java.security.SecureRandom().nextBytes(probe);
        return transfer(settings,probe,true);
    }
    private static String transfer(JSONObject settings,byte[] snapshot,boolean probe) throws Exception {
        validate(settings);
        String folder=folder(settings.getString("folder"));
        String prefix=folder.isEmpty()?"":folder+"\\";
        String name=(probe?"wormwright-pocket-connection-test-":"wormwright-pocket-")+new java.text.SimpleDateFormat("yyyyMMdd-HHmmss",Locale.US).format(new Date())+"-"+UUID.randomUUID().toString()+(probe?".check":".sqlite");
        String temp=prefix+"."+name+".partial",target=prefix+name;
        SmbConfig config=SmbConfig.builder().withSigningRequired(true).withTimeout(15,TimeUnit.SECONDS).withSoTimeout(15,TimeUnit.SECONDS).withBufferSize(65536).build();
        char[] password=settings.getString("password").toCharArray();Stage stage=Stage.CONNECT;
        try(SMBClient client=new SMBClient(config)){
            try(Connection connection=client.connect(settings.getString("host"))){
                stage=Stage.LOGIN;
                try(Session session=connection.authenticate(new AuthenticationContext(settings.getString("user"),password,settings.optString("domain")))){
                    stage=Stage.SHARE;
                    try(DiskShare share=(DiskShare)session.connectShare(settings.getString("share"))){
                        stage=Stage.FOLDER;
                        if(!folder.isEmpty()&&!share.folderExists(folder))throw new IOException("Folder does not exist");
                        try{
                            stage=Stage.WRITE;
                            try(com.hierynomus.smbj.share.File file=share.openFile(temp,EnumSet.of(AccessMask.GENERIC_WRITE,AccessMask.GENERIC_READ,AccessMask.DELETE),EnumSet.of(FileAttributes.FILE_ATTRIBUTE_NORMAL),SMB2ShareAccess.ALL,SMB2CreateDisposition.FILE_CREATE,EnumSet.noneOf(SMB2CreateOptions.class))){
                                try(OutputStream out=file.getOutputStream()){out.write(snapshot);out.flush();}file.flush();
                            }
                            stage=Stage.VERIFY;
                            try(com.hierynomus.smbj.share.File file=share.openFile(temp,EnumSet.of(AccessMask.GENERIC_READ,AccessMask.DELETE),EnumSet.of(FileAttributes.FILE_ATTRIBUTE_NORMAL),SMB2ShareAccess.ALL,SMB2CreateDisposition.FILE_OPEN,EnumSet.noneOf(SMB2CreateOptions.class));InputStream in=file.getInputStream()){
                                verify(in,snapshot);stage=Stage.RENAME;file.rename(target,false);
                            }
                            if(probe){stage=Stage.CLEANUP;share.rm(target);}
                        }finally{if(share.fileExists(temp))share.rm(temp);}
                    }
                }
            }
            return settings.getString("host")+"/"+settings.getString("share")+"/"+target.replace('\\','/');
        }catch(Exception cause){throw new Failure(stage,cause);}
        finally{Arrays.fill(password,'\0');}
    }
}

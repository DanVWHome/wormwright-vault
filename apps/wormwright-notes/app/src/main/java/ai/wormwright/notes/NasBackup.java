package ai.wormwright.notes;

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

/** Explicit, verified snapshots; never opens or modifies the Vault database. */
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
    public static String upload(JSONObject settings,byte[] snapshot) throws Exception {
        String folder=folder(settings.getString("folder"));
        String prefix=folder.isEmpty()?"":folder+"\\";
        String name="wormwright-notes-"+new java.text.SimpleDateFormat("yyyyMMdd-HHmmss",Locale.US).format(new Date())+"-"+UUID.randomUUID().toString().substring(0,8)+".json";
        String temp=prefix+"."+name+".partial", target=prefix+name;
        SmbConfig config=SmbConfig.builder().withSigningRequired(true).withTimeout(15,TimeUnit.SECONDS).withSoTimeout(15,TimeUnit.SECONDS).withBufferSize(65536).build();
        char[] password=settings.getString("password").toCharArray();
        try(SMBClient client=new SMBClient(config);Connection connection=client.connect(settings.getString("host"));Session session=connection.authenticate(new AuthenticationContext(settings.getString("user"),password,settings.optString("domain")));DiskShare share=(DiskShare)session.connectShare(settings.getString("share"))){
            if(!folder.isEmpty()&&!share.folderExists(folder))throw new IOException("Folder does not exist");
            try {
                try(com.hierynomus.smbj.share.File file=share.openFile(temp,EnumSet.of(AccessMask.GENERIC_WRITE,AccessMask.GENERIC_READ,AccessMask.DELETE),EnumSet.of(FileAttributes.FILE_ATTRIBUTE_NORMAL),SMB2ShareAccess.ALL,SMB2CreateDisposition.FILE_CREATE,EnumSet.noneOf(SMB2CreateOptions.class))){
                    try(OutputStream out=file.getOutputStream()){out.write(snapshot);out.flush();}file.flush();
                }
                try(com.hierynomus.smbj.share.File file=share.openFile(temp,EnumSet.of(AccessMask.GENERIC_READ,AccessMask.DELETE),EnumSet.of(FileAttributes.FILE_ATTRIBUTE_NORMAL),SMB2ShareAccess.ALL,SMB2CreateDisposition.FILE_OPEN,EnumSet.noneOf(SMB2CreateOptions.class));InputStream in=file.getInputStream()){
                    verify(in,snapshot);
                    file.rename(target,false);
                }
            }finally{if(share.fileExists(temp))share.rm(temp);}
            return settings.getString("host")+"/"+settings.getString("share")+"/"+target.replace('\\','/');
        }finally{Arrays.fill(password,'\0');}
    }
}

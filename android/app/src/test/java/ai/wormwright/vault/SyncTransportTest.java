package ai.wormwright.vault;
import org.junit.Test;
import static org.junit.Assert.*;
import org.json.JSONObject;
import java.io.*;
import java.nio.file.Files;
import java.util.function.BooleanSupplier;
public class SyncTransportTest {
    static class Remote implements NasClient.SyncRemote {
        boolean released,published,fail,changed; int reads;
        public void acquireLock() {}
        public boolean exists(String suffix) { return false; }
        public InputStream openMaster() { return new ByteArrayInputStream(new byte[]{(byte)(changed && reads++>0?2:1)}); }
        public void releaseLock() { released=true; }
        public void publish(File result,File previous,BooleanSupplier current) throws Exception { if(fail) throw new IOException("interrupted"); published=true; }
    }
    static class Handler implements NasClient.SyncHandler {
        final Remote remote; boolean committed,ready=true;
        Handler(Remote r) {remote=r;}
        public JSONObject prepare(File shared,File result) throws Exception { Files.write(result.toPath(),new byte[]{3}); return new JSONObject().put("ready",ready).put("upload",true); }
        public void checkLocal() {}
        public JSONObject commit() { assertTrue(remote.published); committed=true; return new JSONObject(); }
    }
    void run(Remote remote,Handler handler,BooleanSupplier current) throws Exception {
        File dir=Files.createTempDirectory("sync-test").toFile();
        try { NasClient.syncTransport(remote,dir,handler,current); }
        finally { for(File f:dir.listFiles()) f.delete(); dir.delete(); }
    }
    @Test public void publicationPrecedesPhoneCommit() throws Exception { Remote r=new Remote(); Handler h=new Handler(r); run(r,h,()->true); assertTrue(h.committed && r.released); }
    @Test public void failedUploadNeverCommitsPhone() throws Exception { Remote r=new Remote(); r.fail=true; Handler h=new Handler(r); try {run(r,h,()->true); fail();} catch(IOException expected) {} assertFalse(h.committed); assertTrue(r.released); }
    @Test public void changedNasNeverPublishes() throws Exception { Remote r=new Remote(); r.changed=true; Handler h=new Handler(r); try {run(r,h,()->true); fail();} catch(IOException expected) {} assertFalse(r.published || h.committed); assertTrue(r.released); }
    @Test public void lockingCancelsPublication() throws Exception { Remote r=new Remote(); Handler h=new Handler(r); try {run(r,h,()->false); fail();} catch(IOException expected) {} assertFalse(r.published || h.committed); assertTrue(r.released); }
    @Test public void conflictReviewReleasesLockWithoutCommit() throws Exception { Remote r=new Remote(); Handler h=new Handler(r); h.ready=false; run(r,h,()->true); assertFalse(r.published || h.committed); assertTrue(r.released); }
}

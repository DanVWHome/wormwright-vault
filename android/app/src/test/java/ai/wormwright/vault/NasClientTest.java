package ai.wormwright.vault;

import org.junit.Test;
import static org.junit.Assert.*;
import java.io.*;
import java.nio.file.Files;

public class NasClientTest {
    private static class Remote implements NasClient.Remote {
        boolean busy, journal, acquired, released, opened;
        InputStream content = new ByteArrayInputStream(new byte[]{1,2,3});
        public void acquireLock() throws Exception { if (busy) throw new IOException("busy"); acquired = true; }
        public boolean exists(String suffix) { return journal && "-wal".equals(suffix); }
        public InputStream openMaster() { opened = true; return content; }
        public void releaseLock() { released = true; }
    }
    @Test public void snapshotIsDownloadedUnderOwnedLock() throws Exception {
        Remote remote = new Remote(); File target = File.createTempFile("nas-test", ".sqlite");
        try {
            NasClient.copySnapshot(remote, target);
            assertTrue(remote.acquired && remote.opened && remote.released);
            assertArrayEquals(new byte[]{1,2,3}, Files.readAllBytes(target.toPath()));
        } finally { target.delete(); }
    }
    @Test public void preExistingLockIsNeverRemoved() throws Exception {
        Remote remote = new Remote(); remote.busy = true; File target = File.createTempFile("nas-test", ".sqlite");
        try {
            try { NasClient.copySnapshot(remote, target); fail("Expected busy lock failure"); } catch (IOException expected) {}
            assertFalse(remote.released); assertFalse(remote.opened);
        } finally { target.delete(); }
    }
    @Test public void activeJournalStopsDownloadAndReleasesOurLock() throws Exception {
        Remote remote = new Remote(); remote.journal = true; File target = File.createTempFile("nas-test", ".sqlite");
        try {
            try { NasClient.copySnapshot(remote, target); fail("Expected journal rejection"); } catch (IOException expected) {}
            assertTrue(remote.released); assertFalse(remote.opened);
        } finally { target.delete(); }
    }
    @Test public void interruptedTransferReleasesOurLock() throws Exception {
        Remote remote = new Remote(); remote.content = new InputStream() { public int read() throws IOException { throw new IOException("interrupted"); } };
        File target = File.createTempFile("nas-test", ".sqlite");
        try {
            try { NasClient.copySnapshot(remote, target); fail("Expected transfer failure"); } catch (IOException expected) {}
            assertTrue(remote.released);
        } finally { target.delete(); }
    }
    @Test public void emptyMasterIsRejected() throws Exception {
        Remote remote = new Remote(); remote.content = new ByteArrayInputStream(new byte[0]);
        File target = File.createTempFile("nas-test", ".sqlite");
        try {
            try { NasClient.copySnapshot(remote, target); fail("Expected empty-file rejection"); } catch (IOException expected) {}
            assertTrue(remote.released);
        } finally { target.delete(); }
    }
}

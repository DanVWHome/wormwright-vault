package ai.wormwright.vault;

import com.hierynomus.msdtyp.AccessMask;
import com.hierynomus.msfscc.FileAttributes;
import com.hierynomus.mssmb2.SMB2CreateDisposition;
import com.hierynomus.mssmb2.SMB2CreateOptions;
import com.hierynomus.mssmb2.SMB2ShareAccess;
import com.hierynomus.smbj.SMBClient;
import com.hierynomus.smbj.SmbConfig;
import com.hierynomus.smbj.auth.AuthenticationContext;
import com.hierynomus.smbj.connection.Connection;
import com.hierynomus.smbj.session.Session;
import com.hierynomus.smbj.share.DiskShare;
import com.hierynomus.mssmb2.SMBApiException;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.IOException;
import java.util.Arrays;
import java.util.EnumSet;
import java.util.concurrent.TimeUnit;
import java.io.FileInputStream;
import java.io.FilterInputStream;
import java.io.OutputStream;
import java.security.MessageDigest;
import java.util.UUID;
import java.util.ArrayList;
import java.util.Collections;
import java.util.function.BooleanSupplier;
import com.hierynomus.msfscc.fileinformation.FileIdBothDirectoryInformation;

/** SMB2/3 download with the same lock-directory protocol as Linux. */
public final class NasClient {
    public static final class Failure extends IOException {
        public final String userMessage;
        Failure(String phase, Exception cause) {
            super("NAS " + phase + " failed", cause);
            String message = "NAS connection failed. Check the address and Wi-Fi. Your offline vault is available.";
            if ("login".equals(phase)) message = "NAS login failed. Check the NAS username, password and optional domain.";
            if ("share".equals(phase)) message = "Could not open the NAS share. Check the share name and account permissions.";
            if ("sync".equals(phase)) message = "NAS sync stopped. Phone edits are preserved. Check Wi-Fi, folder permissions and the shared sync lock, then retry.";
            if ("download".equals(phase)) message = "Could not download the shared vault. Check the folder, shared sync lock and NAS permissions.";
            if (cause instanceof SMBApiException) {
                long status = ((SMBApiException)cause).getStatusCode();
                if (status == 0xC0000035L) message = "Another device is syncing, or a previous sync left a lock. Retry after the other sync finishes.";
                if (status == 0xC0000034L || status == 0xC000003AL) message = "NAS folder or wormwright-vault.sqlite was not found. Check the share and folder.";
                if (status == 0xC0000022L) message = "NAS access denied. This account needs to read/write the vault, backups and shared sync lock.";
            }
            userMessage = message;
        }
    }
    public interface Remote {
        void acquireLock() throws Exception;
        boolean exists(String suffix) throws Exception;
        InputStream openMaster() throws Exception;
        void releaseLock() throws Exception;
    }
    public static void copySnapshot(Remote remote, File destination) throws Exception {
        boolean owned = false;
        try {
            remote.acquireLock(); owned = true;
            readSnapshot(remote, destination);
        } finally {
            if (owned) remote.releaseLock();
        }
    }
    private static void readSnapshot(Remote remote, File destination) throws Exception {
            if (remote.exists("-wal") || remote.exists("-journal"))
                throw new IOException("Close the shared database before refreshing.");
            try (InputStream input = remote.openMaster(); FileOutputStream output = new FileOutputStream(destination)) {
                byte[] buffer = new byte[65536]; int count; long size = 0;
                while ((count = input.read(buffer)) != -1) {
                    size += count;
                    if (size > 64L * 1024 * 1024) throw new IOException("The shared vault exceeds the 64 MB preview limit.");
                    output.write(buffer, 0, count);
                }
                if (size == 0) throw new IOException("The shared vault is empty.");
                output.getFD().sync();
            }
    }
    public interface SyncRemote extends Remote {
        void publish(File result, File previous, BooleanSupplier current) throws Exception;
    }
    public interface SyncHandler {
        JSONObject prepare(File remote, File result) throws Exception;
        void checkLocal() throws Exception;
        JSONObject commit() throws Exception;
    }
    public static JSONObject syncTransport(SyncRemote remote, File directory, SyncHandler handler, BooleanSupplier current) throws Exception {
        boolean owned = false;
        File shared = new File(directory, "shared.sqlite"), result = new File(directory, "result.sqlite"), recheck = new File(directory, "recheck.sqlite");
        try {
            remote.acquireLock(); owned = true; readSnapshot(remote, shared);
            JSONObject plan = handler.prepare(shared, result);
            if (!plan.getBoolean("ready")) return plan;
            if (!current.getAsBoolean()) throw new IOException("Sync canceled on lock");
            handler.checkLocal();
            if (plan.getBoolean("upload")) {
                readSnapshot(remote, recheck);
                if (!Arrays.equals(digest(shared), digest(recheck))) throw new IOException("NAS changed during sync");
                remote.publish(result, shared, current);
            }
            // Finish the phone commit after an acknowledged publication, even
            // if the user backgrounds the app at this point. UI remains locked.
            return handler.commit();
        } finally {
            if (owned) remote.releaseLock();
        }
    }
    private static byte[] digest(File path) throws Exception {
        try (InputStream input = new FileInputStream(path)) { return digest(input); }
    }
    private static byte[] digest(InputStream input) throws Exception {
        MessageDigest hash = MessageDigest.getInstance("SHA-256"); byte[] buffer = new byte[65536]; int count;
        while ((count = input.read(buffer)) != -1) hash.update(buffer, 0, count);
        return hash.digest();
    }
    public static JSONObject synchronize(JSONObject settings, File directory, SyncHandler handler, BooleanSupplier current) throws Exception {
        String folder = settings.getString("folder").replace('/', '\\');
        if (folder.startsWith("\\") || folder.endsWith("\\") || Arrays.asList(folder.split("\\\\", -1)).contains(".."))
            throw new IOException("Invalid NAS folder");
        final String prefix = folder.isEmpty() ? "" : folder + "\\", master = prefix + "wormwright-vault.sqlite";
        final String lockPath = prefix + ".wormwright-sync-lock", backups = prefix + ".wormwright-managed-backups";
        SmbConfig config = SmbConfig.builder().withSigningRequired(true).withTimeout(15, TimeUnit.SECONDS)
            .withSoTimeout(15, TimeUnit.SECONDS).withBufferSize(65536).build();
        char[] password = settings.getString("password").toCharArray(); String phase = "connect";
        try (SMBClient client = new SMBClient(config); Connection connection = client.connect(settings.getString("host"))) {
            phase = "login";
            try (Session session = connection.authenticate(new AuthenticationContext(settings.getString("user"), password, settings.optString("domain")))) {
                phase = "share";
                try (DiskShare share = (DiskShare)session.connectShare(settings.getString("share"))) {
                    phase = "sync";
                    return syncTransport(new SyncRemote() {
                        public void acquireLock() { share.mkdir(lockPath); }
                        public boolean exists(String suffix) { return share.fileExists(master + suffix); }
                        private InputStream open(String path) {
                            com.hierynomus.smbj.share.File handle = share.openFile(path, EnumSet.of(AccessMask.GENERIC_READ),
                                EnumSet.of(FileAttributes.FILE_ATTRIBUTE_NORMAL), SMB2ShareAccess.ALL,
                                SMB2CreateDisposition.FILE_OPEN, EnumSet.of(SMB2CreateOptions.FILE_SEQUENTIAL_ONLY));
                            return new FilterInputStream(handle.getInputStream()) {
                                public void close() throws IOException { try { super.close(); } finally { handle.close(); } }
                            };
                        }
                        public InputStream openMaster() { return open(master); }
                        private void writeVerified(File source, String path, boolean replace) throws Exception {
                            try (com.hierynomus.smbj.share.File handle = share.openFile(path,
                                EnumSet.of(AccessMask.GENERIC_READ, AccessMask.GENERIC_WRITE, AccessMask.DELETE),
                                EnumSet.of(FileAttributes.FILE_ATTRIBUTE_NORMAL), SMB2ShareAccess.ALL,
                                SMB2CreateDisposition.FILE_CREATE, EnumSet.noneOf(SMB2CreateOptions.class))) {
                                try (InputStream input = new FileInputStream(source); OutputStream output = handle.getOutputStream()) {
                                    byte[] buffer = new byte[65536]; int count;
                                    while ((count = input.read(buffer)) != -1) output.write(buffer,0,count);
                                    output.flush();
                                }
                                handle.flush();
                                try (InputStream check = open(path)) {
                                    if (!Arrays.equals(digest(source), digest(check))) throw new IOException("Upload verification failed");
                                }
                                if (replace) {
                                    if (!current.getAsBoolean()) throw new IOException("Sync canceled before publication");
                                    handler.checkLocal();
                                    handle.rename(master, true);
                                }
                            }
                        }
                        public void publish(File result, File previous, BooleanSupplier current) throws Exception {
                            if (!share.folderExists(backups)) share.mkdir(backups);
                            String backupPrefix = hex(MessageDigest.getInstance("SHA-256").digest("wormwright-vault.sqlite".getBytes(java.nio.charset.StandardCharsets.UTF_8))).substring(0,16) + "-";
                            String saved = backups + "\\" + backupPrefix + System.currentTimeMillis() + "000000-" + UUID.randomUUID().toString().replace("-", "") + ".sqlite";
                            writeVerified(previous, saved, false);
                            String temporary = prefix + ".wormwright-managed-" + UUID.randomUUID() + ".sqlite";
                            try { writeVerified(result, temporary, true); }
                            finally { if (share.fileExists(temporary)) share.rm(temporary); }
                            // Pruning is best-effort and cannot invalidate an
                            // acknowledged publication or advance local baseline.
                            try {
                                ArrayList<String> old = new ArrayList<>();
                                for (FileIdBothDirectoryInformation entry : share.list(backups)) {
                                    String name = entry.getFileName();
                                    if (name.startsWith(backupPrefix) && name.endsWith(".sqlite")) old.add(name);
                                }
                                Collections.sort(old, Collections.reverseOrder());
                                for (int i=10; i<old.size(); i++) share.rm(backups + "\\" + old.get(i));
                            } catch (Exception ignored) {}
                        }
                        public void releaseLock() { share.rmdir(lockPath, false); }
                    }, directory, handler, current);
                }
            }
        } catch (Exception error) { throw new Failure(phase, error); }
        finally { Arrays.fill(password, '\0'); }
    }
    private static String hex(byte[] value) {
        StringBuilder result = new StringBuilder(); for (byte b : value) result.append(String.format(java.util.Locale.ROOT,"%02x",b & 255));
        return result.toString();
    }
    public static void download(JSONObject settings, File destination) throws Exception {
        String folder = settings.getString("folder").replace('/', '\\');
        if (folder.startsWith("\\") || folder.endsWith("\\") || Arrays.asList(folder.split("\\\\", -1)).contains(".."))
            throw new IOException("Use a folder relative to the share, without .. segments.");
        final String prefix = folder.isEmpty() ? "" : folder + "\\";
        final String master = prefix + "wormwright-vault.sqlite";
        final String lock = prefix + ".wormwright-sync-lock";
        SmbConfig config = SmbConfig.builder().withSigningRequired(true).withTimeout(15, TimeUnit.SECONDS)
                .withSoTimeout(15, TimeUnit.SECONDS).withBufferSize(65536).build();
        char[] password = settings.getString("password").toCharArray();
        String phase = "connect";
        try (SMBClient client = new SMBClient(config); Connection connection = client.connect(settings.getString("host"))) {
            AuthenticationContext auth = new AuthenticationContext(settings.getString("user"), password, settings.optString("domain"));
            phase = "login";
            try (Session session = connection.authenticate(auth)) {
                phase = "share";
                try (DiskShare share = (DiskShare)session.connectShare(settings.getString("share"))) {
                phase = "download";
                copySnapshot(new Remote() {
                    private com.hierynomus.smbj.share.File handle;
                    public void acquireLock() throws Exception { share.mkdir(lock); }
                    public boolean exists(String suffix) { return share.fileExists(master + suffix); }
                    public InputStream openMaster() {
                        handle = share.openFile(master, EnumSet.of(AccessMask.GENERIC_READ),
                            EnumSet.of(FileAttributes.FILE_ATTRIBUTE_NORMAL), EnumSet.of(SMB2ShareAccess.FILE_SHARE_READ),
                            SMB2CreateDisposition.FILE_OPEN, EnumSet.of(SMB2CreateOptions.FILE_SEQUENTIAL_ONLY));
                        return handle.getInputStream();
                    }
                    public void releaseLock() {
                        try { if (handle != null) handle.close(); }
                        finally { share.rmdir(lock, false); }
                    }
                }, destination);
                }
            }
        } catch (Exception error) { throw new Failure(phase, error); }
        finally { Arrays.fill(password, '\0'); }
    }
}

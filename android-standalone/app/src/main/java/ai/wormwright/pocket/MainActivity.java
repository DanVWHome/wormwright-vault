package ai.wormwright.pocket;

import android.app.*;
import android.os.*;
import android.content.*;
import android.hardware.biometrics.BiometricPrompt;
import android.hardware.biometrics.BiometricManager;
import android.view.*;
import android.widget.*;
import android.text.Editable;
import android.text.TextWatcher;
import android.text.InputType;
import android.util.AtomicFile;
import android.util.Base64;
import com.chaquo.python.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.UUID;
import java.util.concurrent.*;
import javax.crypto.Cipher;

public class MainActivity extends Activity {
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final Handler ui = new Handler(Looper.getMainLooper());
    private LinearLayout root, rows;
    private TextView status;
    private boolean unlocked, sample, busy, resumed;
    private volatile int epoch;
    private CancellationSignal auth;
    private AlertDialog dialog;
    private File base, pendingExport;
    private JSONObject active;
    private String ownedClip;
    private final Runnable idle = () -> lock("Locked after two minutes of inactivity.");
    private final Runnable clearClip = this::clearClipboard;
    private interface Job { String run() throws Exception; }
    private interface Done { void accept(String value) throws Exception; }
    private interface PasswordDone { void accept(String value) throws Exception; }
    private interface CryptoDone { void accept(Cipher cipher) throws Exception; }
    private PyObject engine() { return Python.getInstance().getModule("pocket"); }
    private String call(String name, Object... args) { return engine().callAttr(name, args).toString(); }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state); getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        getWindow().setDecorFitsSystemWindows(false);
        base = getNoBackupFilesDir();
        try { active = readActive(); } catch (Exception e) { active = null; }
        home("Phone authentication unlocks this device. A separate backup secret restores exported backups.");
    }
    private JSONObject readActive() throws Exception {
        AtomicFile f = new AtomicFile(new File(base, "active.json"));
        if (!f.getBaseFile().exists()) return null;
        return new JSONObject(new String(f.readFully(), StandardCharsets.UTF_8));
    }
    private void publish(JSONObject state) throws Exception {
        AtomicFile f = new AtomicFile(new File(base, "active.json")); FileOutputStream out = null;
        try { out = f.startWrite(); out.write(state.toString().getBytes(StandardCharsets.UTF_8)); f.finishWrite(out); }
        catch (Exception e) { if (out != null) f.failWrite(out); throw e; }
        active = state;
    }
    private File slotFile(String slot) { return new File(base, "vault-" + slot + ".sqlite"); }
    private byte[] decode(String s) { return Base64.decode(s, Base64.NO_WRAP); }
    private String encode(byte[] b) { return Base64.encodeToString(b, Base64.NO_WRAP); }
    private void task(Job job, Done done) {
        if (busy) { message("Please wait for the current operation."); return; }
        busy = true; final int generation = epoch;
        worker.execute(() -> {
            String result = null, error = null;
            try { if (generation == epoch) result = job.run(); }
            catch (Exception e) { error = safeError(e); }
            final String value = result, problem = error;
            ui.post(() -> {
                busy = false;
                if (generation != epoch || !resumed) return;
                if (problem != null) { message(problem); return; }
                try { done.accept(value); } catch (Exception e) { message(safeError(e)); }
            });
        });
    }
    private String safeError(Exception e) {
        if (e instanceof PyException) {
            String value = e.getMessage();
            if (value != null && value.startsWith("VaultError: ")) return value.substring(12);
            return "Operation failed: incorrect secret or damaged vault. Existing data was kept.";
        }
        return "Operation could not complete. Existing files were kept. Check device screen lock or restore a portable backup.";
    }
    private LinearLayout column() { LinearLayout v = new LinearLayout(this); v.setOrientation(LinearLayout.VERTICAL); return v; }
    private TextView text(String s) { TextView v = new TextView(this); v.setText(s); v.setTextSize(17); v.setPadding(12,12,12,12); v.setTextColor(0xff172d43); return v; }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private void screen(String title) {
        root = column(); root.setPadding(dp(20),dp(16),dp(20),dp(16)); root.setBackgroundColor(0xfffff9ee);
        root.addView(text(title)); status = text(""); root.addView(status);
        ScrollView scroll = new ScrollView(this); scroll.setBackgroundColor(0xfffff9ee);
        // Inset the viewport so scrolling never moves content beneath a camera or system bar.
        scroll.setOnApplyWindowInsetsListener((view, insets) -> {
            android.graphics.Insets safe = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
            android.graphics.Insets keyboard = insets.getInsets(WindowInsets.Type.ime());
            view.setPadding(safe.left, safe.top, safe.right, Math.max(safe.bottom, keyboard.bottom));
            return insets;
        });
        scroll.addView(root); setContentView(scroll); scroll.requestApplyInsets();
    }
    private Button button(LinearLayout parent, String title, Runnable action) {
        Button v = new Button(this); v.setText(title); v.setAllCaps(false); parent.addView(v);
        v.setOnClickListener(w -> { if (!busy) action.run(); else message("Please wait."); });
        return v;
    }
    private void message(String value) { if (status != null) status.setText(value); }
    private void home(String note) {
        screen("Wormwright Pocket"); root.addView(text("Your personal password vault"), 1); message(note);
        boolean stored = new File(base, "active.json").exists();
        if (stored) button(root, "Unlock personal vault", this::unlockPersonal);
        else button(root, "Create personal vault", () -> createOrRestore(null, null));
        button(root, "Open invented sample vault", () -> { sample = true; task(() -> call("sample", new File(base, "sample.sqlite").getPath()), v -> { unlocked = true; vaultScreen(); }); });
        button(root, "Restore portable encrypted backup", this::chooseRestore);
        button(root, "Backup and recovery help", this::help);
    }
    private void authenticate(Cipher cipher, CryptoDone done) {
        KeyguardManager guard = (KeyguardManager)getSystemService(KEYGUARD_SERVICE);
        if (!guard.isDeviceSecure()) { message("Set a secure phone PIN, pattern or password before using your personal vault."); return; }
        if (auth != null) auth.cancel(); auth = new CancellationSignal(); final int generation = epoch;
        new BiometricPrompt.Builder(this).setTitle("Unlock Wormwright Pocket")
            .setSubtitle("Use strong biometrics or your phone screen-lock credential")
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG | BiometricManager.Authenticators.DEVICE_CREDENTIAL)
            .build().authenticate(new BiometricPrompt.CryptoObject(cipher), auth, getMainExecutor(), new BiometricPrompt.AuthenticationCallback() {
                @Override public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult r) {
                    if (generation != epoch || !resumed) return;
                    try { if (r.getCryptoObject() == null || r.getCryptoObject().getCipher() == null) throw new IllegalStateException(); done.accept(r.getCryptoObject().getCipher()); }
                    catch (Exception e) { message(safeError(e)); }
                }
                @Override public void onAuthenticationError(int code, CharSequence error) { if (generation == epoch) message("Authentication cancelled or unavailable. Vault remains locked."); }
                @Override public void onAuthenticationFailed() { if (generation == epoch) message("Authentication failed. Try again or use the phone credential."); }
            });
    }
    private void unlockPersonal() {
        try {
            active = readActive(); if (active == null) throw new IllegalStateException();
            JSONObject state = active; String slot = state.getString("slot");
            authenticate(DeviceKey.cipher(slot, false, decode(state.getString("iv"))), c -> {
                String envelope = new String(c.doFinal(decode(state.getString("wrapped"))), StandardCharsets.UTF_8);
                if (state.optBoolean("password")) password("Separate vault password", false, false, p -> openEnvelope(slot, envelope, p));
                else openEnvelope(slot, envelope, "");
            });
        } catch (Exception e) { message("Device key or vault metadata unavailable. Your files were kept. Restore an exported portable backup; no replacement was created."); }
    }
    private void openEnvelope(String slot, String envelope, String password) {
        task(() -> { String secret = call("unprotect", envelope, password); return call("unlock", slotFile(slot).getPath(), secret); }, v -> { sample = false; unlocked = true; vaultScreen(); });
    }
    private void createOrRestore(File imported, String recovery) {
        if (!((KeyguardManager)getSystemService(KEYGUARD_SERVICE)).isDeviceSecure()) { message("Set a secure phone PIN, pattern or password first."); return; }
        password("Optional separate vault password (leave blank for phone authentication only)", true, true, p -> {
            String slot = UUID.randomUUID().toString();
            authenticate(DeviceKey.cipher(slot, true, null), cipher -> {
                task(() -> {
                    String secret = call("new_secret");
                    String envelope = call("protect", secret, p);
                    byte[] wrapped = cipher.doFinal(envelope.getBytes(StandardCharsets.UTF_8));
                    if (imported == null) call("create", slotFile(slot).getPath(), secret);
                    else { call("restore", imported.getPath(), slotFile(slot).getPath(), recovery, secret); call("unlock", slotFile(slot).getPath(), secret); }
                    JSONObject state = new JSONObject().put("slot", slot).put("iv", encode(cipher.getIV())).put("wrapped", encode(wrapped)).put("password", !p.isEmpty());
                    publish(state);
                    if (imported != null) imported.delete();
                    return "";
                }, v -> { sample = false; unlocked = true; vaultScreen(); message("Vault ready. Export a portable backup and keep its secret separately."); });
            });
        });
    }
    private EditText input(LinearLayout parent, String hint, boolean secret) {
        EditText field = new EditText(this); field.setHint(hint); field.setSingleLine(secret);
        field.setInputType(secret ? InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD : InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        field.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);
        parent.addView(field); return field;
    }
    private void password(String title, boolean confirmation, boolean optional, PasswordDone done) {
        LinearLayout fields = column(); EditText first = input(fields, "Password or recovery key", true);
        EditText second = confirmation ? input(fields, "Confirm password", true) : null;
        if (confirmation && !optional) button(fields, "Generate recovery key", () -> { String key = UUID.randomUUID().toString() + UUID.randomUUID().toString(); first.setText(key); second.setText(key); first.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD); });
        dialog = new AlertDialog.Builder(this).setTitle(title).setView(fields).setNegativeButton("Cancel", null).setPositiveButton("Continue", null).create();
        dialog.setOnShowListener(d -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
            String p = first.getText().toString();
            if (confirmation && (!p.equals(second.getText().toString()) || (!p.isEmpty() && p.length() < 12) || (!optional && p.length() < 12))) { first.setError("Match both fields; use at least 12 characters."); return; }
            if (optional && p.isEmpty() && !confirmation) return;
            dialog.dismiss(); first.setText(""); if (second != null) second.setText("");
            try { done.accept(p); } catch (Exception e) { message(safeError(e)); }
        })); dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE); dialog.show();
    }
    private void vaultScreen() {
        screen(sample ? "Invented sample vault" : "Personal vault");
        button(root, "Lock vault", () -> lock("Vault locked."));
        button(root, "Add entry", () -> edit(new JSONObject()));
        button(root, "Recently deleted", this::recentlyDeleted);
        if (!sample) {
            button(root, "Export portable backup", () -> export(false));
            button(root, "Export for desktop and NAS", () -> export(true));
            button(root, "Change optional vault password", this::changePassword);
        }
        EditText search = input(root, "Search description, username or link", false);
        rows = column(); root.addView(rows);
        search.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s,int a,int c,int f) {} public void onTextChanged(CharSequence s,int a,int b,int c) {}
            public void afterTextChanged(Editable e) { ui.removeCallbacks(searchJob); ui.postDelayed(searchJob, 250); }
            private final Runnable searchJob = () -> refresh(search.getText().toString());
        }); refresh(""); onUserInteraction();
    }
    private void refresh(String q) {
        if (!unlocked) return;
        task(() -> call("listing", q), value -> {
            rows.removeAllViews(); JSONArray records = new JSONArray(value);
            for (int i=0;i<records.length();i++) { JSONObject r=records.getJSONObject(i); String id=r.getString("id"); button(rows,r.getString("description")+"\n"+r.optString("user_name"),()-> showEntry(id)); }
            if (records.length()==0) rows.addView(text("No matching entries."));
        });
    }
    private void showEntry(String id) {
        task(() -> call("detail", id), v -> {
            JSONObject record = new JSONObject(v); LinearLayout view = column();
            view.setPadding(dp(24),dp(8),dp(24),dp(8));
            view.addView(text("Username: " + record.optString("user_name")));
            view.addView(text(record.optString("link")));
            TextView secret = text("••••••••"); secret.setTextSize(24); view.addView(secret);
            if (!record.optString("notes").isEmpty()) view.addView(text(record.optString("notes")));

            LinearLayout actions = column(); view.addView(actions);
            Button reveal = button(actions,"Show password",()->{});
            final boolean[] showing = {false};
            reveal.setOnClickListener(w -> {
                if (busy) { message("Please wait."); return; }
                showing[0] = !showing[0];
                secret.setText(showing[0] ? record.optString("password") : "••••••••");
                reveal.setText(showing[0] ? "Hide password" : "Show password");
            });
            button(actions,"Copy password",()->copy(record.optString("password")));
            button(actions,"Copy username",()->copy(record.optString("user_name")));
            button(actions,"Copy website",()->copy(record.optString("link")));
            button(actions,"Copy notes",()->copy(record.optString("notes")));
            button(actions,"Copy description",()->copy(record.optString("description")));
            button(actions,"Edit entry",()-> { dialog.dismiss(); edit(record); });
            button(actions,"Delete entry",()-> { dialog.dismiss(); new AlertDialog.Builder(this).setMessage("Move this entry to Recently deleted?").setNegativeButton("Cancel",null).setPositiveButton("Delete",(d,w)->task(()->call("delete",id),r->vaultScreen())).show(); });
            ScrollView scroll = new ScrollView(this); scroll.addView(view);
            dialog = new AlertDialog.Builder(this).setTitle(record.optString("description")).setView(scroll).setPositiveButton("Done",null).create();
            dialog.setOnDismissListener(d -> { secret.setText(""); view.removeAllViews(); dialog = null; });
            dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE); dialog.show();
        });
    }
    private void edit(JSONObject record) {
        LinearLayout fields=column(); String[] keys={"description","user_name","password","link","notes"}; EditText[] inputs=new EditText[keys.length];
        for(int i=0;i<keys.length;i++){ inputs[i]=input(fields,keys[i].replace("user_name","Username"),keys[i].equals("password")); inputs[i].setText(record.optString(keys[i])); }
        ScrollView scroll=new ScrollView(this); scroll.addView(fields);
        dialog=new AlertDialog.Builder(this).setTitle("Save entry").setView(scroll).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();
        dialog.setOnShowListener(d->dialog.getButton(-1).setOnClickListener(v->{
            if(inputs[0].getText().toString().trim().isEmpty()){inputs[0].setError("Description required");return;}
            try { for(int i=0;i<keys.length;i++)record.put(keys[i],inputs[i].getText().toString()); dialog.dismiss(); task(()->call("save",record.toString()),r->vaultScreen()); } catch(Exception e){message(safeError(e));}
        })); dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE); dialog.show();
    }
    private void recentlyDeleted() {
        task(()->call("deleted"),v->{ LinearLayout list=column();JSONArray records=new JSONArray(v);
            for(int i=0;i<records.length();i++){JSONObject r=records.getJSONObject(i);button(list,"Restore "+r.getString("description"),()->{dialog.dismiss();task(()->call("recover",r.optString("id")),x->vaultScreen());});}
            if(records.length()==0)list.addView(text("No deleted entries."));dialog=new AlertDialog.Builder(this).setTitle("Recently deleted").setView(list).setPositiveButton("Close",null).create();dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE); dialog.show(); });
    }
    private void copy(String value) {
        ClipboardManager c=(ClipboardManager)getSystemService(CLIPBOARD_SERVICE); ClipData clip=ClipData.newPlainText("Wormwright Pocket",value);
        PersistableBundle extras=new PersistableBundle();extras.putBoolean("android.content.extra.IS_SENSITIVE",true);clip.getDescription().setExtras(extras);
        c.setPrimaryClip(clip);ownedClip=value;ui.removeCallbacks(clearClip);ui.postDelayed(clearClip,30000);message("Copied. Clipboard clears in 30 seconds or when Vault locks.");
    }
    private void clearClipboard() {
        ClipboardManager c=(ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
        if(ownedClip!=null && c.hasPrimaryClip() && c.getPrimaryClip()!=null && c.getPrimaryClip().getItemCount()>0 && ownedClip.contentEquals(c.getPrimaryClip().getItemAt(0).coerceToText(this))) c.clearPrimaryClip();ownedClip=null;
    }
    private void export(boolean migration) {
        String title=migration?"Set and confirm desktop master password":"Backup password or generated recovery key — record it separately before continuing";
        password(title,true,false,p->task(()->{
            File target=new File(base,"export-"+UUID.randomUUID()+".sqlite");call("export",target.getPath(),p);return target.getPath();
        },v->{pendingExport=new File(v);Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/octet-stream").addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE,migration?"wormwright-desktop.sqlite":"wormwright-portable-backup.sqlite");startActivityForResult(intent,101);}));
    }
    private void chooseRestore() {
        new AlertDialog.Builder(this).setMessage("Restore creates a new local vault protected by this phone. The previous encrypted file is retained privately. Keep an exported backup of the current vault before replacing it. Select a portable backup and enter its backup secret, not your phone PIN.").setNegativeButton("Cancel",null).setPositiveButton("Choose backup",(d,w)->startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE),100)).show();
    }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data);
        if(request==101){File export=pendingExport;pendingExport=null;if(export==null)return;
            if(result!=RESULT_OK || data==null){export.delete();message("Export cancelled.");return;}
            task(()->{try(InputStream in=new FileInputStream(export);OutputStream out=getContentResolver().openOutputStream(data.getData(),"wt")){if(out==null)throw new IOException();byte[] buffer = new byte[8192]; int count; while ((count = in.read(buffer)) != -1) out.write(buffer, 0, count);}finally{export.delete();}return "";},v->message("Encrypted export saved. Keep its secret separately. Verify restoration before relying on it."));
        }
        if(request==100 && result==RESULT_OK && data!=null){
            task(()->{File imported=new File(base,"import-"+UUID.randomUUID()+".sqlite");try(InputStream in=getContentResolver().openInputStream(data.getData());OutputStream out=new FileOutputStream(imported)){byte[] b=new byte[8192];long total=0;int n;while((n=in.read(b))!=-1){total+=n;if(total>64L*1024*1024)throw new IOException();out.write(b,0,n);}}catch(Exception e){imported.delete();throw e;}return imported.getPath();},v->password("Backup password or recovery key",false,false,p->createOrRestore(new File(v),p)));
        }
    }
    private void changePassword() {
        // Reauthenticate the existing slot first, then create a fresh authenticated
        // envelope. Existing ciphertext and old slot remain until explicit cleanup.
        lock("Authenticate again to change the optional vault password.");
        try { JSONObject state=readActive();String old=state.getString("slot");
            authenticate(DeviceKey.cipher(old,false,decode(state.getString("iv"))),c->{String envelope=new String(c.doFinal(decode(state.getString("wrapped"))),StandardCharsets.UTF_8);
                PasswordDone current=p->task(()->call("unprotect",envelope,p),secret->password("New optional vault password (blank removes it)",true,true,next->{
                    String slot=UUID.randomUUID().toString();authenticate(DeviceKey.cipher(slot,true,null),cipher->task(()->{
                        String protectedSecret=call("protect",secret,next);byte[] wrapped=cipher.doFinal(protectedSecret.getBytes(StandardCharsets.UTF_8));
                        Files.copy(slotFile(old).toPath(),slotFile(slot).toPath());
                        publish(new JSONObject().put("slot",slot).put("iv",encode(cipher.getIV())).put("wrapped",encode(wrapped)).put("password",!next.isEmpty()));
                        DeviceKey.delete(old); slotFile(old).delete(); return "";
                    },r->home("Protection updated. Unlock again.")));
                }));
                if(state.optBoolean("password"))password("Current separate vault password",false,false,current);else current.accept("");
            });
        }catch(Exception e){message(safeError(e));}
    }
    private void help() {
        dialog=new AlertDialog.Builder(this).setTitle("Recovery and migration").setMessage("Phone authentication unlocks only this local vault. Exported backups require their separate password or generated recovery key on a replacement phone. Keep the backup and secret separately; losing the phone and all backup secrets makes recovery impossible.\n\nExports remain wherever you save them until you delete them. Wormwright Pocket does not rotate or delete exported backups. Deleted entries remain recoverable. Uninstalling clears app-private vaults and device keys, but does not delete exported documents.\n\nExport for desktop and NAS creates a signed format-2 personal vault; use its chosen master password (Owner account). Transfer it, open it on desktop, configure SMB NAS sync, then import a copy in the existing companion and complete initial NAS pairing. The phone vault stays independent. Format 2 retains deleted entries but has no per-entry edit history.\n\nSupport: danvanwormer@pm.me").setPositiveButton("Close",null).create();dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE); dialog.show();
    }
    private void lock(String note) {
        epoch++;unlocked=false;if(auth!=null)auth.cancel();if(dialog!=null)dialog.dismiss();ui.removeCallbacks(idle);clearClipboard();worker.execute(()->engine().callAttr("lock"));home(note);
    }
    @Override public void onUserInteraction(){super.onUserInteraction();if(unlocked){ui.removeCallbacks(idle);ui.postDelayed(idle,120000);}}
    @Override protected void onResume(){super.onResume();resumed=true;}
    @Override protected void onPause(){resumed=false;lock("Vault locked. Authenticate to reopen.");super.onPause();}
    @Override protected void onDestroy(){if(pendingExport!=null)pendingExport.delete();super.onDestroy();}
}

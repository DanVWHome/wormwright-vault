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
    private EditText search;
    private int searchVersion;
    private TextView status, progressLabel;
    private LinearLayout progressRow;
    private String progressText = "Working…";
    private final java.util.Map<View, Boolean> disabledControls = new java.util.IdentityHashMap<>();
    private boolean unlocked, sample, busy, resumed;
    private volatile int epoch;
    private CancellationSignal auth;
    private int authVersion;
    private boolean authenticating;
    private Runnable pendingAuthentication;
    private AlertDialog dialog;
    private DestructiveActions maintenance;
    private File base, pendingExport;
    private JSONObject active;
    private boolean startupChoicePending;
    private String ownedClip;
    private final Runnable idle = () -> lock("Locked after two minutes of inactivity.");
    private final Runnable clearClip = this::clearClipboard;
    private interface Job { String run() throws Exception; }
    private interface Done { void accept(String value) throws Exception; }
    private interface PasswordDone { void accept(String value) throws Exception; }
    private interface CryptoDone { void accept(Cipher cipher) throws Exception; }
    private PyObject engine() { return Python.getInstance().getModule("pocket"); }
    private String call(String name, Object... args) { PyObject result = engine().callAttr(name, args); return result == null ? "" : result.toString(); }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state); maintenance=new DestructiveActions(this); getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        getWindow().setDecorFitsSystemWindows(false);
        base = getNoBackupFilesDir();
        try { active = readActive(); startupChoicePending=savedVaults().size()>1; } catch (Exception e) { active = null; }
        home("Phone authentication unlocks this device. A separate backup secret restores exported backups.");
    }
    private JSONObject readActive() throws Exception {
        AtomicFile f = new AtomicFile(new File(base, "active.json"));
        if (!f.getBaseFile().exists()) return null;
        return new JSONObject(new String(f.readFully(), StandardCharsets.UTF_8));
    }
    private void saveState(File target, JSONObject state) throws Exception {
        AtomicFile f=new AtomicFile(target);FileOutputStream out=null;
        try{out=f.startWrite();out.write(state.toString().getBytes(StandardCharsets.UTF_8));f.finishWrite(out);}
        catch(Exception e){if(out!=null)f.failWrite(out);throw e;}
    }
    private void publish(JSONObject state) throws Exception {
        JSONObject previous=readActive();
        if(previous!=null && slotFile(previous.getString("slot")).exists()) saveState(new File(base,"saved-"+previous.getString("slot")+".json"),previous);
        if(!state.has("created"))state.put("created",new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm",java.util.Locale.US).format(new java.util.Date()));
        saveState(new File(base,"saved-"+state.getString("slot")+".json"),state);
        saveState(new File(base,"active.json"),state);active=state;
    }
    private File slotFile(String slot) { return new File(base, "vault-" + slot + ".sqlite"); }
    private byte[] decode(String s) { return Base64.decode(s, Base64.NO_WRAP); }
    private String encode(byte[] b) { return Base64.encodeToString(b, Base64.NO_WRAP); }
    private void setBusy(boolean value, String message) {
        busy = value; progressText = message;
        if (progressRow != null) { progressLabel.setText(message); progressRow.setVisibility(value ? View.VISIBLE : View.GONE); }
        if (value) { disabledControls.clear(); disableControls(root); }
        else { for (java.util.Map.Entry<View, Boolean> entry : disabledControls.entrySet()) entry.getKey().setEnabled(entry.getValue()); disabledControls.clear(); }
    }
    private void disableControls(View view) {
        if (view instanceof Button && !"Lock vault".contentEquals(((Button)view).getText()) && !"Help".contentEquals(((Button)view).getText()) || view instanceof EditText) {
            disabledControls.put(view, view.isEnabled()); view.setEnabled(false);
        }
        if (view instanceof ViewGroup) for (int i=0;i<((ViewGroup)view).getChildCount();i++) disableControls(((ViewGroup)view).getChildAt(i));
    }
    private void task(Job job, Done done) { task("Working…", job, done); }
    private void task(String label, Job job, Done done) {
        if (busy) { message("Please wait for the current operation."); return; }
        setBusy(true, label); final int generation = epoch;
        worker.execute(() -> {
            String result = null, error = null;
            try { if (generation == epoch) result = job.run(); }
            catch (Exception e) { error = safeError(e); }
            final String value = result, problem = error;
            ui.post(() -> {
                if (generation != epoch || !resumed || isFinishing()) return;
                setBusy(false, "");
                if (problem != null) { message(problem); return; }
                try { done.accept(value); } catch (Exception e) { message(safeError(e)); }
            });
        });
    }
    private String safeError(Exception e) {
        StackTraceElement[] trace=e.getStackTrace();
        android.util.Log.e("PocketFailure",e.getClass().getSimpleName()+(trace.length==0?"":" at "+trace[0].toString()));
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
        LinearLayout heading = new LinearLayout(this); heading.setGravity(Gravity.CENTER_VERTICAL);
        heading.addView(text(title), new LinearLayout.LayoutParams(0,-2,1));
        Button helpButton = new Button(this); helpButton.setText("Help"); helpButton.setAllCaps(false);
        helpButton.setOnClickListener(v -> {
            onUserInteraction(); PopupMenu menu = new PopupMenu(this,helpButton);
            menu.getMenu().add("Create new vault"); menu.getMenu().add("Vaults"); menu.getMenu().add("Rename current vault"); menu.getMenu().add("Delete current vault"); menu.getMenu().add("Delete vault…"); menu.getMenu().add("Delete all phone vaults"); menu.getMenu().add("Delete selected backups");
            menu.getMenu().add("Backup and recovery"); menu.getMenu().add("About"); menu.getMenu().add("Wormwright Website");
            menu.setOnMenuItemClickListener(item -> { String choice=item.getTitle().toString();
                if(choice.equals("Create new vault")) newVault(); else if(choice.equals("Vaults")) switchVault(); else if(choice.equals("Rename current vault")) renameVault(); else if(choice.equals("Delete current vault")) deleteCurrentVault(); else if(choice.equals("Delete vault…")) chooseVaultForDeletion(); else if(choice.equals("Delete all phone vaults")) deletePhoneVaults(); else if(choice.equals("Delete selected backups")) maintenance.chooseBackups(); else if (choice.equals("About")) about(); else if (choice.equals("Backup and recovery")) help(); else openWebsite(); return true; }); menu.show();
        });
        heading.addView(helpButton); root.addView(heading); root.addView(text("Version " + installedVersion())); status = text(""); root.addView(status);
        progressRow = column(); LinearLayout loading = new LinearLayout(this); loading.setGravity(Gravity.CENTER_VERTICAL);
        ProgressBar spinner = new ProgressBar(this); spinner.setIndeterminate(true); spinner.setContentDescription("Operation in progress");
        loading.addView(spinner, new LinearLayout.LayoutParams(dp(36),dp(36)));
        progressLabel = text(progressText); progressLabel.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        loading.addView(progressLabel); progressRow.addView(loading); progressRow.setVisibility(busy ? View.VISIBLE : View.GONE); root.addView(progressRow);
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
        v.setEnabled(!busy || "Lock vault".equals(title));
        v.setOnClickListener(w -> { if (!busy || "Lock vault".equals(title)) action.run(); else message("Please wait."); });
        return v;
    }
    private void message(String value) { if (status != null) status.setText(value); }
    private void home(String note) {
        screen("Wormwright Pocket"); root.addView(text("Your personal password vault"), 1); message(note);
        boolean stored = new File(base, "active.json").exists();
        if(stored)root.addView(text("Current vault: "+vaultLabel(active)));
        if (stored) { button(root,"Choose a vault",this::switchVault); button(root, "Open “"+vaultLabel(active)+"”", this::unlockPersonal); button(root,"Create new vault",this::newVault); button(root,"Delete current vault",this::deleteCurrentVault); }
        else {button(root, "Create personal vault", () -> createOrRestore(null, null));button(root,"Vaults",this::switchVault);}
        button(root, "Open invented sample vault", () -> { sample = true; task("Opening vault…", () -> call("sample", new File(base, "sample.sqlite").getPath()), v -> { unlocked = true; vaultScreen(); }); });
        button(root, "Restore portable encrypted backup", this::chooseRestore);
        button(root, "Backup and recovery help", this::help);
    }
    private void authenticate(Cipher cipher, CryptoDone done) {
        KeyguardManager guard = (KeyguardManager)getSystemService(KEYGUARD_SERVICE);
        if (!guard.isDeviceSecure()) { message("Set a secure phone PIN, pattern or password before using your personal vault."); return; }
        final int request = ++authVersion;
        if (auth != null) auth.cancel(); auth = new CancellationSignal(); authenticating = true;
        pendingAuthentication = null;
        try {
            new BiometricPrompt.Builder(this).setTitle("Unlock Wormwright Pocket")
                .setSubtitle("Confirm your identity")
                .setDescription("Use strong biometrics or your phone PIN, pattern or password.")
                .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG | BiometricManager.Authenticators.DEVICE_CREDENTIAL)
                .build().authenticate(new BiometricPrompt.CryptoObject(cipher), auth, getMainExecutor(), new BiometricPrompt.AuthenticationCallback() {
                    @Override public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult r) {
                        if (request != authVersion || isFinishing()) return;
                        pendingAuthentication = () -> {
                            if (request != authVersion || !resumed || isFinishing()) return;
                            authenticating = false; auth = null; pendingAuthentication = null;
                            try { if (r.getCryptoObject() == null || r.getCryptoObject().getCipher() == null) throw new IllegalStateException(); done.accept(r.getCryptoObject().getCipher()); }
                            catch (Exception e) { message(safeError(e)); }
                        };
                        if (resumed) pendingAuthentication.run();
                    }
                    @Override public void onAuthenticationError(int code, CharSequence error) {
                        if (request != authVersion) return;
                        authenticating = false; auth = null; pendingAuthentication = null;
                        message("Authentication cancelled or unavailable. Vault remains locked.");
                    }
                    @Override public void onAuthenticationFailed() { if (request == authVersion) message("Authentication failed. Try again or use the phone credential."); }
                });
        } catch(RuntimeException e) { authenticating=false;auth=null;pendingAuthentication=null;throw e; }
    }
    private void unlockPersonal() {
        try {
            active = readActive(); if (active == null) throw new IllegalStateException();
            JSONObject state = active; String slot = state.getString("slot");
            authenticate(DeviceKey.cipher(slot, false, decode(state.getString("iv"))), c -> {
                String envelope = new String(DeviceKey.finish(slot,c,decode(state.getString("wrapped"))), StandardCharsets.UTF_8);
                if (state.optBoolean("password")) password("Separate vault password", false, false, p -> openEnvelope(slot, envelope, p));
                else openEnvelope(slot, envelope, "");
            });
        } catch (Exception e) { message("Device key or vault metadata unavailable. Your files were kept. Restore an exported portable backup; no replacement was created."); }
    }
    private void openEnvelope(String slot,String envelope,String password) {
        task("Opening vault…",()->{String secret=call("unprotect",envelope,password);String result=call("unlock",slotFile(slot).getPath(),secret);String name=call("vault_name");
            JSONObject state=readActive();if(state!=null&&slot.equals(state.optString("slot"))&&!name.isEmpty()){state.put("name",name);publish(state);}return result;
        },v->{sample=false;unlocked=true;vaultScreen();if(active.optString("name","").isEmpty())message("This vault has no name yet. Choose Rename current vault to identify it in the list.");});
    }
    private void createOrRestore(File imported, String recovery) {
        namePrompt("Name the vault", "", null, name->createNamed(imported,recovery,name));
    }
    private void createNamed(File imported,String recovery,String name) {
        if (!((KeyguardManager)getSystemService(KEYGUARD_SERVICE)).isDeviceSecure()) { message("Set a secure phone PIN, pattern or password first."); return; }
        password("Optional vault password", true, true, p -> {
            String slot = UUID.randomUUID().toString();
            authenticate(DeviceKey.cipher(slot, true, null), cipher -> {
                task(() -> {
                    String secret = call("new_secret");
                    String envelope = call("protect", secret, p);
                    byte[] wrapped = DeviceKey.finish(slot,cipher,envelope.getBytes(StandardCharsets.UTF_8));
                    if (imported == null) call("create", slotFile(slot).getPath(), secret,name);
                    else { call("restore", imported.getPath(), slotFile(slot).getPath(), recovery, secret); call("unlock", slotFile(slot).getPath(), secret);call("rename_vault",name); }
                    JSONObject state = new JSONObject().put("slot", slot).put("iv", encode(cipher.getIV())).put("wrapped", encode(wrapped)).put("password", !p.isEmpty()).put("name",name);
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
        LinearLayout fields = column(); fields.setPadding(dp(20),dp(8),dp(20),dp(8));
        if(optional) fields.addView(text("Leave blank to use phone authentication only. If you add a password, enter it in both fields (at least 12 characters)."));
        EditText first = input(fields, "Password or recovery key", true);
        EditText second = confirmation ? input(fields, "Confirm password", true) : null;
        if (confirmation && !optional) button(fields, "Generate recovery key", () -> { String key = UUID.randomUUID().toString() + UUID.randomUUID().toString(); first.setText(key); second.setText(key); first.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD); });
        final int token = epoch;
        ScrollView passwordScroll = new ScrollView(this); passwordScroll.addView(fields);
        final AlertDialog prompt = new AlertDialog.Builder(this).setTitle(title).setView(passwordScroll).setNegativeButton("Cancel", null).setPositiveButton("Continue", null).create();
        dialog = prompt;
        prompt.setOnDismissListener(d -> { first.setText(""); if (second != null) second.setText(""); if (dialog == prompt) dialog = null; });
        prompt.setOnShowListener(d -> {
            if (!prompt.isShowing() || token != epoch) return;
            prompt.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
                if (token != epoch || !prompt.isShowing()) return;
                String value = first.getText().toString();
                if (confirmation && (!value.equals(second.getText().toString()) || (!value.isEmpty() && value.length() < 12) || (!optional && value.length() < 12))) { first.setError("Match both fields; use at least 12 characters."); return; }
                if (optional && value.isEmpty() && !confirmation) return;
                prompt.dismiss();
                try { done.accept(value); } catch (Exception e) { message(safeError(e)); }
            });
        }); prompt.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE); prompt.show();
    }

    private void vaultScreen() {
        screen(sample ? "Invented sample vault" : vaultLabel(active));
        button(root, "Lock vault", () -> lock("Vault locked."));
        button(root, "Add entry", () -> edit(new JSONObject()));
        button(root, "Recently deleted", this::recentlyDeleted);
        if (!sample) {
            button(root,"Vaults",this::switchVault); button(root,"Rename current vault",this::renameVault); button(root,"Delete current vault",this::deleteCurrentVault);
            button(root, "Export portable backup", () -> export(false));
            button(root, "Export for desktop and NAS", () -> export(true));
            button(root, "Change optional vault password", this::changePassword);
        }
        search = input(root, "Search description, username or link", false);
        rows = column(); root.addView(rows);
        search.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s,int a,int c,int f) {} public void onTextChanged(CharSequence s,int a,int b,int c) {}
            public void afterTextChanged(Editable e) { ++searchVersion; for(int i=0;i<rows.getChildCount();i++)rows.getChildAt(i).setEnabled(false); ui.removeCallbacks(searchJob); ui.postDelayed(searchJob, 250); }
            private final Runnable searchJob = () -> refresh(search.getText().toString());
        }); refresh(""); onUserInteraction();
    }
    private void refresh(String q) {
        if (!unlocked) return;
        final int token = epoch, request = ++searchVersion;
        final LinearLayout target = rows;
        for (int i=0;i<target.getChildCount();i++) target.getChildAt(i).setEnabled(false);
        worker.execute(() -> {
            String result = null, error = null;
            try { if (token == epoch) result = call("listing",q); } catch (Exception e) { error = safeError(e); }
            final String value = result, problem = error;
            ui.post(() -> {
                if (token != epoch || request != searchVersion || !unlocked || !resumed || target != rows) return;
                if (problem != null) { for(int i=0;i<target.getChildCount();i++) target.getChildAt(i).setEnabled(true); message(problem); return; }
                try {
                    JSONArray records = new JSONArray(value); target.removeAllViews();
                    for(int i=0;i<records.length();i++) { JSONObject r=records.getJSONObject(i); String id=r.getString("id"); button(target,r.getString("description")+"\n"+r.optString("user_name"),()->showEntry(id)); }
                    if(records.length()==0)target.addView(text("No matching entries."));
                } catch(Exception e) { message(safeError(e)); }
            });
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
            button(actions,"Delete entry",()-> { dialog.dismiss(); confirmDelete(id); });
            ScrollView scroll = new ScrollView(this); scroll.addView(view);
            final AlertDialog detail = new AlertDialog.Builder(this).setTitle(record.optString("description")).setView(scroll).setPositiveButton("Done",null).create();
            dialog = detail;
            detail.setOnDismissListener(d -> { secret.setText(""); view.removeAllViews(); if (dialog == detail) dialog = null; });
            detail.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE); detail.show();
        });
    }
    private void confirmDelete(String id) {
        final int token = epoch;
        final AlertDialog confirmation = new AlertDialog.Builder(this).setMessage("Move this entry to Recently deleted?")
                .setNegativeButton("Cancel",null).setPositiveButton("Delete",(d,w)-> {
                    if (token == epoch && unlocked && !busy) task("Deleting entry…",()->call("delete",id),r->vaultScreen());
                }).create();
        dialog = confirmation;
        confirmation.setOnDismissListener(d -> { if (dialog == confirmation) dialog = null; });
        confirmation.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE); confirmation.show();
    }
    private void edit(JSONObject record) {
        LinearLayout fields=column(); String[] keys={"description","user_name","password","link","notes"}; EditText[] inputs=new EditText[keys.length];
        for(int i=0;i<keys.length;i++){ inputs[i]=input(fields,keys[i].replace("user_name","Username"),keys[i].equals("password")); inputs[i].setText(record.optString(keys[i])); }
        CheckBox showPassword = new CheckBox(this); showPassword.setText("Show password");
        showPassword.setOnCheckedChangeListener((button,show)-> {
            int start=inputs[2].getSelectionStart(),end=inputs[2].getSelectionEnd();
            inputs[2].setTransformationMethod(show ? null : android.text.method.PasswordTransformationMethod.getInstance());
            if(start>=0 && end>=0)inputs[2].setSelection(start,end); onUserInteraction();
        }); fields.addView(showPassword);
        button(fields,"Generate password",()->{inputs[2].setText(PasswordGenerator.generate());inputs[2].setSelection(inputs[2].length());onUserInteraction();});
        ScrollView scroll=new ScrollView(this); scroll.addView(fields);
        final int token = epoch;
        final AlertDialog editor = new AlertDialog.Builder(this).setTitle("Save entry").setView(scroll).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();
        dialog = editor;
        editor.setOnDismissListener(d -> { for (EditText field : inputs) field.setText(""); if (dialog == editor) dialog = null; });
        editor.setOnShowListener(d -> {
            if (!editor.isShowing() || token != epoch || !unlocked) return;
            editor.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
                if (token != epoch || !unlocked || busy || !editor.isShowing()) return;
                if(inputs[0].getText().toString().trim().isEmpty()){inputs[0].setError("Description required");return;}
                try { for(int i=0;i<keys.length;i++)record.put(keys[i],inputs[i].getText().toString()); editor.dismiss(); task("Saving entry…", ()->call("save",record.toString()),r->vaultScreen()); } catch(Exception e){message(safeError(e));}
            });
        }); editor.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE); editor.show();
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
        if(maintenance.result(request,result,data))return;
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
            authenticate(DeviceKey.cipher(old,false,decode(state.getString("iv"))),c->{String envelope=new String(DeviceKey.finish(old,c,decode(state.getString("wrapped"))),StandardCharsets.UTF_8);
                PasswordDone current=p->task(()->call("unprotect",envelope,p),secret->password("Change vault password",true,true,next->{
                    String slot=UUID.randomUUID().toString();authenticate(DeviceKey.cipher(slot,true,null),cipher->task(()->{
                        String protectedSecret=call("protect",secret,next);byte[] wrapped=DeviceKey.finish(slot,cipher,protectedSecret.getBytes(StandardCharsets.UTF_8));
                        Files.copy(slotFile(old).toPath(),slotFile(slot).toPath());
                        publish(new JSONObject().put("slot",slot).put("iv",encode(cipher.getIV())).put("wrapped",encode(wrapped)).put("password",!next.isEmpty()).put("name",state.optString("name", "")).put("created",state.optString("created","")));
                        DeviceKey.delete(old); slotFile(old).delete(); new File(base,"saved-"+old+".json").delete(); return "";
                    },r->home("Protection updated. Unlock again.")));
                }));
                if(state.optBoolean("password"))password("Current separate vault password",false,false,current);else current.accept("");
            });
        }catch(Exception e){message(safeError(e));}
    }
    private void newVault() {
        if(busy)return;
        final AlertDialog prompt=new AlertDialog.Builder(this).setTitle("Create new vault")
            .setMessage("Create a separate empty personal vault. Your current vault is kept and can be reopened using Switch personal vault. Export a backup before testing. This new vault is independent of NAS copies.")
            .setNegativeButton("Cancel",null).setPositiveButton("Create",(d,w)->{lock("Creating a separate new vault.");createOrRestore(null,null);}).create();
        dialog=prompt;prompt.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);prompt.show();
    }
    private String vaultLabel(JSONObject state) {
        if(state==null)return "No selected vault";
        String name=state.optString("name","").trim();
        return name.isEmpty()?"Unnamed vault · "+state.optString("created","Earlier vault")+" · "+state.optString("slot","").substring(0,Math.min(8,state.optString("slot","").length())):name;
    }
    private java.util.List<JSONObject> savedVaults() throws Exception {
        java.util.List<JSONObject> states=new java.util.ArrayList<>();JSONObject current=readActive();
        if(current!=null&&slotFile(current.getString("slot")).exists())saveState(new File(base,"saved-"+current.getString("slot")+".json"),current);
        File[] files=base.listFiles();if(files!=null)for(File file:files)if(file.getName().matches("saved-[a-f0-9-]{36}\\.json")){
            JSONObject state=new JSONObject(new String(new AtomicFile(file).readFully(),StandardCharsets.UTF_8));String slot=state.getString("slot");
            if(slot.matches("[a-f0-9-]{36}")&&slotFile(slot).exists())states.add(state);
        }
        states.sort((a,b)->vaultLabel(a).compareToIgnoreCase(vaultLabel(b)));return states;
    }
    private void namePrompt(String title,String initial,String exceptSlot,PasswordDone done) {
        LinearLayout fields=column();fields.setPadding(dp(20),dp(8),dp(20),dp(8));fields.addView(text("Give this vault a recognizable name. The name is shown in your vault list."));
        EditText name=input(fields,"Vault name (required)",false);name.setSingleLine(true);name.setText(initial);final int token=epoch;
        final AlertDialog prompt=new AlertDialog.Builder(this).setTitle(title).setView(fields).setNegativeButton("Cancel",null).setPositiveButton("Save name",null).create();dialog=prompt;
        prompt.setOnDismissListener(d->{name.setText("");if(dialog==prompt)dialog=null;});
        prompt.setOnShowListener(d->prompt.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            if(token!=epoch||busy)return;String value=name.getText().toString().trim();
            if(value.isEmpty()||value.length()>80||value.matches(".*[\\p{Cntrl}].*")){name.setError("Enter a vault name of 1–80 characters.");return;}
            try{for(JSONObject state:savedVaults())if(!state.optString("slot").equals(exceptSlot)&&value.equalsIgnoreCase(state.optString("name",""))){name.setError("That vault name is already used. Choose a different name.");return;}
                prompt.dismiss();done.accept(value);
            }catch(Exception e){message(safeError(e));}
        }));prompt.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);prompt.show();
    }
    private void renameVault() {
        if(busy)return;
        if(!unlocked||sample){message("Unlock the selected personal vault to name it.");return;}
        final JSONObject state=active;
        namePrompt("Rename current vault",state.optString("name",""),state.optString("slot"),name->task("Saving vault name…",()->{call("rename_vault",name);state.put("name",name);publish(state);return "";},v->vaultScreen()));
    }
    private void vaultChooser(boolean deleting) {
        if(busy)return;
        try{java.util.List<JSONObject> states=savedVaults();java.util.List<String> labels=new java.util.ArrayList<>();JSONObject current=readActive();
            for(JSONObject state:states)labels.add(vaultLabel(state)+(current!=null&&state.getString("slot").equals(current.optString("slot"))?" (current)":""));
            if(states.isEmpty()){message("No saved personal vaults.");return;}
            final AlertDialog chooser=new AlertDialog.Builder(this).setTitle(deleting?"Select one vault to delete":"Vaults — select to open")
                .setItems(labels.toArray(new String[0]),(d,index)->{JSONObject chosen=states.get(index);
                    if(deleting){deleteVault(chosen);return;}
                    lock("Selected "+vaultLabel(chosen)+". Authenticate to open it.");try{publish(chosen);home("Selected "+vaultLabel(chosen)+". Authenticate to open it.");unlockPersonal();}catch(Exception e){message(safeError(e));}
                }).setNegativeButton("Cancel",null).create();dialog=chooser;chooser.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);chooser.show();
        }catch(Exception e){message(safeError(e));}
    }
    private void switchVault(){vaultChooser(false);}
    private void chooseVaultForDeletion(){vaultChooser(true);}
    private void deleteCurrentVault(){try{JSONObject state=readActive();if(state==null){message("No current vault to delete.");return;}deleteVault(state);}catch(Exception e){message(safeError(e));}}
    private void deleteVault(JSONObject state) {
        if(busy)return;
        deletionStart("Delete “"+vaultLabel(state)+"”?","Only this selected phone vault and its device key will be deleted. Other vaults and exported backups are kept. Continue to authenticate, then review and type DELETE.",()->authorizeVaultDeletion(state));
    }
    private void deletionStart(String title,String scope,Runnable action) {
        final AlertDialog prompt=new AlertDialog.Builder(this).setTitle(title).setMessage(scope).setNegativeButton("Cancel",null).setPositiveButton("Continue",(d,w)->action.run()).create();dialog=prompt;
        prompt.setOnDismissListener(d->{if(dialog==prompt)dialog=null;});prompt.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);prompt.show();
    }
    private void authorizeVaultDeletion(JSONObject state) {
        if(busy)return;
        lock("Authenticate to delete “"+vaultLabel(state)+"”.");
        try{String slot=state.getString("slot");if(!slot.matches("[a-f0-9-]{36}")||!slotFile(slot).exists())throw new IllegalStateException();
            authenticate(DeviceKey.cipher(slot,false,decode(state.getString("iv"))),cipher->{
                String envelope=new String(DeviceKey.finish(slot,cipher,decode(state.getString("wrapped"))),StandardCharsets.UTF_8);
                PasswordDone verified=password->task("Verifying selected vault…",()->{String secret=call("unprotect",envelope,password);return call("verify_deletion",slotFile(slot).getPath(),secret);},name->{
                    String label=name.isEmpty()?vaultLabel(state):name;
                    maintenance.confirm("Delete one vault","Permanently delete only “"+label+"” ("+slot.substring(0,8)+") and its phone key. Other phone vaults, exported backups, desktop vaults and NAS copies are kept.",()->task("Deleting selected vault…",()->{
                        call("lock");DeviceKey.delete(slot);java.util.List<String> failures=new java.util.ArrayList<>();
                        for(String file:new String[]{"vault-"+slot+".sqlite","vault-"+slot+".sqlite-wal","vault-"+slot+".sqlite-shm","vault-"+slot+".sqlite-journal","saved-"+slot+".json","saved-"+slot+".json.bak","saved-"+slot+".json.new"})try{Files.deleteIfExists(new File(base,file).toPath());}catch(Exception e){failures.add(file);}
                        JSONObject current=readActive();if(current!=null&&slot.equals(current.optString("slot"))){for(String file:new String[]{"active.json","active.json.bak","active.json.new"})try{Files.deleteIfExists(new File(base,file).toPath());}catch(Exception e){failures.add(file);}active=null;
                            if(failures.isEmpty()){java.util.List<JSONObject> remaining=savedVaults();if(!remaining.isEmpty())publish(remaining.get(0));}
                        }
                        return failures.isEmpty()?"Deleted “"+label+"”. Other vaults and backups were kept.":"Deletion incomplete. Could not remove: "+String.join(", ",failures);
                    },result->lock(result)));
                });if(state.optBoolean("password"))password("Password for “"+vaultLabel(state)+"”",false,false,verified);else verified.accept("");
            });
        }catch(Exception e){message("Cannot authorize this selected vault. Nothing was deleted.");}
    }
    private void deletePhoneVaults() {
        if(busy)return;
        deletionStart("Delete all phone vaults?","This removes every personal vault stored inside Pocket and their device keys. Exported backups are kept. Continue to authenticate, then review and type DELETE.",this::authorizeAllVaultDeletion);
    }
    private void authorizeAllVaultDeletion() {
        if(busy)return;
        lock("Authenticate to review permanent deletion.");
        try{
            JSONObject state=readActive();
            if(state==null){maintenance.authenticate(this::reviewPhoneDeletion);return;}
            String slot=state.getString("slot");
            authenticate(DeviceKey.cipher(slot,false,decode(state.getString("iv"))),cipher->{
                String envelope=new String(DeviceKey.finish(slot,cipher,decode(state.getString("wrapped"))),StandardCharsets.UTF_8);
                PasswordDone verified=p->task("Verifying authorization…",()->call("unprotect",envelope,p),v->reviewPhoneDeletion());
                if(state.optBoolean("password"))password("Current separate vault password",false,false,verified);else verified.accept("");
            });
        }catch(Exception e){message("Cannot authenticate this vault. Nothing was deleted. Restore access before using permanent deletion.");}
    }
    private void reviewPhoneDeletion() {
        int count=0;File[] files=base.listFiles();if(files!=null)for(File file:files)if(file.getName().matches("vault-[a-f0-9-]{36}\\.sqlite"))count++;
        maintenance.confirm("Delete all phone vaults", "Remove all "+count+" private personal vault files, retained older phone copies, sample data and their device keys. Exported backups, desktop vaults and NAS copies are separate and are not removed.",()->task("Deleting phone vaults…",()->{
            call("lock");java.util.List<String> failures=new java.util.ArrayList<>();
            try{DeviceKey.deleteAll();}catch(Exception e){failures.add("device keys");}
            File[] stored=base.listFiles();if(stored!=null)for(File file:stored){String n=file.getName();
                if(n.equals("active.json")||n.startsWith("active.json.")||n.startsWith("saved-")||n.startsWith("vault-")||n.startsWith("import-")||n.startsWith("export-")||n.startsWith("sample.sqlite"))try{Files.deleteIfExists(file.toPath());}catch(Exception e){failures.add(n);}
            }active=null;return String.join(", ",failures);
        },v->{lock(v.isEmpty()?"Phone vaults deleted. Create a new personal vault or restore a backup.":"Deletion incomplete. Could not remove: "+v);}));
    }
    private String installedVersion() {
        try { return getPackageManager().getPackageInfo(getPackageName(),0).versionName; }
        catch (android.content.pm.PackageManager.NameNotFoundException e) { return "unavailable"; }
    }
    private void openWebsite() {
        try { startActivity(new Intent(Intent.ACTION_VIEW,android.net.Uri.parse("https://wormwright.com/"))); }
        catch (ActivityNotFoundException e) { message("Open https://wormwright.com/ in your browser."); }
    }
    private void about() {
        final AlertDialog about = new AlertDialog.Builder(this).setTitle("About Wormwright Pocket")
            .setMessage("Your personal password vault\n\nVersion " + installedVersion() + "\n\nhttps://wormwright.com/")
            .setPositiveButton("Website",(d,w) -> openWebsite()).setNegativeButton("Close",null).create();
        dialog=about; about.setOnDismissListener(d -> { if(dialog==about) dialog=null; });
        about.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE); about.show();
    }
    private void help() {
        dialog=new AlertDialog.Builder(this).setTitle("Recovery and migration").setMessage("Phone authentication unlocks only this local vault. Exported backups require their separate password or generated recovery key on a replacement phone. Keep the backup and secret separately; losing the phone and all backup secrets makes recovery impossible.\n\nExports remain wherever you save them until you delete them. Wormwright Pocket does not automatically rotate or delete exported backups. Use Help → Delete selected backups to choose exported files for separately authorized deletion. Deleted entries remain recoverable. Uninstalling clears app-private vaults and device keys, but does not delete exported documents.\n\nExport for desktop and NAS creates a signed format-2 personal vault; use its chosen master password (Owner account). Transfer it, open it on desktop, configure SMB NAS sync, then import a copy in the existing companion and complete initial NAS pairing. The phone vault stays independent. Format 2 retains deleted entries but has no per-entry edit history.\n\nSupport: danvanwormer@pm.me").setPositiveButton("Close",null).create();dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE); dialog.show();
    }
    private void lock(String note) { lock(note,false); }
    private void lock(String note,boolean keepAuthentication) {
        epoch++;unlocked=false;setBusy(false, "");
        if(!keepAuthentication) { ++authVersion;authenticating=false;pendingAuthentication=null;if(auth!=null)auth.cancel();auth=null; }
        if(dialog!=null)dialog.dismiss();ui.removeCallbacks(idle);clearClipboard();worker.execute(()->engine().callAttr("lock"));home(note);
    }
    @Override public void onUserInteraction(){super.onUserInteraction();if(unlocked){ui.removeCallbacks(idle);ui.postDelayed(idle,120000);}}
    @Override protected void onResume(){super.onResume();resumed=true;maintenance.onResume();if(startupChoicePending){startupChoicePending=false;ui.post(()->{if(resumed&&!busy&&!authenticating)switchVault();});}if(pendingAuthentication!=null)ui.post(()->{if(pendingAuthentication!=null)pendingAuthentication.run();});}
    @Override protected void onPause(){maintenance.onPause();resumed=false;lock("Vault locked. Authenticate to reopen.",authenticating);super.onPause();}
    @Override protected void onDestroy(){maintenance.onDestroy();++authVersion;pendingAuthentication=null;if(auth!=null)auth.cancel();if(pendingExport!=null)pendingExport.delete();super.onDestroy();}
}

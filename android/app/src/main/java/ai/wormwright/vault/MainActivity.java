package ai.wormwright.vault;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipDescription;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.ActivityNotFoundException;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PersistableBundle;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.view.View;
import android.view.ViewGroup;
import android.view.Gravity;
import android.view.WindowManager;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.PopupMenu;
import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** A local, read-only preview. All crypto and SQLite work uses one worker. */
public class MainActivity extends Activity {
    private static final int IMPORT = 100;
    private static final int EXPORT = 101;
    private static final int NAVY = Color.rgb(23, 45, 67);
    private static final int CREAM = Color.rgb(255, 249, 238);
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private LinearLayout root, rows;
    private EditText username, password, search;
    private TextView status, progressLabel;
    private LinearLayout progressRow;
    private String progressText = "Working…";
    private final java.util.Map<View, Boolean> disabledControls = new java.util.IdentityHashMap<>();
    private AlertDialog detailDialog;
    private AlertDialog nasDialog;
    private AlertDialog editorDialog;
    private AlertDialog conflictDialog;
    private NasSettings nasSettings;
    private File vaultFile;
    private volatile boolean unlocked = false, resumed = false;
    private boolean busy = false, sampleMode = false, nasRunning = false;
    private volatile int generation = 0;
    private int searchVersion = 0;
    private String ownedClip = null;
    private JSONObject conflictReview;
    private JSONObject conflictChoices;
    private final Runnable idleLock = () -> lockNow("Locked after two minutes of inactivity.");
    private final Runnable clipClear = this::clearOwnedClipboard;
    private final Runnable nasPoll = new Runnable() {
        public void run() {
            if (!resumed || !unlocked || sampleMode || !nasSettings.exists()) return;
            refreshNas(false); handler.postDelayed(this, 60000);
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        vaultFile = new File(getNoBackupFilesDir(), "vault.db");
        nasSettings = new NasSettings(this);
        showLogin(vaultFile.exists() ? "Your encrypted phone copy is ready." : "Bring an encrypted vault copy from your computer.");
    }

    private int dp(int n) { return Math.round(n * getResources().getDisplayMetrics().density); }
    private LinearLayout column() {
        LinearLayout result = new LinearLayout(this);
        result.setOrientation(LinearLayout.VERTICAL);
        return result;
    }
    private TextView label(String value, int size) {
        TextView view = new TextView(this);
        view.setText(value); view.setTextSize(size); view.setTextColor(NAVY);
        view.setPadding(0, dp(8), 0, dp(8));
        return view;
    }
    private Button button(String value, Runnable action) {
        Button view = new Button(this);
        view.setText(value); view.setAllCaps(false); view.setTextColor(NAVY);
        view.setOnClickListener(v -> { onUserInteraction(); action.run(); });
        return view;
    }
    private EditText input(String hint, boolean secret) {
        EditText view = new EditText(this);
        view.setHint(hint); view.setSingleLine(true); view.setTextSize(17);
        view.setInputType(secret ? InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD
                : InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        view.setSaveEnabled(false);
        view.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);
        view.setPadding(dp(8), dp(12), dp(8), dp(12));
        view.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s,int start,int count,int after) {}
            public void onTextChanged(CharSequence s,int start,int before,int count) { resetIdleTimer(); }
            public void afterTextChanged(Editable value) {}
        });
        return view;
    }
    private void frame(String subtitle) {
        root = column(); root.setBackgroundColor(CREAM);
        root.setPadding(dp(24), dp(16), dp(24), dp(16));
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            android.graphics.Insets bars = insets.getInsets(android.view.WindowInsets.Type.systemBars() | android.view.WindowInsets.Type.displayCutout());
            android.graphics.Insets ime = insets.getInsets(android.view.WindowInsets.Type.ime());
            view.setPadding(dp(24) + bars.left, dp(16) + bars.top, dp(24) + bars.right, dp(16) + Math.max(bars.bottom, ime.bottom));
            return insets;
        });
        TextView title = label("Wormwright Vault", 28); title.setTypeface(null, Typeface.BOLD);
        LinearLayout heading = new LinearLayout(this);
        heading.addView(title, new LinearLayout.LayoutParams(0, -2, 1));
        Button help = button("Help", () -> {});
        help.setOnClickListener(v -> {
            onUserInteraction();
            PopupMenu menu = new PopupMenu(this, help);
            menu.getMenu().add("Wormwright Website");
            menu.setOnMenuItemClickListener(item -> { openWebsite(); return true; });
            menu.show();
        });
        heading.addView(help);
        root.addView(heading); root.addView(label(subtitle, 15));
        progressRow = new LinearLayout(this); progressRow.setGravity(Gravity.CENTER_VERTICAL);
        ProgressBar spinner = new ProgressBar(this); spinner.setIndeterminate(true); spinner.setContentDescription("Operation in progress");
        progressRow.addView(spinner, new LinearLayout.LayoutParams(dp(36),dp(36)));
        progressLabel = label(progressText, 16); progressLabel.setPadding(dp(12),dp(8),0,dp(8));
        progressLabel.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE); progressRow.addView(progressLabel);
        root.addView(progressRow); updateProgress();
        setContentView(root); root.requestApplyInsets();
    }
    private void openWebsite() {
        try {
            // Fixed public URL only: never attach account, search or vault data.
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://wormwright.com/")));
        } catch (ActivityNotFoundException error) {
            new AlertDialog.Builder(this).setTitle("Cannot open website")
                .setMessage("Open https://wormwright.com/ in your browser.")
                .setPositiveButton("OK", null).show();
        }
    }

    private void showLogin(String message) {
        frame("ANDROID PREVIEW · PRIVATE PHONE COPY");
        ScrollView scroll = new ScrollView(this); LinearLayout form = column();
        scroll.addView(form); root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        form.addView(label("Your vault, wherever you are", 23));
        username = input("Account name", false);
        password = input("Vault account password", true);
        form.addView(username); form.addView(password);
        password.setOnFocusChangeListener((view, focused) -> {
            if (focused) scroll.post(() -> password.requestRectangleOnScreen(
                    new android.graphics.Rect(0, 0, password.getWidth(), password.getHeight()), false));
        });
        Button unlock = button("Unlock vault", this::unlock);
        unlock.setEnabled(vaultFile.exists()); form.addView(unlock);
        form.addView(button(vaultFile.exists() ? "Replace encrypted phone copy" : "Import encrypted vault", this::chooseImport));
        form.addView(button("Try the sample vault", this::loadSample));
        form.addView(button("NAS connection settings", this::configureNas));
        if (vaultFile.exists()) form.addView(button("Export encrypted phone backup", this::chooseExport));
        status = label(message, 15); form.addView(status);
        form.addView(label("Personal vault: leave account name blank.", 14));
        form.addView(label("Read and edit your encrypted vault offline. Changes sync with your NAS after unlocking, saving and while the app is open. Complete the first NAS sync before editing.", 16));
        form.addView(label("Locks when you leave the app or after two minutes idle. Screenshots and device backups are disabled. Copied values clear after 30 seconds or when you lock.", 14));
        form.addView(label("0.1.0-preview.6 · No Google Play services needed", 13));
    }
    private PyObject bridge() { return Python.getInstance().getModule("mobile_bridge"); }
    private interface Job { String run() throws Exception; }
    private interface Result { void accept(String value) throws Exception; }
    private void updateProgress() {
        if (progressRow != null) { progressLabel.setText(busy ? progressText : "Syncing with NAS…"); progressRow.setVisibility(busy || nasRunning ? View.VISIBLE : View.GONE); }
    }
    private void setBusy(boolean value, String label) {
        busy = value; progressText = label; updateProgress();
        if (value) { disabledControls.clear(); disableControls(root); }
        else { for (java.util.Map.Entry<View, Boolean> entry : disabledControls.entrySet()) entry.getKey().setEnabled(entry.getValue()); disabledControls.clear(); }
    }
    private void disableControls(View view) {
        if (view instanceof Button && !"Lock".contentEquals(((Button)view).getText()) && !"Help".contentEquals(((Button)view).getText()) || view instanceof EditText) {
            disabledControls.put(view,view.isEnabled()); view.setEnabled(false);
        }
        if (view instanceof ViewGroup) for(int i=0;i<((ViewGroup)view).getChildCount();i++) disableControls(((ViewGroup)view).getChildAt(i));
    }
    private void job(Job task, Result success, String errorText) { job("Working…", task, success, errorText); }
    private void job(String label, Job task, Result success, String errorText) {
        if (busy) return;
        final int token = generation;
        setBusy(true, label);
        worker.execute(() -> {
            String result = null; boolean failed = false;
            try { result = task.run(); } catch (Exception error) { failed = true; }
            final String value = result; final boolean error = failed;
            handler.post(() -> {
                if (token != generation || !resumed || isFinishing()) return;
                setBusy(false, "");
                if (error) { lockNow(errorText); return; }
                try { success.accept(value); }
                catch (Exception ignored) { lockNow("Cannot read this vault. Import a valid encrypted copy."); }
            });
        });
    }
    private void unlock() {
        if (busy || !vaultFile.exists()) return;
        String account = username.getText().toString();
        String secret = password.getText().toString();
        password.getText().clear();
        ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(password.getWindowToken(), 0);
        status.setText("Unlocking and checking vault signatures…");
        job("Opening vault…", () -> bridge().callAttr("unlock", vaultFile.getAbsolutePath(), account, secret, true, false).toString(),
            result -> {
                unlocked = true; sampleMode = false; showEntries(result); resetIdleTimer();
                if (nasSettings.exists()) { refreshNas(false); handler.postDelayed(nasPoll, 60000); }
            },
            "Cannot unlock. Check the account name and password, or import a fresh encrypted copy.");
    }
    private void showEntries(String result) throws Exception {
        frame(sampleMode ? "SAMPLE VAULT · INVENTED ENTRIES" : "YOUR VAULT · OFFLINE EDITS + NAS SYNC");
        LinearLayout actions = new LinearLayout(this);
        actions.addView(button("Lock", () -> lockNow("Vault locked.")),new LinearLayout.LayoutParams(0,-2,1));
        if (!sampleMode) actions.addView(button("Sync now", () -> { if (nasSettings.exists()) refreshNas(true); else configureNas(); }),new LinearLayout.LayoutParams(0,-2,1));
        root.addView(actions);
        LinearLayout editing = new LinearLayout(this);
        editing.addView(button("New entry", () -> openEditor(new JSONObject())),new LinearLayout.LayoutParams(0,-2,1));
        Button more = new Button(this); more.setText("More"); more.setAllCaps(false);
        more.setOnClickListener(v -> {
            PopupMenu menu = new PopupMenu(this,more);
            menu.getMenu().add("NAS connection settings"); menu.getMenu().add("Export encrypted phone backup");
            menu.setOnMenuItemClickListener(item -> {
                if ("NAS connection settings".contentEquals(item.getTitle())) configureNas(); else chooseExport();
                return true;
            }); menu.show();
        });
        if (!sampleMode) editing.addView(more,new LinearLayout.LayoutParams(0,-2,1));
        root.addView(editing);
        search = input("Search description, username or website", false); root.addView(search);
        status = label("", 14); root.addView(status);
        ScrollView scroll = new ScrollView(this); rows = column(); scroll.addView(rows);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
        renderRows(result);
        search.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                final int request = ++searchVersion;
                final int token = generation; final String query = s.toString();
                for(int i=0;i<rows.getChildCount();i++) rows.getChildAt(i).setEnabled(false);
                handler.postDelayed(() -> {
                    if (!unlocked || request != searchVersion || token != generation) return;
                    filterEntries(query,request,token);
                }, 200);
            }
            public void afterTextChanged(Editable s) {}
        });
    }
    private void filterEntries(String query,int request,int token) {
        worker.execute(() -> {
            String result=null; boolean failed=false;
            try { if(token==generation) result=bridge().callAttr("list_entries",query).toString(); } catch(Exception e){failed=true;}
            final String value=result; final boolean error=failed;
            handler.post(() -> {
                if(token!=generation || request!=searchVersion || !unlocked || !resumed || isFinishing())return;
                if(error){lockNow("The vault could not be checked. Please unlock again.");return;}
                try{renderRows(value);}catch(Exception e){lockNow("Cannot read this vault. Import a valid encrypted copy.");}
            });
        });
    }
    private void renderRows(String value) throws Exception {
        JSONArray records = new JSONArray(value); rows.removeAllViews();
        status.setText(records.length() + (records.length() == 1 ? " entry" : " entries") + " · Tap an entry to open it");
        if (records.length() == 0) rows.addView(label("No matching entries.", 17));
        for (int i = 0; i < records.length(); i++) {
            JSONObject record = records.getJSONObject(i);
            String id = record.getString("id");
            String text = record.getString("description") + "\n" + record.optString("user_name") + "\n••••••••";
            Button row = button(text, () -> openEntry(id));
            row.setGravity(android.view.Gravity.START | android.view.Gravity.CENTER_VERTICAL);
            row.setPadding(dp(16), dp(12), dp(16), dp(12)); rows.addView(row);
        }
    }
    private void openEntry(String id) {
        if (!unlocked || busy || nasRunning) return;
        job(() -> bridge().callAttr("detail", id).toString(), value -> {
            JSONObject record = new JSONObject(value);
            LinearLayout panel = column(); panel.setPadding(dp(24), dp(8), dp(24), dp(8));
            panel.addView(label("Username: " + record.optString("user_name"), 17));
            TextView website = label(record.optString("link"), 15); panel.addView(website);
            TextView secret = label("••••••••", 24); panel.addView(secret);
            Button reveal = button("Show password", () -> {
                boolean showing = "Hide password".contentEquals(((Button)panel.getChildAt(3)).getText());
                secret.setText(showing ? "••••••••" : record.optString("password"));
                ((Button)panel.getChildAt(3)).setText(showing ? "Show password" : "Hide password");
                resetIdleTimer();
            });
            panel.addView(reveal);
            panel.addView(button("Copy password", () -> copyValue(record.optString("password"))));
            panel.addView(button("Copy username", () -> copyValue(record.optString("user_name"))));
            panel.addView(button("Edit entry", () -> { if (detailDialog != null) detailDialog.dismiss(); openEditor(record); }));
            panel.addView(button("Delete entry", () -> confirmDelete(record)));
            if (!record.optString("notes").isEmpty()) panel.addView(label(record.optString("notes"), 16));
            ScrollView scroll = new ScrollView(this); scroll.addView(panel);
            detailDialog = new AlertDialog.Builder(this).setTitle(record.optString("description"))
                .setView(scroll).setPositiveButton("Done", null).create();
            detailDialog.setOnDismissListener(dialog -> { secret.setText(""); panel.removeAllViews(); detailDialog = null; });
            detailDialog.show(); detailDialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        }, "Cannot open this entry. Please unlock again.");
    }
    private void copyValue(String value) {
        ClipboardManager clipboard = (ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
        ownedClip = "Wormwright " + UUID.randomUUID();
        ClipData data = ClipData.newPlainText(ownedClip, value);
        PersistableBundle extras = new PersistableBundle(); extras.putBoolean("android.content.extra.IS_SENSITIVE", true);
        data.getDescription().setExtras(extras); clipboard.setPrimaryClip(data);
        handler.removeCallbacks(clipClear); handler.postDelayed(clipClear, 30000);
        status.setText("Copied. Clears after 30 seconds or when you lock."); resetIdleTimer();
    }
    private void clearOwnedClipboard() {
        if (ownedClip == null) return;
        ClipboardManager clipboard = (ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
        ClipDescription description = clipboard.getPrimaryClipDescription();
        if (description != null && ownedClip.contentEquals(description.getLabel())) clipboard.clearPrimaryClip();
        ownedClip = null; handler.removeCallbacks(clipClear);
    }
    private void chooseImport() {
        if (busy) return;
        if (vaultFile.exists()) {
            new AlertDialog.Builder(this).setTitle("Replace phone copy?")
                .setMessage("Choose an encrypted database or backup from Linux. Sync pending phone edits first; export a backup if sync needs Manager review. Importing replaces the phone copy and requires a fresh NAS pairing.")
                .setNegativeButton("Cancel", null).setPositiveButton("Choose file", (d,w) -> picker()).show();
        } else picker();
    }
    private void picker() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.setType("*/*"); intent.addCategory(Intent.CATEGORY_OPENABLE);
        startActivityForResult(intent, IMPORT);
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (result != RESULT_OK || data == null || data.getData() == null) return;
        final Uri uri = data.getData();
        if (request == EXPORT) { handler.post(() -> exportDocument(uri)); return; }
        if (request != IMPORT) return;
        // onActivityResult can precede onResume; defer until the Activity is resumed.
        handler.post(() -> importDocument(uri));
    }
    private void importDocument(Uri uri) {
        if (busy) return;
        status.setText("Checking encrypted vault copy…");
        job(() -> {
            File temporary = new File(getNoBackupFilesDir(), "import-" + UUID.randomUUID() + ".tmp");
            try {
                try (InputStream input = getContentResolver().openInputStream(uri);
                     FileOutputStream output = new FileOutputStream(temporary)) {
                    if (input == null) throw new Exception("No input");
                    byte[] buffer = new byte[65536]; int count; long length = 0;
                    while ((count = input.read(buffer)) != -1) {
                        length += count; if (length > 64L * 1024 * 1024) throw new Exception("File too large");
                        output.write(buffer, 0, count);
                    }
                    output.getFD().sync();
                }
                String info = bridge().callAttr("validate_file", temporary.getAbsolutePath()).toString();
                bridge().callAttr("import_snapshot", temporary.getAbsolutePath(), vaultFile.getAbsolutePath());
                return info;
            } finally { temporary.delete(); }
        }, result -> showLogin(new JSONObject(result).getBoolean("personal")
                ? "Imported. Enter your vault password; account name can stay blank."
                : "Imported. Enter the same account name and password you use on Linux."),
            "Import stopped. Sync pending edits first, and choose a valid encrypted format-2 vault (up to 64 MB). The previous copy is unchanged.");
    }
    private void loadSample() {
        if (busy) return;
        if (vaultFile.exists()) {
            new AlertDialog.Builder(this).setTitle("Try the sample?")
                .setMessage("The sample is separate from your phone vault. It contains only invented entries.")
                .setNegativeButton("Cancel", null).setPositiveButton("Open sample", (d,w) -> openSample()).show();
        } else openSample();
    }
    private void openSample() {
        status.setText("Opening the invented sample entries…");
        job("Opening vault…", () -> {
            File sample = new File(getNoBackupFilesDir(), "sample.db");
            try (InputStream input = getAssets().open("sample-vault.db"); FileOutputStream output = new FileOutputStream(sample)) {
                byte[] buffer = new byte[65536]; int count;
                while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
            }
            return bridge().callAttr("unlock", sample.getAbsolutePath(), "Demo", "SampleOnly-October2026!", true, true).toString();
        }, result -> { unlocked = true; sampleMode = true; showEntries(result); status.setText("SAMPLE VAULT · Invented entries only"); resetIdleTimer(); },
            "Sample vault could not open on this device. The real phone copy is unchanged.");
    }
    private void resetIdleTimer() {
        handler.removeCallbacks(idleLock); if (unlocked) handler.postDelayed(idleLock, 120000);
    }
    @Override public void onUserInteraction() { super.onUserInteraction(); resetIdleTimer(); }
    private void lockNow(String message) {
        ++generation; ++searchVersion; unlocked = false; nasRunning = false; setBusy(false, "");
        handler.removeCallbacks(idleLock); handler.removeCallbacks(nasPoll); clearOwnedClipboard();
        if (detailDialog != null) detailDialog.dismiss();
        if (nasDialog != null) nasDialog.dismiss();
        if (editorDialog != null) editorDialog.dismiss();
        if (conflictDialog != null) conflictDialog.dismiss();
        conflictReview = null; conflictChoices = null;
        if (password != null) password.getText().clear();
        worker.execute(() -> { try { bridge().callAttr("lock"); } catch (Exception ignored) {} });
        showLogin(message);
    }

    private void configureNas() {
        if (busy || nasRunning) return;
        job(() -> {
            JSONObject saved = nasSettings.load();
            return saved == null ? "{}" : saved.toString();
        }, value -> showNasDialog(new JSONObject(value)), "Could not read NAS settings. Please try again.");
    }
    private void showNasDialog(JSONObject saved) {
        LinearLayout form = column(); form.setPadding(dp(20), dp(8), dp(20), dp(8));
        form.addView(label("Syncs phone and NAS changes. Credentials stay on this phone. The NAS account needs permission to write the vault, backups and shared sync lock.", 15));
        EditText host = input("NAS address", false); host.setText(saved.optString("host", "192.168.1.144"));
        EditText share = input("Share name", false); share.setText(saved.optString("share", "share"));
        EditText folder = input("Folder within share", false); folder.setText(saved.optString("folder", "PasswordVault/Dans-Vault"));
        EditText user = input("NAS username", false); user.setText(saved.optString("user"));
        EditText domain = input("Domain / workgroup (optional)", false); domain.setText(saved.optString("domain"));
        EditText pass = input(saved.has("password") ? "NAS password (blank keeps saved password)" : "NAS password", true);
        form.addView(label("NAS address", 14)); form.addView(host);
        form.addView(label("Share", 14)); form.addView(share);
        form.addView(label("Vault folder", 14)); form.addView(folder);
        form.addView(user); form.addView(domain); form.addView(pass);
        TextView notice = label("Use your NAS login, which may differ from your vault password.", 14); form.addView(notice);
        ScrollView scroll = new ScrollView(this); scroll.addView(form);
        nasDialog = new AlertDialog.Builder(this).setTitle("NAS connection").setView(scroll)
                .setNegativeButton("Cancel", null).setPositiveButton("Save", null)
                .setNeutralButton("Forget login", (d,w) -> {
                    job(() -> { nasSettings.clear(); return ""; }, ignored -> {
                        handler.removeCallbacks(nasPoll); status.setText("NAS login removed. Your encrypted phone vault is unchanged.");
                    }, "Could not remove NAS settings.");
                }).create();
        nasDialog.setOnDismissListener(d -> { pass.getText().clear(); saved.remove("password"); form.removeAllViews(); nasDialog = null; });
        nasDialog.show(); nasDialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        nasDialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
            try {
                String secret = pass.getText().toString();
                if (secret.isEmpty()) secret = saved.optString("password");
                if (host.getText().toString().trim().isEmpty() || share.getText().toString().trim().isEmpty()
                    || user.getText().toString().trim().isEmpty() || secret.isEmpty()) {
                    notice.setText("Enter the NAS address, share, username and password."); return;
                }
                JSONObject values = new JSONObject();
                values.put("host", host.getText().toString().trim()); values.put("share", share.getText().toString().trim());
                values.put("folder", folder.getText().toString().trim()); values.put("user", user.getText().toString().trim());
                values.put("domain", domain.getText().toString().trim()); values.put("password", secret);
                nasDialog.dismiss();
                job(() -> { try { nasSettings.save(values); return ""; } finally { values.remove("password"); } }, ignored -> {
                    if (unlocked && !sampleMode) {
                        handler.removeCallbacks(nasPoll); refreshNas(true); handler.postDelayed(nasPoll, 60000);
                    } else showLogin("NAS login saved. Unlock your vault to sync with NAS.");
                }, "Could not save the NAS login. Please try again.");
            } catch (Exception ignored) { notice.setText("Could not save those connection details."); }
        });
    }
    private void chooseExport() {
        if (busy || nasRunning || sampleMode) return;
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.setType("application/octet-stream"); intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.putExtra(Intent.EXTRA_TITLE, "Wormwright-Vault-phone-backup.sqlite");
        startActivityForResult(intent, EXPORT);
    }
    private void exportDocument(Uri uri) {
        job(() -> {
            File temporary = File.createTempFile("export-", ".sqlite", getNoBackupFilesDir());
            try {
                bridge().callAttr("encrypted_backup", vaultFile.getAbsolutePath(), temporary.getAbsolutePath());
                try (InputStream input = new java.io.FileInputStream(temporary);
                     java.io.OutputStream output = getContentResolver().openOutputStream(uri,"wt")) {
                    if (output == null) throw new Exception("No output");
                    byte[] buffer = new byte[65536]; int n;
                    while ((n=input.read(buffer)) != -1) output.write(buffer,0,n);
                    output.flush();
                }
                return "";
            } finally { temporary.delete(); }
        }, ignored -> showLogin("Encrypted phone backup exported."), "Could not export the backup. Your phone copy is preserved.");
    }
    private void openEditor(JSONObject record) {
        if (!unlocked || busy || nasRunning || conflictReview != null) return;
        job(() -> bridge().callAttr("editing_info").toString(), value -> {
            JSONObject info = new JSONObject(value);
            if (!info.getBoolean("can_edit")) { status.setText("Complete the first NAS sync before editing."); return; }
            LinearLayout form=column(); form.setPadding(dp(20),dp(8),dp(20),dp(8));
            String[] names={"description","link","user_name","password","notes"};
            String[] labels={"Description","Website","Username","Password","Notes"};
            EditText[] fields=new EditText[names.length];
            for(int i=0;i<names.length;i++) {
                form.addView(label(labels[i],14)); fields[i]=input(labels[i],i==3);
                fields[i].setText(record.optString(names[i]));
                if(i==4) { fields[i].setSingleLine(false); fields[i].setMinLines(3); }
                form.addView(fields[i]);
            }
            JSONObject groups=info.getJSONObject("groups");
            java.util.ArrayList<String> ids=new java.util.ArrayList<>();
            java.util.Iterator<String> keys=groups.keys(); while(keys.hasNext()) ids.add(keys.next());
            boolean[] selected=new boolean[ids.size()]; JSONArray assigned=record.optJSONArray("groups");
            for(int i=0;i<ids.size();i++) {
                if(assigned!=null) for(int j=0;j<assigned.length();j++) if(ids.get(i).equals(assigned.getString(j))) selected[i]=true;
                else {} // Existing assignments are preserved below for ordinary accounts.
                if(assigned==null) selected[i]=!info.getBoolean("manager") || "Generic".equals(groups.getString(ids.get(i)));
            }
            if(info.getBoolean("manager") || !record.has("id")) {
                form.addView(label("Groups",14));
                for(int i=0;i<ids.size();i++) {
                    final int index=i; android.widget.CheckBox check=new android.widget.CheckBox(this);
                    check.setText(groups.getString(ids.get(i))); check.setChecked(selected[i]);
                    check.setOnCheckedChangeListener((v,on)->{ selected[index]=on; resetIdleTimer(); }); form.addView(check);
                }
            }
            TextView notice=label("Changes are saved on this phone before syncing.",14); form.addView(notice);
            ScrollView scroll=new ScrollView(this); scroll.addView(form);
            final int token=generation;
            AlertDialog dialog=new AlertDialog.Builder(this).setTitle(record.has("id")?"Edit entry":"New entry")
                .setView(scroll).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();
            editorDialog=dialog;
            dialog.setOnDismissListener(d->{ for(EditText field:fields) field.getText().clear(); form.removeAllViews(); if(editorDialog==dialog) editorDialog=null; });
            dialog.show(); dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
                if(token!=generation || !unlocked) return;
                try {
                    JSONObject document=new JSONObject();
                    if(record.has("id")) document.put("id",record.getString("id"));
                    for(int i=0;i<names.length;i++) document.put(names[i],fields[i].getText().toString());
                    if(document.getString("description").trim().isEmpty()) { notice.setText("Enter a description."); return; }
                    JSONArray chosen=new JSONArray();
                    if(!info.getBoolean("manager") && assigned!=null) chosen=assigned;
                    else for(int i=0;i<ids.size();i++) if(selected[i]) chosen.put(ids.get(i));
                    if(chosen.length()==0) { notice.setText("Choose at least one group."); return; }
                    document.put("groups",chosen); dialog.dismiss();
                    final String query=search.getText().toString();
                    job(()->{ bridge().callAttr("save_entry",document.toString()); return bridge().callAttr("list_entries",query).toString(); },
                        result->{ renderRows(result); status.setText("Saved on this phone."); resetIdleTimer(); if(!sampleMode && nasSettings.exists()) refreshNas(true); },
                        "Could not save this entry. Check your permissions and unlock again.");
                } catch(Exception ignored) { notice.setText("Check the entry details."); }
            });
        },"Could not open the editor. Please unlock again.");
    }
    private void confirmDelete(JSONObject record) {
        if(busy || nasRunning || !unlocked) return;
        if(detailDialog!=null) detailDialog.dismiss();
        final int token=generation;
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Delete entry?")
            .setMessage("Delete this entry from the phone and sync the deletion to NAS? The Manager can restore deleted entries on Linux.")
            .setNegativeButton("Cancel",null).setPositiveButton("Delete",(d,w)->{
                if(token!=generation || !unlocked) return;
                final String query=search.getText().toString();
                job(()->{ bridge().callAttr("delete_entry",record.getString("id")); return bridge().callAttr("list_entries",query).toString(); },
                    result->{ renderRows(result); status.setText("Deleted on this phone."); if(!sampleMode && nasSettings.exists()) refreshNas(true); },
                    "Could not delete this entry. Check your permissions and unlock again.");
            }).create();
        editorDialog=dialog; dialog.setOnDismissListener(d->{if(editorDialog==dialog) editorDialog=null;});
        dialog.show(); dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
    }
    private void reviewConflict(int index) throws Exception {
        if(conflictReview==null || !unlocked) return;
        JSONArray conflicts=conflictReview.getJSONArray("conflicts");
        if(index==conflicts.length()) {
            String choices=conflictChoices.toString(), expected=conflictReview.getJSONArray("expected").toString();
            conflictReview=null; conflictChoices=null; refreshNas(true,choices,expected); return;
        }
        JSONObject item=conflicts.getJSONObject(index); final int token=generation;
        String message="Phone: "+item.getString("phone")+(item.optBoolean("phone_deleted")?" (deleted)":"")+
            "\nNAS: "+item.getString("nas")+(item.optBoolean("nas_deleted")?" (deleted)":"")+"\nChoose the version to keep.";
        android.content.DialogInterface.OnClickListener choose=(d,w)->{
            if(token!=generation || conflictReview==null || !unlocked) return;
            try { conflictChoices.put(item.getString("id"),w==AlertDialog.BUTTON_POSITIVE?"local":"shared"); reviewConflict(index+1); }
            catch(Exception ignored) { conflictReview=null; conflictChoices=null; status.setText("Sync again to review conflicts."); }
        };
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Conflict "+(index+1)+" of "+conflicts.length())
            .setMessage(message).setPositiveButton("Keep phone",choose).setNegativeButton("Keep NAS",choose)
            .setNeutralButton("Cancel",(d,w)->{conflictReview=null; conflictChoices=null; status.setText("Sync paused. Both copies are preserved.");}).create();
        dialog.setCancelable(false); conflictDialog=dialog;
        dialog.setOnDismissListener(d->{if(conflictDialog==dialog) conflictDialog=null;});
        dialog.show(); dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
    }
    private void refreshNas(boolean manual) { refreshNas(manual,"",""); }
    private void refreshNas(boolean manual,String choices,String expected) {
        if(!unlocked || sampleMode || !resumed || busy || nasRunning || editorDialog!=null || conflictReview!=null) return;
        if(detailDialog!=null) { if(manual) detailDialog.dismiss(); else return; }
        nasRunning=true; updateProgress(); final int token=generation; final String query=search.getText().toString();
        status.setText("Syncing encrypted vault with NAS…");
        worker.execute(()->{
            JSONObject result=new JSONObject(); File directory=null;
            java.util.function.BooleanSupplier current=()->token==generation && resumed && unlocked;
            try {
                JSONObject settings=nasSettings.load(); if(settings==null) throw new Exception("No settings");
                try {
                    directory=Files.createTempDirectory(getNoBackupFilesDir().toPath(),"nas-sync-").toFile();
                    final String endpoint=settings.getString("host")+"/"+settings.getString("share")+"/"+settings.getString("folder").replace('\\','/');
                    result=NasClient.synchronize(settings,directory,new NasClient.SyncHandler(){
                        public JSONObject prepare(File remote,File output) throws Exception {
                            return new JSONObject(bridge().callAttr("prepare_sync",remote.getAbsolutePath(),vaultFile.getAbsolutePath(),output.getAbsolutePath(),endpoint,choices,expected).toString());
                        }
                        public void checkLocal() { bridge().callAttr("ensure_sync_current"); }
                        public JSONObject commit() throws Exception { return new JSONObject(bridge().callAttr("commit_sync",current.getAsBoolean()).toString()); }
                    },current);
                } finally { settings.remove("password"); }
                if(!result.has("ready") || result.optBoolean("ready")) {
                    result.put("ok",true);
                    if(!result.optBoolean("revoked") && current.getAsBoolean()) result.put("entries",bridge().callAttr("list_entries",query).toString());
                }
            } catch(Exception error) {
                try { result.put("ok",false); result.put("message",error instanceof NasClient.Failure?((NasClient.Failure)error).userMessage:"Sync stopped. Your phone edits are preserved. Retry after unlocking.");
                    result.put("session_ready",bridge().callAttr("session_ready").toBoolean()); } catch(Exception ignored) {}
            } finally {
                try { bridge().callAttr("abort_sync"); } catch(Exception ignored) {}
                if(directory!=null) { File[] files=directory.listFiles(); if(files!=null) for(File file:files) file.delete(); directory.delete(); }
            }
            final JSONObject response=result;
            handler.post(()->{
                if(token!=generation || !resumed || isFinishing()) return; nasRunning=false; updateProgress();
                try {
                    if(response.has("ready") && !response.getBoolean("ready")) {
                        status.setText(response.getString("message"));
                        if(response.optJSONArray("conflicts")!=null && response.getJSONArray("conflicts").length()>0) {
                            conflictReview=response; conflictChoices=new JSONObject(); reviewConflict(0);
                        }
                    } else if(!response.optBoolean("ok")) {
                        if(!response.optBoolean("session_ready")) lockNow("Sync stopped. Unlock to continue."); else status.setText(response.getString("message"));
                    } else if(response.optBoolean("revoked")) lockNow(response.getString("message"));
                    else { if(query.equals(search.getText().toString())) renderRows(response.getString("entries")); status.setText(response.getString("message")); }
                } catch(Exception ignored) { lockNow("Please unlock your vault again."); }
            });
        });
    }
    @Override protected void onResume() { super.onResume(); resumed = true; }
    @Override protected void onPause() {
        resumed = false; lockNow("Vault locked. Unlock to continue."); super.onPause();
    }
    @Override public void onBackPressed() {
        if (unlocked) lockNow("Vault locked."); else super.onBackPressed();
    }
    @Override protected void onDestroy() {
        handler.removeCallbacksAndMessages(null); clearOwnedClipboard();
        worker.shutdown(); super.onDestroy();
    }
}

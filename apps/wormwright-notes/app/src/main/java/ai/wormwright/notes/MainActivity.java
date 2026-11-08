package ai.wormwright.notes;

import android.app.*;
import android.hardware.biometrics.BiometricPrompt;
import android.hardware.biometrics.BiometricManager;
import android.view.inputmethod.EditorInfo;
import android.os.*;
import android.content.*;
import android.database.Cursor;
import android.database.sqlite.*;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.*;
import android.widget.*;
import android.text.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class MainActivity extends Activity {
    SQLiteDatabase db;
    HardwareBackupUi backupHardware;
    HardwareBackupUi hardwareBackups(){if(backupHardware==null)backupHardware=new HardwareBackupUi(this);return backupHardware;}
    NoteCipher secretCipher=new NoteCipher(new PhoneSecrets());
    boolean currentSecret=false, resumed=false, authenticating=false;
    long unlockedId=-1, draftId=-1;
    String draftTitle, draftBody;
    CancellationSignal credentialSignal;
    Runnable afterCredential;
    File pendingExport;
    int credentialGeneration=0;
    long accessEpoch=0,credentialEpoch=-1;

    LinearLayout root, cards;
    EditText title, body;
    TextView status;
    LinearLayout checklist;
    ScrollView checklistScroll;
    boolean checklistMode=false;
    long editing = -1;
    boolean trash = false, loading = false;
    String query = "";
    final Handler handler = new Handler();
    final Runnable saveLater = () -> save();
    int ink = Color.rgb(30,49,43), green = Color.rgb(36,101,86);

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        db = new SQLiteOpenHelper(this,"notes.db",null,2) {
            public void onCreate(SQLiteDatabase d) { d.execSQL("CREATE TABLE notes (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,body TEXT NOT NULL,pinned INTEGER NOT NULL DEFAULT 0,deleted INTEGER NOT NULL DEFAULT 0,updated INTEGER NOT NULL,secret INTEGER NOT NULL DEFAULT 0)"); }
            public void onConfigure(SQLiteDatabase d) { try(Cursor c=d.rawQuery("PRAGMA secure_delete=ON",null)){c.moveToFirst();} }
            public void onUpgrade(SQLiteDatabase d,int old,int next) {
                if(old==1&&next==2)d.execSQL("ALTER TABLE notes ADD COLUMN secret INTEGER NOT NULL DEFAULT 0");
                else throw new IllegalStateException("Unsupported database upgrade");
            }
        }.getWritableDatabase();
        if(state!=null) { editing=state.getLong("editing",-1); trash=state.getBoolean("trash"); query=state.getString("query","");
            String name=state.getString("pendingExport");
            if(name!=null&&name.matches("notes-export-[a-f0-9-]+\\.tmp"))pendingExport=new File(getCacheDir(),name);
        }
        if(editing!=-1) editor(editing); else home();
    }
    int dp(int n) { return (int)(getResources().getDisplayMetrics().density*n); }
    LinearLayout column() { LinearLayout l=new LinearLayout(this); l.setOrientation(1); return l; }
    TextView label(String s,int size) { TextView t=new TextView(this); t.setText(s);t.setTextSize(size);t.setTextColor(ink);t.setPadding(0,dp(8),0,dp(8));return t; }
    Button button(String s,Runnable action) { Button b=new Button(this);b.setText(s);b.setAllCaps(false);b.setTextColor(green);b.setOnClickListener(v->action.run());return b; }
    void shell() {
        root=column(); root.setPadding(dp(20),dp(12),dp(20),dp(12));root.setBackgroundColor(0xffF5F3ED);
        root.setOnApplyWindowInsetsListener((v,i)-> { root.setPadding(dp(20),dp(12)+i.getSystemWindowInsetTop(),dp(20),dp(12)+i.getSystemWindowInsetBottom()); return i; });
        setContentView(root);
    }
    void home() {
        handler.removeCallbacks(saveLater); editing=-1; unlockedId=-1; currentSecret=false; title=null; body=null; shell();
        allowPublicScreenshotsAfterFrame();
        TextView heading=label(trash?"Trash":"Wormwright Notes",32);heading.setTypeface(null,Typeface.BOLD);root.addView(heading);
        root.addView(label(trash?"Restore notes or remove them permanently.":"A little space for your thoughts.",15));
        LinearLayout actions=new LinearLayout(this);
        actions.addView(button(trash?"Back to notes":"+ New note",()->{if(trash){trash=false;home();}else new AlertDialog.Builder(this).setTitle("Create").setItems(new String[]{"Note","Checklist"},(d,n)->{editor(-1);if(n==1){body.setText("[ ] ");checklistMode=true;showChecklist();save();}}).show();}));
        actions.addView(button("More",()->new AlertDialog.Builder(this).setItems(new String[]{"Back up all notes","Restore backup","Open trash","About","NAS settings","Save backup to NAS","YubiKey backup keys"},(d,n)->{
            if(n==0)startBackup(false);
            if(n==1) startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*"),11);
            if(n==2){trash=true;home();}
            if(n==4)nasSettings();
            if(n==5)startBackup(true);
            if(n==6)hardwareBackups().manage();
            if(n==3)new AlertDialog.Builder(this).setTitle("Wormwright Notes").setMessage("No ads. No purchases. No account.\n\nNotes stay in this app on your phone. Use backup to keep a separate copy. Uninstalling removes local notes.\n\nVersion 0.1.0-preview.4").setPositiveButton("OK",null).show();
        }).show()));root.addView(actions);
        EditText search=new EditText(this);search.setSingleLine();search.setHint("Search notes");search.setText(query);root.addView(search);
        ScrollView scroll=new ScrollView(this);cards=column();scroll.addView(cards);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        search.addTextChangedListener(watcher(()->{query=search.getText().toString();renderNotes();}));renderNotes();
    }
    void renderNotes() {
        cards.removeAllViews();
        try(Cursor c=db.rawQuery("SELECT id,title,body,pinned,updated,secret FROM notes WHERE deleted=? AND ((secret=1 AND ?='') OR (secret=0 AND (instr(lower(title),lower(?))>0 OR instr(lower(body),lower(?))>0))) ORDER BY pinned DESC,updated DESC",new String[]{trash?"1":"0",query,query,query})) {
            if(c.getCount()==0) cards.addView(label(query.isEmpty()?(trash?"Your trash is empty.":"Your first note starts here.\nTap + New note to begin."):"No matching notes.",18));
            while(c.moveToNext()) {
                long id=c.getLong(0);boolean locked=c.getInt(5)==1;LinearLayout card=column();card.setPadding(dp(16),dp(8),dp(16),dp(12));
                GradientDrawable bg=new GradientDrawable();bg.setColor(Color.WHITE);bg.setCornerRadius(dp(16));card.setBackground(bg);
                LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.setMargins(0,dp(12),0,0);cards.addView(card,lp);
                TextView name=label((c.getInt(3)==1?"★  ":"")+(locked?"🔒 Secret note":(c.getString(1).isEmpty()?"Untitled note":c.getString(1))),20);name.setTypeface(null,Typeface.BOLD);card.addView(name);
                TextView preview=label(locked?"Tap to unlock with your phone screen lock":c.getString(2),15);preview.setMaxLines(3);card.addView(preview);
                card.addView(label(android.text.format.DateFormat.format("MMM d, yyyy · h:mm a",c.getLong(4)).toString(),12));
                card.setOnClickListener(v->{if(trash) trashActions(id);else editor(id);});
            }
        }
    }
    TextWatcher watcher(Runnable r) { return new TextWatcher(){public void beforeTextChanged(CharSequence s,int a,int c,int f){}public void onTextChanged(CharSequence s,int a,int b,int c){r.run();}public void afterTextChanged(Editable e){}}; }
    void editor(long id) {
        boolean secret=isSecret(id);
        if(secret&&unlockedId!=id){home();requestCredential(()->{unlockedId=id;editor(id);});return;}
        String noteTitle="",noteBody="";
        if(id!=-1)try(Cursor c=db.rawQuery("SELECT title,body FROM notes WHERE id=?",new String[]{""+id})){
            if(!c.moveToFirst()){home();return;}
            if(secret){try{JSONObject content=new JSONObject(secretCipher.decrypt(id,c.getString(1)));noteTitle=content.getString("title");noteBody=content.getString("body");}
                catch(Exception e){home();toast("Could not unlock this secret note. Restore a password-protected backup if its phone key was lost.");return;}}
            else{noteTitle=c.getString(0);noteBody=c.getString(1);}
        }
        if(secret&&draftId==id){noteTitle=draftTitle;noteBody=draftBody;}
        currentSecret=secret;editing=id;
        if(secret)getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        else { /* Clear only after the new public frame is committed. */ }
        shell();if(!secret)allowPublicScreenshotsAfterFrame(); LinearLayout actions=new LinearLayout(this);
        actions.addView(button("‹ Notes",()->{if(save())home();}));actions.addView(button("Options",()->options()));root.addView(actions);
        title=new EditText(this);title.setHint("Title");title.setTextSize(28);title.setTypeface(null,Typeface.BOLD);title.setBackgroundColor(Color.TRANSPARENT);root.addView(title);
        body=new EditText(this);body.setHint("Write something…");body.setGravity(Gravity.TOP);body.setTextSize(18);body.setBackgroundColor(Color.TRANSPARENT);body.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE|android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        root.addView(body,new LinearLayout.LayoutParams(-1,0,1));
        checklistScroll=new ScrollView(this);checklist=column();checklistScroll.addView(checklist);root.addView(checklistScroll,new LinearLayout.LayoutParams(-1,0,1));
        checklistMode=false;
        status=label(secret?"Secret · locks when you leave this note":"Saved on this phone",12);root.addView(status);
        loading=true;
        title.setText(noteTitle);body.setText(noteBody);
        if(secret){privateInput(title);privateInput(body);}
        loading=false;
        checklistMode=body.getText().toString().startsWith("[ ] ")||body.getText().toString().startsWith("[x] ");
        showChecklist();
        TextWatcher w=watcher(()->{if(!loading){status.setText("Saving…");handler.removeCallbacks(saveLater);handler.postDelayed(saveLater,400);}});title.addTextChangedListener(w);body.addTextChangedListener(w);
    }
    boolean save() {
        handler.removeCallbacks(saveLater);if(editing==-1&&title==null)return true;
        if(title==null||body==null)return true;
        if(editing==-1&&title.length()==0&&body.length()==0)return true;
        try{if(currentSecret&&unlockedId!=editing)return false;
            ContentValues v=new ContentValues();String textTitle=title.getText().toString(),textBody=body.getText().toString();
            if(currentSecret){v.put("title","");v.put("body",secretCipher.encrypt(editing,new JSONObject().put("title",textTitle).put("body",textBody).toString()));}
            else{v.put("title",textTitle);v.put("body",textBody);}
            v.put("updated",System.currentTimeMillis());
            if(editing==-1)editing=db.insertOrThrow("notes",null,v);else db.update("notes",v,"id=?",new String[]{""+editing});status.setText(currentSecret?"Secret · saved on this phone":"Saved on this phone");if(draftId==editing){draftId=-1;draftTitle=null;draftBody=null;}return true;
        }catch(Exception e){status.setText("Could not save. Keep this note open.");return false;}
    }
    void options() {
        new AlertDialog.Builder(this).setItems(new String[]{"Pin / unpin","Share text","Move to trash", "Checklist / plain text",currentSecret?"Make public":"Make secret", "Lock now"},(d,n)->{
            if(title==null||body==null||!save())return;
            if(n==0&&editing!=-1){db.execSQL("UPDATE notes SET pinned=1-pinned WHERE id=?",new Object[]{editing});Toast.makeText(this,"Pin updated",Toast.LENGTH_SHORT).show();}
            if(n==1)shareNote();
            if(n==4){if(currentSecret)confirmMakePublic();else confirmMakeSecret();}
            if(n==5){if(currentSecret)concealSecret();else toast("This note is not secret");}
            if(n==3){checklistMode=!checklistMode;if(checklistMode){String text=body.getText().toString();StringBuilder b=new StringBuilder();for(String line:text.split("\n",-1)){if(b.length()>0)b.append("\n");b.append(line.startsWith("[ ] ")||line.startsWith("[x] ")?line:"[ ] "+line);}body.setText(b.toString());}if(!checklistMode){body.setText(body.getText().toString().replaceAll("(?m)^\\[(?: |x)\\] ",""));}showChecklist();save();}
            if(n==2){if(editing!=-1)db.execSQL("UPDATE notes SET deleted=1 WHERE id=?",new Object[]{editing});title=null;body=null;home();}
        }).show();
    }

    void showChecklist(){
        body.setVisibility(checklistMode?View.GONE:View.VISIBLE);
        checklistScroll.setVisibility(checklistMode?View.VISIBLE:View.GONE);
        if(!checklistMode)return;
        checklist.removeAllViews();
        String text=body.getText().toString();
        String[] lines=text.isEmpty()?new String[]{"[ ] "}:text.split("\n",-1);
        for(int i=0;i<lines.length;i++){
            final int index=i;String line=lines[i];boolean checked=line.startsWith("[x] ");
            LinearLayout row=new LinearLayout(this);row.setGravity(Gravity.CENTER_VERTICAL);
            CheckBox box=new CheckBox(this);box.setChecked(checked);box.setContentDescription("Mark item complete");row.addView(box);
            EditText item=new EditText(this);item.setText(line.startsWith("[ ] ")||checked?line.substring(4):line);item.setTextSize(18);item.setSingleLine(true);if(currentSecret)privateInput(item);
            row.addView(item,new LinearLayout.LayoutParams(0,-2,1));
            row.addView(button("×",()->{ArrayList<String> a=new ArrayList<>(Arrays.asList(body.getText().toString().split("\n",-1)));a.remove(index);body.setText(a.isEmpty()?"[ ] ":String.join("\n",a));showChecklist();save();}));
            box.setOnCheckedChangeListener((b,on)->{setItem(index,(on?"[x] ":"[ ] ")+item.getText());save();});
            item.addTextChangedListener(watcher(()->setItem(index,(box.isChecked()?"[x] ":"[ ] ")+item.getText())));
            checklist.addView(row);
        }
        checklist.addView(button("+ Add item",()->{body.append("\n[ ] ");showChecklist();LinearLayout row=(LinearLayout)checklist.getChildAt(checklist.getChildCount()-2);row.getChildAt(1).requestFocus();((android.view.inputmethod.InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showSoftInput(row.getChildAt(1),0);}));
    }
    void setItem(int index,String value){String[] a=body.getText().toString().split("\n",-1);if(index<a.length){a[index]=value;body.setText(String.join("\n",a));}}

    void trashActions(long id) {new AlertDialog.Builder(this).setItems(new String[]{"Restore note","Delete forever"},(d,n)->{
        if(n==0){db.execSQL("UPDATE notes SET deleted=0 WHERE id=?",new Object[]{id});renderNotes();}
        else new AlertDialog.Builder(this).setTitle("Delete this note forever?").setMessage("This cannot be undone.").setNegativeButton("Cancel",null).setPositiveButton("Delete",(x,y)->{db.delete("notes","id=?",new String[]{""+id});renderNotes();}).show();
    }).show();}
    @Override public void onBackPressed(){if(editing!=-1||title!=null){if(save()){title=null;body=null;home();}}else if(trash){trash=false;home();}else super.onBackPressed();}
    @Override protected void onPause(){
        boolean usbOverlay=backupHardware!=null&&backupHardware.pauseForUsbPermission();
        resumed=false;if(!usbOverlay)accessEpoch++;
        if(backupHardware!=null&&!usbOverlay)backupHardware.stop();
        if(currentSecret)concealSecret();else if(title!=null)save();
        if(!authenticating)afterCredential=null;
        super.onPause();
    }
    @Override protected void onResume(){
        super.onResume();resumed=true;if(backupHardware!=null)backupHardware.resume();if(!currentSecret)allowPublicScreenshotsAfterFrame();
        Runnable action=afterCredential;afterCredential=null;
        if(action!=null&&!((KeyguardManager)getSystemService(KEYGUARD_SERVICE)).isKeyguardLocked()){credentialEpoch=accessEpoch;action.run();}
    }
    @Override protected void onStop(){accessEpoch++;if(backupHardware!=null)backupHardware.stop();super.onStop();}
    @Override protected void onDestroy(){
        if(backupHardware!=null)backupHardware.dispose();
        credentialGeneration++;afterCredential=null;
        if(credentialSignal!=null)credentialSignal.cancel();
        handler.removeCallbacksAndMessages(null);super.onDestroy();
    }
    @Override protected void onSaveInstanceState(Bundle b){
        if(title!=null)save();
        b.putLong("editing",currentSecret?-1:editing);b.putBoolean("trash",trash);b.putString("query",query);
        if(pendingExport!=null)b.putString("pendingExport",pendingExport.getName());
        super.onSaveInstanceState(b);
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request==10){
            File export=pendingExport;pendingExport=null;
            try{if(result!=RESULT_OK)return;if(export==null||!export.isFile()||data==null||data.getData()==null)throw new IOException();
                try(InputStream in=new FileInputStream(export);OutputStream out=getContentResolver().openOutputStream(data.getData())){
                    if(out==null)throw new IOException();byte[] buf=new byte[8192];int count;while((count=in.read(buf))!=-1)out.write(buf,0,count);
                }toast("Backup saved");
            }catch(Exception e){toast("Could not save this backup. Please try again.");}finally{if(export!=null)export.delete();}
            return;
        }
        if(request!=11||result!=RESULT_OK||data==null||data.getData()==null)return;
        try{ByteArrayOutputStream bytes=new ByteArrayOutputStream();try(InputStream in=getContentResolver().openInputStream(data.getData())){
            if(in==null)throw new IOException();byte[] buf=new byte[8192];int count;
            while((count=in.read(buf))!=-1){if(bytes.size()+count>20*1024*1024)throw new IOException();bytes.write(buf,0,count);}}
            byte[] backup=bytes.toByteArray();
            if(KeyBackupEnvelope.isEncrypted(backup))hardwareBackups().restore(backup);
            else if(BackupEnvelope.isEncrypted(backup))passwordDialog(false,password->runBackupTask(()->{
                try{return BackupEnvelope.decrypt(backup,password);}finally{Arrays.fill(password,'\0');}
            },plain->offerRestore(plain,true)));
            else offerRestore(backup,false);
        }catch(Exception e){toast("Could not read this backup");}
    }
    void nasSettings(){
        JSONObject old;try{old=new NasSettings(this).load();}catch(Exception e){toast("Could not read saved NAS settings");return;}
        if(old==null)old=new JSONObject();final JSONObject saved=old;
        LinearLayout form=column();form.setPadding(dp(20),0,dp(20),0);
        form.addView(label("Same connection defaults as Wormwright Vault. Enter your NAS login once for Notes. Backups are separate JSON files; they do not change your vault.",14));
        String[] keys={"host","share","folder","user","domain","password"};
        String[] names={"NAS address","Share name","Folder within share","Username","Domain (optional)","Password"};
        String[] defaults={"192.168.1.144","share","PasswordVault/Dans-Vault","","",""};
        EditText[] fields=new EditText[keys.length];
        for(int i=0;i<keys.length;i++){form.addView(label(names[i],14));fields[i]=new EditText(this);fields[i].setSingleLine();fields[i].setText(saved.optString(keys[i],defaults[i]));if(i==5)fields[i].setInputType(129);form.addView(fields[i]);}
        ScrollView sc=new ScrollView(this);sc.addView(form);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("NAS settings").setView(sc).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();
        dialog.setOnShowListener(x->dialog.getButton(-1).setOnClickListener(v->{try{JSONObject settings=new JSONObject();for(int i=0;i<keys.length;i++)settings.put(keys[i],i==5?fields[i].getText().toString():fields[i].getText().toString().trim());if(settings.getString("host").isEmpty()||settings.getString("share").isEmpty()||settings.getString("user").isEmpty()){toast("Enter address, share and username");return;}new NasSettings(this).save(settings);dialog.dismiss();toast("NAS settings saved on this phone");}catch(Exception e){toast("Could not save NAS settings");}}));dialog.show();
    }
    boolean isSecret(long id){
        if(id<0)return false;
        try(Cursor c=db.rawQuery("SELECT secret FROM notes WHERE id=?",new String[]{""+id})){return c.moveToFirst()&&c.getInt(0)==1;}
    }
    boolean hasSecrets(){try(Cursor c=db.rawQuery("SELECT 1 FROM notes WHERE secret=1 LIMIT 1",null)){return c.moveToFirst();}}
    boolean screenLockAvailable(){return Build.VERSION.SDK_INT>=30&&((KeyguardManager)getSystemService(KEYGUARD_SERVICE)).isDeviceSecure();}
    void requestCredential(Runnable success){
        if(!screenLockAvailable()){toast("Secret notes need Android 11 or later and a phone PIN, pattern or password. Set your screen lock in phone Settings.");return;}
        if(authenticating)return;
        authenticating=true;afterCredential=null;int generation=++credentialGeneration;
        credentialSignal=new CancellationSignal();
        try{
            new BiometricPrompt.Builder(this).setTitle("Unlock secret notes")
                .setDescription("Use your phone PIN, pattern or password")
                .setAllowedAuthenticators(BiometricManager.Authenticators.DEVICE_CREDENTIAL).build()
                .authenticate(credentialSignal,getMainExecutor(),new BiometricPrompt.AuthenticationCallback(){
                    @Override public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult result){
                        if(generation!=credentialGeneration||isDestroyed()||isFinishing())return;
                        authenticating=false;credentialSignal=null;
                        if(resumed){credentialEpoch=accessEpoch;success.run();}else afterCredential=success;
                    }
                    @Override public void onAuthenticationError(int error,CharSequence message){
                        if(generation!=credentialGeneration)return;
                        authenticating=false;credentialSignal=null;afterCredential=null;
                    }
                });
        }catch(Exception e){authenticating=false;credentialSignal=null;toast("Could not open your phone screen-lock prompt");}
    }
    void allowPublicScreenshotsAfterFrame(){
        if(!resumed||currentSecret||root==null)return;
        final View publicRoot=root;
        if(Build.VERSION.SDK_INT>=29){
            // Keep the last secret surface protected until a public frame replaces it.
            publicRoot.getViewTreeObserver().registerFrameCommitCallback(()->handler.post(()->{
                if(resumed&&!currentSecret&&root==publicRoot)getWindow().clearFlags(WindowManager.LayoutParams.FLAG_SECURE);
            }));
            publicRoot.invalidate();
        }
    }
    void privateInput(EditText input){
        input.setSaveEnabled(false);input.setSaveFromParentEnabled(false);
        input.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);
        input.setInputType(input.getInputType()|android.text.InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        input.setImeOptions(input.getImeOptions()|EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING);
    }
    void concealSecret(){
        if(!currentSecret)return;
        if(!save()){draftId=editing;draftTitle=title.getText().toString();draftBody=body.getText().toString();toast("Could not save secret edits. Unlock this note again before closing the app.");}
        loading=true;title.setText("");body.setText("");if(checklist!=null)checklist.removeAllViews();loading=false;
        home();
    }
    void confirmMakeSecret(){
        new AlertDialog.Builder(this).setTitle("Make this note secret?")
            .setMessage("Its title and text will be hidden until you enter your phone screen lock. It locks again when you leave it. Backups that contain secret notes need a separate backup password or a registered YubiKey. Older backups remain unchanged.")
            .setNegativeButton("Cancel",null).setPositiveButton("Make secret",(d,w)->{
                if(!save())return;
                if(editing==-1){ContentValues v=new ContentValues();v.put("title","");v.put("body","");v.put("updated",System.currentTimeMillis());editing=db.insertOrThrow("notes",null,v);}
                final long id=editing;
                requestCredential(()->{try{
                    makeSecret(id);home();toast("Secret note saved. Tap it to unlock.");
                }catch(Exception e){toast("Could not make this note secret; it is still public");}});
            }).show();
    }
    void makeSecret(long id)throws Exception{
        try(Cursor c=db.rawQuery("SELECT title,body,secret FROM notes WHERE id=?",new String[]{""+id})){
            if(!c.moveToFirst()||c.getInt(2)==1)return;
            String encrypted=secretCipher.encrypt(id,new JSONObject().put("title",c.getString(0)).put("body",c.getString(1)).toString());
            ContentValues values=new ContentValues();values.put("title","");values.put("body",encrypted);values.put("secret",1);
            db.update("notes",values,"id=?",new String[]{""+id});
        }
    }
    void confirmMakePublic(){
        if(!currentSecret||unlockedId!=editing)return;
        new AlertDialog.Builder(this).setTitle("Make this note public?").setMessage("Its title and text will display without your phone screen lock.")
            .setNegativeButton("Cancel",null).setPositiveButton("Make public",(d,w)->{
                if(!currentSecret||unlockedId!=editing||!save())return;
                ContentValues v=new ContentValues();v.put("title",title.getText().toString());v.put("body",body.getText().toString());v.put("secret",0);
                db.update("notes",v,"id=?",new String[]{""+editing});long id=editing;unlockedId=-1;editor(id);
            }).show();
    }
    void shareNote(){
        if(title==null||body==null||(currentSecret&&unlockedId!=editing))return;
        startActivity(Intent.createChooser(new Intent(Intent.ACTION_SEND).setType("text/plain")
            .putExtra(Intent.EXTRA_TEXT,title.getText()+"\n\n"+body.getText()),"Share note"));
    }
    byte[] backupBytes(boolean includeSecrets)throws Exception{
        boolean secretPresent=hasSecrets();if(secretPresent&&(!includeSecrets||!resumed||credentialEpoch!=accessEpoch))throw new SecurityException("Secret backup needs authentication and encryption");
        return snapshotBytes();
    }
    interface BackupProtection{byte[] seal(byte[] plain)throws Exception;}
    byte[] protectedBackup(BackupProtection protection)throws Exception{
        if(!resumed)throw new SecurityException("Backup needs the foreground app");
        byte[] plain=snapshotBytes();
        try{return protection.seal(plain);}finally{Arrays.fill(plain,(byte)0);}
    }
    private byte[] snapshotBytes()throws Exception{
        boolean secretPresent=hasSecrets();
        JSONObject backup=new JSONObject();backup.put("format",secretPresent?"wormwright-notes-v2":"wormwright-notes-v1");JSONArray notes=new JSONArray();
        try(Cursor c=db.rawQuery("SELECT id,title,body,pinned,deleted,updated,secret FROM notes",null)){
            while(c.moveToNext()){
                boolean secret=c.getInt(6)==1;JSONObject n;
                if(secret)n=new JSONObject(secretCipher.decrypt(c.getLong(0),c.getString(2)));
                else n=new JSONObject().put("title",c.getString(1)).put("body",c.getString(2));
                n.put("pinned",c.getInt(3));n.put("deleted",c.getInt(4));n.put("updated",c.getLong(5));n.put("secret",secret);notes.put(n);
            }
        }
        backup.put("notes",notes);return backup.toString().getBytes(StandardCharsets.UTF_8);
    }
    interface PasswordAction{void run(char[] password);}
    void passwordDialog(boolean confirm,PasswordAction action){
        LinearLayout form=column();form.setPadding(dp(20),0,dp(20),0);
        form.addView(label(confirm?"Use a separate backup password of at least 12 characters. Keep it safe: your phone PIN cannot restore this file on another phone.":"Enter this backup's password. It may be different from your phone PIN.",15));
        EditText password=new EditText(this);password.setHint("Backup password");password.setInputType(129);privateInput(password);form.addView(password);
        EditText again=new EditText(this);again.setHint("Confirm backup password");again.setInputType(129);privateInput(again);if(confirm)form.addView(again);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle(confirm?"Protect your backup":"Unlock backup").setView(form).setNegativeButton("Cancel",null).setPositiveButton(confirm?"Create backup":"Unlock",null).create();
        dialog.setOnShowListener(d->{dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);dialog.getButton(-1).setOnClickListener(v->{
            String value=password.getText().toString();
            if(confirm&&(value.length()<12||!value.equals(again.getText().toString()))){toast("Use at least 12 characters and match both passwords");return;}
            char[] chars=value.toCharArray();password.setText("");again.setText("");dialog.dismiss();action.run(chars);
        });});dialog.show();
    }
    interface BackupTask{byte[] run()throws Exception;}
    interface BytesAction{void run(byte[] bytes);}
    void runBackupTask(BackupTask task,BytesAction success){
        ProgressDialog progress=new ProgressDialog(this);progress.setMessage("Preparing protected backup…");progress.setCancelable(false);progress.show();
        new Thread(()->{try{byte[] bytes=task.run();runOnUiThread(()->{if(isDestroyed()||isFinishing())return;progress.dismiss();success.run(bytes);});}
            catch(Exception e){runOnUiThread(()->{if(isDestroyed()||isFinishing())return;progress.dismiss();toast("Could not unlock or prepare this backup. Check its password and file.");});}},"protected-backup").start();
    }
    void startBackup(boolean nas){
        Runnable choose=()->new AlertDialog.Builder(this).setTitle("Protect this backup")
            .setItems(hasSecrets()?new String[]{"Password","YubiKey"}:new String[]{"Password","YubiKey","Plain JSON"},(d,n)->{
                if(n==0)passwordBackup(nas);
                else if(n==1)hardwareBackups().createBackup(nas);
                else try{deliverBackup(backupBytes(false),nas,false);}catch(Exception e){toast("Could not prepare backup");}
            }).setNegativeButton("Cancel",null).show();
        choose.run();
    }
    void passwordBackup(boolean nas){
        passwordDialog(true,password->{
            long epoch=accessEpoch;
            runBackupTask(()->{try{return protectedBackup(plain->BackupEnvelope.encrypt(plain,password));}finally{Arrays.fill(password,'\0');}},
                bytes->{if(resumed&&accessEpoch==epoch)deliverBackup(bytes,nas,true);else Arrays.fill(bytes,(byte)0);});
        });
    }
    boolean nasBusy=false;
    void deliverBackup(byte[] bytes,boolean nas,boolean protectedBackup){
        if(bytes.length>20*1024*1024){toast("This backup exceeds the 20 MB limit");return;}
        if(nas){
            if(nasBusy){toast("A NAS backup is already running");return;}
            try{JSONObject settings=new NasSettings(this).load();if(settings==null){toast("Save your NAS settings first, then create the backup again");nasSettings();return;}
                nasBusy=true;toast("Saving backup to NAS…");
                new Thread(()->{try{String path=NasBackup.upload(settings,bytes);runOnUiThread(()->{nasBusy=false;if(!isDestroyed()&&!isFinishing())new AlertDialog.Builder(this).setTitle("NAS backup saved").setMessage(path).setPositiveButton("OK",null).show();});}
                    catch(Exception e){runOnUiThread(()->{nasBusy=false;if(!isDestroyed()&&!isFinishing())new AlertDialog.Builder(this).setTitle("NAS backup failed").setMessage("Your phone notes are safe. Check Wi-Fi, address, login, folder and write permissions, then try again.").setPositiveButton("OK",null).show();});}},"nas-backup").start();
            }catch(Exception e){toast("Could not prepare NAS backup");}
        }else try{
            if(pendingExport!=null)pendingExport.delete();pendingExport=File.createTempFile("notes-export-"+UUID.randomUUID(),".tmp",getCacheDir());
            try(OutputStream out=new FileOutputStream(pendingExport)){out.write(bytes);}
            startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                .setType(protectedBackup?"application/octet-stream":"application/json")
                .putExtra(Intent.EXTRA_TITLE,protectedBackup?"wormwright-notes-backup.wwnotes":"wormwright-notes-backup.json"),10);
        }catch(Exception e){if(pendingExport!=null)pendingExport.delete();pendingExport=null;toast("Could not prepare backup file");}
    }
    void offerRestore(byte[] bytes,boolean encrypted){offerRestore(bytes,encrypted,()->{});}
    void offerRestore(byte[] bytes,boolean encrypted,Runnable afterRestore){
        try{JSONObject backup=new JSONObject(new String(bytes,StandardCharsets.UTF_8));String format=backup.getString("format");
            if(!"wormwright-notes-v1".equals(format)&&!(encrypted&&"wormwright-notes-v2".equals(format)))throw new IOException();
            JSONArray notes=backup.getJSONArray("notes");boolean secrets=false;
            for(int i=0;i<notes.length();i++){JSONObject n=notes.getJSONObject(i);n.getString("title");n.getString("body");n.getInt("pinned");n.getInt("deleted");n.getLong("updated");
                if(n.optBoolean("secret",false)){if(!encrypted)throw new IOException();secrets=true;}}
            Runnable confirm=()->new AlertDialog.Builder(this).setTitle("Restore "+notes.length()+" notes?")
                .setMessage("These will be added to your existing notes. Secret notes remain secret. Restoring the same backup again creates duplicates.")
                .setNegativeButton("Cancel",null).setPositiveButton("Restore",(d,w)->{
                    try{restoreNotes(notes);home();toast("Notes restored");afterRestore.run();}catch(Exception e){toast("Restore failed; no notes added");}
                }).show();
            if(secrets&&!screenLockAvailable()){toast("Set a phone screen lock before restoring secret notes. It will be used when you open them.");return;}
            confirm.run();
        }catch(Exception e){toast("Could not read this backup");}finally{Arrays.fill(bytes,(byte)0);}
    }
    void restoreNotes(JSONArray notes)throws Exception{
        db.beginTransaction();try{
            for(int i=0;i<notes.length();i++){
                JSONObject n=notes.getJSONObject(i);boolean secret=n.optBoolean("secret",false);ContentValues v=new ContentValues();
                v.put("title",secret?"":n.getString("title"));v.put("body",secret?"":n.getString("body"));
                v.put("pinned",n.getInt("pinned")==1?1:0);v.put("deleted",n.getInt("deleted")==1?1:0);v.put("updated",n.getLong("updated"));v.put("secret",secret?1:0);
                long id=db.insertOrThrow("notes",null,v);
                if(secret){ContentValues sealed=new ContentValues();sealed.put("body",secretCipher.encrypt(id,new JSONObject().put("title",n.getString("title")).put("body",n.getString("body")).toString()));db.update("notes",sealed,"id=?",new String[]{""+id});}
            }db.setTransactionSuccessful();
        }finally{db.endTransaction();}
    }
    void toast(String s){Toast.makeText(this,s,Toast.LENGTH_LONG).show();}
}

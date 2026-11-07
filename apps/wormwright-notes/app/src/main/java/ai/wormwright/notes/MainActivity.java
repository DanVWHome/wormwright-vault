package ai.wormwright.notes;

import android.app.*;
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
        db = new SQLiteOpenHelper(this,"notes.db",null,1) {
            public void onCreate(SQLiteDatabase d) { d.execSQL("CREATE TABLE notes (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,body TEXT NOT NULL,pinned INTEGER NOT NULL DEFAULT 0,deleted INTEGER NOT NULL DEFAULT 0,updated INTEGER NOT NULL)"); }
            public void onUpgrade(SQLiteDatabase d,int old,int next) { throw new IllegalStateException("Unsupported database upgrade"); }
        }.getWritableDatabase();
        if(state!=null) { editing=state.getLong("editing",-1); trash=state.getBoolean("trash"); query=state.getString("query",""); }
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
        editing=-1; title=null; body=null; shell();
        TextView heading=label(trash?"Trash":"Wormwright Notes",32);heading.setTypeface(null,Typeface.BOLD);root.addView(heading);
        root.addView(label(trash?"Restore notes or remove them permanently.":"A little space for your thoughts.",15));
        LinearLayout actions=new LinearLayout(this);
        actions.addView(button(trash?"Back to notes":"+ New note",()->{if(trash){trash=false;home();}else new AlertDialog.Builder(this).setTitle("Create").setItems(new String[]{"Note","Checklist"},(d,n)->{editor(-1);if(n==1){body.setText("[ ] ");checklistMode=true;showChecklist();save();}}).show();}));
        actions.addView(button("More",()->new AlertDialog.Builder(this).setItems(new String[]{"Back up all notes","Restore backup","Open trash","About","NAS settings","Save backup to NAS"},(d,n)->{
            if(n==0) startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("application/json").putExtra(Intent.EXTRA_TITLE,"wormwright-notes-backup.json"),10);
            if(n==1) startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*"),11);
            if(n==2){trash=true;home();}
            if(n==4)nasSettings();
            if(n==5)nasBackup();
            if(n==3)new AlertDialog.Builder(this).setTitle("Wormwright Notes").setMessage("No ads. No purchases. No account.\n\nNotes stay in this app on your phone. Use backup to keep a separate copy. Uninstalling removes local notes.\n\nVersion 0.1.0-preview.2").setPositiveButton("OK",null).show();
        }).show()));root.addView(actions);
        EditText search=new EditText(this);search.setSingleLine();search.setHint("Search notes");search.setText(query);root.addView(search);
        ScrollView scroll=new ScrollView(this);cards=column();scroll.addView(cards);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        search.addTextChangedListener(watcher(()->{query=search.getText().toString();renderNotes();}));renderNotes();
    }
    void renderNotes() {
        cards.removeAllViews();
        try(Cursor c=db.rawQuery("SELECT id,title,body,pinned,updated FROM notes WHERE deleted=? AND (instr(lower(title),lower(?))>0 OR instr(lower(body),lower(?))>0) ORDER BY pinned DESC,updated DESC",new String[]{trash?"1":"0",query,query})) {
            if(c.getCount()==0) cards.addView(label(query.isEmpty()?(trash?"Your trash is empty.":"Your first note starts here.\nTap + New note to begin."):"No matching notes.",18));
            while(c.moveToNext()) {
                long id=c.getLong(0);LinearLayout card=column();card.setPadding(dp(16),dp(8),dp(16),dp(12));
                GradientDrawable bg=new GradientDrawable();bg.setColor(Color.WHITE);bg.setCornerRadius(dp(16));card.setBackground(bg);
                LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.setMargins(0,dp(12),0,0);cards.addView(card,lp);
                TextView name=label((c.getInt(3)==1?"★  ":"")+(c.getString(1).isEmpty()?"Untitled note":c.getString(1)),20);name.setTypeface(null,Typeface.BOLD);card.addView(name);
                TextView preview=label(c.getString(2),15);preview.setMaxLines(3);card.addView(preview);
                card.addView(label(android.text.format.DateFormat.format("MMM d, yyyy · h:mm a",c.getLong(4)).toString(),12));
                card.setOnClickListener(v->{if(trash) trashActions(id);else editor(id);});
            }
        }
    }
    TextWatcher watcher(Runnable r) { return new TextWatcher(){public void beforeTextChanged(CharSequence s,int a,int c,int f){}public void onTextChanged(CharSequence s,int a,int b,int c){r.run();}public void afterTextChanged(Editable e){}}; }
    void editor(long id) {
        editing=id;shell(); LinearLayout actions=new LinearLayout(this);
        actions.addView(button("‹ Notes",()->{if(save())home();}));actions.addView(button("Options",()->options()));root.addView(actions);
        title=new EditText(this);title.setHint("Title");title.setTextSize(28);title.setTypeface(null,Typeface.BOLD);title.setBackgroundColor(Color.TRANSPARENT);root.addView(title);
        body=new EditText(this);body.setHint("Write something…");body.setGravity(Gravity.TOP);body.setTextSize(18);body.setBackgroundColor(Color.TRANSPARENT);body.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE|android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        root.addView(body,new LinearLayout.LayoutParams(-1,0,1));
        checklistScroll=new ScrollView(this);checklist=column();checklistScroll.addView(checklist);root.addView(checklistScroll,new LinearLayout.LayoutParams(-1,0,1));
        checklistMode=false;
        status=label("Saved on this phone",12);root.addView(status);
        loading=true;
        if(id!=-1)try(Cursor c=db.rawQuery("SELECT title,body FROM notes WHERE id=?",new String[]{""+id})){if(c.moveToFirst()){title.setText(c.getString(0));body.setText(c.getString(1));}}
        loading=false;
        checklistMode=body.getText().toString().startsWith("[ ] ")||body.getText().toString().startsWith("[x] ");
        showChecklist();
        TextWatcher w=watcher(()->{if(!loading){status.setText("Saving…");handler.removeCallbacks(saveLater);handler.postDelayed(saveLater,400);}});title.addTextChangedListener(w);body.addTextChangedListener(w);
    }
    boolean save() {
        handler.removeCallbacks(saveLater);if(editing==-1&&title==null)return true;
        if(title==null||body==null)return true;
        if(editing==-1&&title.length()==0&&body.length()==0)return true;
        try{ContentValues v=new ContentValues();v.put("title",title.getText().toString());v.put("body",body.getText().toString());v.put("updated",System.currentTimeMillis());
            if(editing==-1)editing=db.insertOrThrow("notes",null,v);else db.update("notes",v,"id=?",new String[]{""+editing});status.setText("Saved on this phone");return true;
        }catch(Exception e){status.setText("Could not save. Keep this note open.");return false;}
    }
    void options() {
        new AlertDialog.Builder(this).setItems(new String[]{"Pin / unpin","Share text","Move to trash", "Checklist / plain text"},(d,n)->{
            if(!save())return;
            if(n==0&&editing!=-1){db.execSQL("UPDATE notes SET pinned=1-pinned WHERE id=?",new Object[]{editing});Toast.makeText(this,"Pin updated",Toast.LENGTH_SHORT).show();}
            if(n==1)startActivity(Intent.createChooser(new Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT,title.getText()+"\n\n"+body.getText()),"Share note"));
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
            EditText item=new EditText(this);item.setText(line.startsWith("[ ] ")||checked?line.substring(4):line);item.setTextSize(18);item.setSingleLine(true);
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
    @Override protected void onPause(){if(title!=null)save();super.onPause();}
    @Override protected void onSaveInstanceState(Bundle b){if(title!=null)save();b.putLong("editing",editing);b.putBoolean("trash",trash);b.putString("query",query);super.onSaveInstanceState(b);}
    @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(result!=RESULT_OK||data==null||data.getData()==null)return;
        try{
            if(request==10){byte[] snapshot=backupBytes();try(OutputStream o=getContentResolver().openOutputStream(data.getData())){if(o==null)throw new IOException();o.write(snapshot);}toast("Backup saved");
            }else if(request==11){ByteArrayOutputStream bytes=new ByteArrayOutputStream();try(InputStream in=getContentResolver().openInputStream(data.getData())){if(in==null)throw new IOException();byte[] buf=new byte[8192];int n;while((n=in.read(buf))!=-1){if(bytes.size()+n>20*1024*1024)throw new IOException("Backup too large");bytes.write(buf,0,n);}}
                JSONObject backup=new JSONObject(bytes.toString("UTF-8"));if(!"wormwright-notes-v1".equals(backup.getString("format")))throw new IOException();JSONArray notes=backup.getJSONArray("notes");
                ArrayList<ContentValues> values=new ArrayList<>();for(int i=0;i<notes.length();i++){JSONObject n=notes.getJSONObject(i);ContentValues v=new ContentValues();v.put("title",n.getString("title"));v.put("body",n.getString("body"));v.put("pinned",n.getInt("pinned")==1?1:0);v.put("deleted",n.getInt("deleted")==1?1:0);v.put("updated",n.getLong("updated"));values.add(v);}
                new AlertDialog.Builder(this).setTitle("Restore "+values.size()+" notes?").setMessage("These will be added to your existing notes. Restoring the same backup again creates duplicates.").setNegativeButton("Cancel",null).setPositiveButton("Restore",(d,w)->{try{db.beginTransaction();try{for(ContentValues v:values)db.insertOrThrow("notes",null,v);db.setTransactionSuccessful();}finally{db.endTransaction();}home();toast("Notes restored");}catch(Exception e){toast("Restore failed; no notes added");}}).show();
            }
        }catch(Exception e){toast("Could not read or write this backup");}
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
    byte[] backupBytes() throws Exception{
        JSONObject backup=new JSONObject();backup.put("format","wormwright-notes-v1");JSONArray notes=new JSONArray();
        try(Cursor c=db.rawQuery("SELECT title,body,pinned,deleted,updated FROM notes",null)){while(c.moveToNext()){JSONObject n=new JSONObject();n.put("title",c.getString(0));n.put("body",c.getString(1));n.put("pinned",c.getInt(2));n.put("deleted",c.getInt(3));n.put("updated",c.getLong(4));notes.put(n);}}
        backup.put("notes",notes);return backup.toString(2).getBytes(StandardCharsets.UTF_8);
    }
    boolean nasBusy=false;
    void nasBackup(){
        if(nasBusy){toast("A NAS backup is already running");return;}
        try{JSONObject settings=new NasSettings(this).load();if(settings==null){nasSettings();return;}byte[] snapshot=backupBytes();nasBusy=true;toast("Saving backup to NAS…");
            new Thread(()->{try{String path=NasBackup.upload(settings,snapshot);runOnUiThread(()->{nasBusy=false;new AlertDialog.Builder(this).setTitle("NAS backup saved").setMessage(path).setPositiveButton("OK",null).show();});}catch(Exception e){runOnUiThread(()->{nasBusy=false;new AlertDialog.Builder(this).setTitle("NAS backup failed").setMessage("Your phone notes are safe. Check Wi-Fi, address, login, folder and write permissions, then try again.").setPositiveButton("OK",null).show();});}},"nas-backup").start();
        }catch(Exception e){toast("Could not prepare NAS backup");}
    }
    void toast(String s){Toast.makeText(this,s,Toast.LENGTH_LONG).show();}
}

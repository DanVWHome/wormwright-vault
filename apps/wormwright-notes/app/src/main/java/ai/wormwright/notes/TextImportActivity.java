package ai.wormwright.notes;

import android.app.*;
import android.content.*;
import android.database.sqlite.SQLiteDatabase;
import android.graphics.Color;
import android.os.Bundle;
import android.text.*;
import android.view.*;
import android.widget.*;

/** Receiving shared text only opens an editable review. Explicit Save inserts one public row. */
public final class TextImportActivity extends Activity {
    EditText title,text;RadioGroup kind;RadioButton note,list;TextView preview;Button save;boolean saving=false;
    int dp(int value){return (int)(getResources().getDisplayMetrics().density*value);}
    TextView label(String value,int size){TextView v=new TextView(this);v.setText(value);v.setTextSize(size);v.setTextColor(0xff1e312b);v.setPadding(0,dp(8),0,dp(8));return v;}
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        LinearLayout root=new LinearLayout(this);root.setOrientation(1);root.setPadding(dp(20),dp(12),dp(20),dp(12));root.setBackgroundColor(0xffF5F3ED);
        root.setOnApplyWindowInsetsListener((v,insets)->{root.setPadding(dp(20),dp(12)+insets.getSystemWindowInsetTop(),dp(20),dp(12)+insets.getSystemWindowInsetBottom());return insets;});
        setContentView(root);root.addView(label("Save shared text",28));root.addView(label("Review the text, then choose how to save it. Nothing is saved until you tap Save.",15));
        ScrollView scroll=new ScrollView(this);LinearLayout form=new LinearLayout(this);form.setOrientation(1);scroll.addView(form);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        title=new EditText(this);title.setHint("Title (optional)");title.setSingleLine();title.setFilters(new InputFilter[]{new InputFilter.LengthFilter(ImportedText.MAX_TITLE)});form.addView(title);
        kind=new RadioGroup(this);kind.setOrientation(0);note=new RadioButton(this);note.setId(View.generateViewId());note.setText("Note");list=new RadioButton(this);list.setId(View.generateViewId());list.setText("Checklist");kind.addView(note);kind.addView(list);note.setChecked(true);form.addView(kind);
        form.addView(label("For a checklist, put one item on each line. You can correct handwriting or remove ChatGPT’s extra commentary here.",14));
        Button paste=new Button(this);paste.setAllCaps(false);paste.setText("Paste text");paste.setOnClickListener(v->paste());form.addView(paste);
        text=new EditText(this);text.setHint("Share text here, or paste a ChatGPT reply");text.setGravity(Gravity.TOP);text.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE|android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);text.setMinLines(5);text.setMaxLines(12);form.addView(text,new LinearLayout.LayoutParams(-1,-2));
        form.addView(label("Preview",18));preview=label("",16);form.addView(preview);
        form.addView(label("This creates a new non-secret note or checklist on this phone. Existing notes are unchanged. You can make it secret afterward in Options.",14));
        LinearLayout actions=new LinearLayout(this);Button cancel=new Button(this);cancel.setText("Cancel");cancel.setAllCaps(false);cancel.setOnClickListener(v->finish());actions.addView(cancel);save=new Button(this);save.setText("Save");save.setAllCaps(false);save.setOnClickListener(v->saveImport());actions.addView(save);root.addView(actions);
        if(state!=null){title.setText(state.getString("importTitle",""));text.setText(state.getString("importText",""));if(state.getBoolean("checklist"))list.setChecked(true);}
        else if(Intent.ACTION_SEND.equals(getIntent().getAction()))receive(getIntent());
        kind.setOnCheckedChangeListener((g,id)->refreshPreview());text.addTextChangedListener(new TextWatcher(){public void beforeTextChanged(CharSequence s,int start,int count,int after){}public void onTextChanged(CharSequence s,int start,int before,int count){refreshPreview();}public void afterTextChanged(Editable e){}});
        refreshPreview();getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN|WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
    }
    void receive(Intent intent){
        String type=intent.getType();if(!"text/plain".equals(type)&&!"text/markdown".equals(type)){message("Share plain text to import it into Notes");return;}
        CharSequence incoming=intent.getCharSequenceExtra(Intent.EXTRA_TEXT);if(incoming!=null&&incoming.length()>ImportedText.MAX_TEXT){message("This text is too large. Share a shorter passage.");return;}
        if(incoming!=null)text.setText(incoming.toString());
        String subject=intent.getStringExtra(Intent.EXTRA_SUBJECT);if(subject!=null&&subject.length()<=ImportedText.MAX_TITLE)title.setText(subject);
    }
    void paste(){
        android.content.ClipboardManager clipboard=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);ClipData clip=clipboard.getPrimaryClip();
        if(clip==null||clip.getItemCount()==0){message("Copy the text in ChatGPT first");return;}
        CharSequence value=clip.getItemAt(0).getText();if(value==null){message("The clipboard does not contain plain text");return;}
        if(value.length()>ImportedText.MAX_TEXT){message("This text is too large. Copy a shorter passage.");return;}text.setText(value);
    }
    void refreshPreview(){
        try{String value=ImportedText.body(text.getText().toString(),list.isChecked());
            String[] lines=value.split("\n",-1);StringBuilder shown=new StringBuilder();
            for(int i=0;i<Math.min(lines.length,8);i++){if(i>0)shown.append('\n');String line=lines[i];if(list.isChecked())line=(line.startsWith("[x] ")?"☑ ":"☐ ")+line.substring(4);shown.append(line.length()>180?line.substring(0,180)+"…":line);}
            if(lines.length>8)shown.append("\n… ").append(lines.length-8).append(" more lines");preview.setText(shown);save.setEnabled(!saving);
        }catch(IllegalArgumentException error){preview.setText(error.getMessage());save.setEnabled(false);}
    }
    void saveImport(){
        if(saving)return;
        try{boolean checklist=list.isChecked();String body=ImportedText.body(text.getText().toString(),checklist),name=ImportedText.title(title.getText().toString(),checklist);
            saving=true;save.setEnabled(false);SQLiteDatabase db=NotesDatabase.open(this);long id;
            try{ContentValues values=new ContentValues();values.put("title",name);values.put("body",body);values.put("pinned",0);values.put("deleted",0);values.put("updated",System.currentTimeMillis());values.put("secret",0);values.put("kind",checklist?1:0);id=db.insertOrThrow("notes",null,values);}finally{db.close();}
            startActivity(new Intent(this,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP).putExtra("open_imported_note",id));finish();
        }catch(Exception error){saving=false;refreshPreview();message(error instanceof IllegalArgumentException?error.getMessage():"Could not save. Your text is still here; try again.");}
    }
    @Override protected void onSaveInstanceState(Bundle state){state.putString("importTitle",title.getText().toString());state.putString("importText",text.getText().toString());state.putBoolean("checklist",list.isChecked());super.onSaveInstanceState(state);}
    void message(String value){Toast.makeText(this,value,Toast.LENGTH_LONG).show();}
}

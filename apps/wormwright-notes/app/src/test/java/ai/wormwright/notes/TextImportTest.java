package ai.wormwright.notes;
import android.content.*;
import android.database.Cursor;
import android.os.Bundle;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import org.robolectric.android.controller.ActivityController;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class) @Config(sdk=35)
public class TextImportTest {
 @Before public void reset(){RuntimeEnvironment.getApplication().deleteDatabase("notes.db");}
 Intent share(String text){return new Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT,text).putExtra(Intent.EXTRA_SUBJECT,"Groceries");}
 int count(){try(android.database.sqlite.SQLiteDatabase db=NotesDatabase.open(RuntimeEnvironment.getApplication());Cursor c=db.rawQuery("SELECT count(*) FROM notes",null)){c.moveToFirst();return c.getInt(0);}}
 @Test public void inboundShareAndCancelNeverWriteNotes(){
  try(ActivityController<TextImportActivity> c=Robolectric.buildActivity(TextImportActivity.class,share("Milk\nBread")).setup()){
   TextImportActivity a=c.get();assertEquals("Groceries",a.title.getText().toString());assertEquals(0,count());assertTrue(a.preview.getText().toString().contains("Milk"));a.finish();assertEquals(0,count());
  }
 }
 @Test public void checkedBulletsNumbersAndBlankLinesNormalizeWithoutDroppingWords(){
  assertEquals("[ ] Milk\n[x] Apples\n[ ] 2% milk\n[x] Bread\n[ ] Oat milk",ImportedText.body("- Milk\r\n* [x] Apples\r\n\r\n1. 2% milk\n☑ Bread\n• Oat milk",true));
  assertEquals("[x] Milk\n[ ] Bread",ImportedText.body("[X] Milk\n[ ] Bread",true));
  assertEquals("* Keep this formatting\n\n[ ] Literal text",ImportedText.body("* Keep this formatting\n\n[ ] Literal text",false));
 }
 @Test public void explicitNoteChoiceSurvivesCheckboxLookingBodyAndBackupRestore()throws Exception{
  long id;
  try(ActivityController<TextImportActivity> c=Robolectric.buildActivity(TextImportActivity.class,share("[ ] This is literal text")).setup()){
   TextImportActivity a=c.get();a.saveImport();assertEquals(1,count());a.saveImport();assertEquals(1,count());
   try(android.database.sqlite.SQLiteDatabase db=NotesDatabase.open(a);Cursor row=db.rawQuery("SELECT id,body,secret,kind FROM notes",null)){row.moveToFirst();id=row.getLong(0);assertEquals("[ ] This is literal text",row.getString(1));assertEquals(0,row.getInt(2));assertEquals(0,row.getInt(3));}
  }
  try(ActivityController<MainActivity> c=Robolectric.buildActivity(MainActivity.class).setup()){
   MainActivity a=c.get();a.editor(id);assertFalse(a.checklistMode);a.save();a.home();a.editor(id);assertFalse(a.checklistMode);
   org.json.JSONObject backup=new org.json.JSONObject(new String(a.backupBytes(false),java.nio.charset.StandardCharsets.UTF_8));a.restoreNotes(backup.getJSONArray("notes"));
   long last;try(Cursor row=a.db.rawQuery("SELECT max(id) FROM notes",null)){row.moveToFirst();last=row.getLong(0);}a.editor(last);assertFalse(a.checklistMode);
  }
 }
 @Test public void checklistReviewSavesOnlyAfterConfirmationAndPreservesTicks(){
  try(ActivityController<TextImportActivity> c=Robolectric.buildActivity(TextImportActivity.class,share("- Milk\n- [x] Bread")).setup()){
   TextImportActivity a=c.get();a.list.setChecked(true);assertEquals(0,count());assertTrue(a.preview.getText().toString().contains("☑ Bread"));a.title.setText("Family groceries");a.saveImport();assertEquals(1,count());
   try(android.database.sqlite.SQLiteDatabase db=NotesDatabase.open(a);Cursor row=db.rawQuery("SELECT title,body,kind,secret FROM notes",null)){row.moveToFirst();assertEquals("Family groceries",row.getString(0));assertEquals("[ ] Milk\n[x] Bread",row.getString(1));assertEquals(1,row.getInt(2));assertEquals(0,row.getInt(3));}
  }
 }
 @Test public void draftAndChoiceSurviveRecreationWithoutSaving(){
  try(ActivityController<TextImportActivity> c=Robolectric.buildActivity(TextImportActivity.class,share("Milk")).setup()){
   TextImportActivity a=c.get();a.list.setChecked(true);a.text.setText("Milk\nPears");a.title.setText("Edited title");Bundle state=new Bundle();a.onSaveInstanceState(state);
   try(ActivityController<TextImportActivity> restored=Robolectric.buildActivity(TextImportActivity.class,share("Old text")).create(state).start().resume().visible()){
    assertEquals("Milk\nPears",restored.get().text.getText().toString());assertEquals("Edited title",restored.get().title.getText().toString());assertTrue(restored.get().list.isChecked());assertEquals(0,count());
   }
  }
 }
 @Test public void emptyOversizedAndTooManyItemsAreRejectedWithoutDataLoss(){
  try(ActivityController<TextImportActivity> c=Robolectric.buildActivity(TextImportActivity.class,share(" ")).setup()){
   TextImportActivity a=c.get();assertFalse(a.save.isEnabled());a.saveImport();assertEquals(0,count());
   a.text.setText("x".repeat(ImportedText.MAX_TEXT+1));a.saveImport();assertEquals(0,count());assertEquals(ImportedText.MAX_TEXT+1,a.text.length());
  }
  try{ImportedText.body("Milk\n".repeat(1001),true);fail();}catch(IllegalArgumentException expected){}
 }
 @Test public void pasteReadsClipboardOnlyAfterAnExplicitTap(){
  ClipboardManager clipboard=(ClipboardManager)RuntimeEnvironment.getApplication().getSystemService(Context.CLIPBOARD_SERVICE);clipboard.setPrimaryClip(ClipData.newPlainText("ChatGPT","Milk\nEggs"));
  try(ActivityController<TextImportActivity> c=Robolectric.buildActivity(TextImportActivity.class).setup()){
   assertEquals("",c.get().text.getText().toString());c.get().paste();assertEquals("Milk\nEggs",c.get().text.getText().toString());assertEquals(0,count());
  }
 }
 @Test public void exportedShareTargetResolvesStandardTextIntent(){
  Intent intent=share("Milk").setPackage("ai.wormwright.notes");assertNotNull(RuntimeEnvironment.getApplication().getPackageManager().resolveActivity(intent,0));
 }
 @Test public void malformedShareCannotTargetOrOverwriteAnExistingNote(){
  try(android.database.sqlite.SQLiteDatabase db=NotesDatabase.open(RuntimeEnvironment.getApplication())){db.execSQL("INSERT INTO notes(title,body,updated,secret) VALUES('Locked title','opaque encrypted payload',1,1)");}
  try(ActivityController<TextImportActivity> c=Robolectric.buildActivity(TextImportActivity.class,share("Replace me").putExtra("id",1).putExtra("secret",true).putExtra("action","delete")).setup()){
   c.get().saveImport();assertEquals(2,count());
   try(android.database.sqlite.SQLiteDatabase db=NotesDatabase.open(c.get());Cursor row=db.rawQuery("SELECT title,body,secret FROM notes WHERE id=1",null)){row.moveToFirst();assertEquals("Locked title",row.getString(0));assertEquals("opaque encrypted payload",row.getString(1));assertEquals(1,row.getInt(2));}
  }
 }
}

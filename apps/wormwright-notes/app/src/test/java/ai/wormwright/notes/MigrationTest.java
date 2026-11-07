package ai.wormwright.notes;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class)
@Config(sdk=35)
public class MigrationTest {
 @Test public void upgradingPreview2KeepsPublicNotesPinsAndTrash(){
  android.app.Application app=RuntimeEnvironment.getApplication();app.deleteDatabase("notes.db");java.io.File file=app.getDatabasePath("notes.db");file.getParentFile().mkdirs();
  try(SQLiteDatabase old=SQLiteDatabase.openOrCreateDatabase(file,null)){
   old.execSQL("CREATE TABLE notes (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,body TEXT NOT NULL,pinned INTEGER NOT NULL DEFAULT 0,deleted INTEGER NOT NULL DEFAULT 0,updated INTEGER NOT NULL)");
   old.execSQL("INSERT INTO notes VALUES(42,'Old title','[x] milk',1,1,100)");old.setVersion(1);
  }
  try(org.robolectric.android.controller.ActivityController<MainActivity> c=Robolectric.buildActivity(MainActivity.class).setup()){
   MainActivity a=c.get();assertEquals(2,a.db.getVersion());
   try(Cursor row=a.db.rawQuery("SELECT id,title,body,pinned,deleted,secret FROM notes",null)){assertTrue(row.moveToFirst());assertEquals(42,row.getLong(0));assertEquals("Old title",row.getString(1));assertEquals("[x] milk",row.getString(2));assertEquals(1,row.getInt(3));assertEquals(1,row.getInt(4));assertEquals(0,row.getInt(5));}
  }
 }
}

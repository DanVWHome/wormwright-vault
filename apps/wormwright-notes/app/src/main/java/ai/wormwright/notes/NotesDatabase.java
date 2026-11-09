package ai.wormwright.notes;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.*;
/** Shared schema for the notes editor and explicit text-import review screen. */
final class NotesDatabase {
    static SQLiteDatabase open(Context context){
        return new SQLiteOpenHelper(context,"notes.db",null,3) {
            public void onCreate(SQLiteDatabase d) { d.execSQL("CREATE TABLE notes (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,body TEXT NOT NULL,pinned INTEGER NOT NULL DEFAULT 0,deleted INTEGER NOT NULL DEFAULT 0,updated INTEGER NOT NULL,secret INTEGER NOT NULL DEFAULT 0,kind INTEGER NOT NULL DEFAULT -1)"); }
            public void onConfigure(SQLiteDatabase d) { try(Cursor c=d.rawQuery("PRAGMA secure_delete=ON",null)){c.moveToFirst();} }
            public void onUpgrade(SQLiteDatabase d,int old,int next) {
                if(next!=3||old<1||old>2)throw new IllegalStateException("Unsupported database upgrade");
                if(old<2)d.execSQL("ALTER TABLE notes ADD COLUMN secret INTEGER NOT NULL DEFAULT 0");
                d.execSQL("ALTER TABLE notes ADD COLUMN kind INTEGER NOT NULL DEFAULT -1");
            }
        }.getWritableDatabase();
    }
}

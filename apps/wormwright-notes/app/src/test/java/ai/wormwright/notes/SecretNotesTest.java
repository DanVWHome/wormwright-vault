package ai.wormwright.notes;

import android.app.AlertDialog;
import android.content.ContentValues;
import android.content.Intent;
import android.database.Cursor;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.TextView;
import org.json.*;
import org.junit.*;
import static org.junit.Assert.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.android.controller.ActivityController;
import org.robolectric.annotation.Config;
import org.robolectric.shadows.ShadowAlertDialog;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;

@RunWith(RobolectricTestRunner.class)
@Config(sdk=35)
public class SecretNotesTest {
    public static class TestActivity extends MainActivity {
        Runnable requested;
        @Override void requestCredential(Runnable success){authenticating=true;requested=success;}
        void answerCredential(boolean success){Runnable action=requested;requested=null;authenticating=false;if(success&&action!=null){credentialEpoch=accessEpoch;action.run();}}
    }
    ActivityController<TestActivity> controller;
    TestActivity activity;
    static SecretKey key;
    @BeforeClass public static void createKey()throws Exception{KeyGenerator g=KeyGenerator.getInstance("AES");g.init(256);key=g.generateKey();}
    @Before public void setup(){
        RuntimeEnvironment.getApplication().deleteDatabase("notes.db");
        controller=Robolectric.buildActivity(TestActivity.class).setup();activity=controller.get();activity.secretCipher=new NoteCipher(()->key);
    }
    @After public void cleanup(){controller.pause().stop().destroy();}
    long note(String title,String body){activity.editor(-1);activity.title.setText(title);activity.body.setText(body);assertTrue(activity.save());return activity.editing;}
    long secret(String title,String body)throws Exception{long id=note(title,body);activity.makeSecret(id);activity.home();return id;}
    void unlock(long id){activity.editor(id);assertNotNull(activity.requested);activity.answerCredential(true);}
    String visible(View v){StringBuilder b=new StringBuilder();if(v instanceof TextView)b.append(((TextView)v).getText());if(v instanceof ViewGroup){ViewGroup g=(ViewGroup)v;for(int i=0;i<g.getChildCount();i++)b.append(' ').append(visible(g.getChildAt(i)));}return b.toString();}
    int count(){try(Cursor c=activity.db.rawQuery("SELECT count(*) FROM notes",null)){c.moveToFirst();return c.getInt(0);}}
    @Test public void secrecyRequiresCredentialAndCancelDoesNotReveal()throws Exception{
        long id=note("cabin code","blue watermelon");activity.confirmMakeSecret();
        ShadowAlertDialog.getLatestAlertDialog().getButton(AlertDialog.BUTTON_POSITIVE).performClick();Shadows.shadowOf(android.os.Looper.getMainLooper()).idle();
        assertNotNull(activity.requested);assertFalse(activity.isSecret(id));activity.answerCredential(false);assertFalse(activity.isSecret(id));
        activity.confirmMakeSecret();ShadowAlertDialog.getLatestAlertDialog().getButton(-1).performClick();Shadows.shadowOf(android.os.Looper.getMainLooper()).idle();activity.answerCredential(true);
        assertTrue(activity.isSecret(id));assertNull(activity.title);assertFalse(visible(activity.root).contains("watermelon"));
        activity.editor(id);activity.answerCredential(false);assertNull(activity.title);assertEquals(-1,activity.unlockedId);
    }
    @Test public void lockedTitleBodySearchAndTrashNeverRevealContent()throws Exception{
        long id=secret("cabin code","blue watermelon");
        try(Cursor c=activity.db.rawQuery("SELECT title,body FROM notes WHERE id=?",new String[]{""+id})){assertTrue(c.moveToFirst());assertEquals("",c.getString(0));assertFalse(c.getString(1).contains("watermelon"));}
        assertTrue(visible(activity.root).contains("Secret note"));assertFalse(visible(activity.root).contains("cabin code"));
        activity.query="watermelon";activity.renderNotes();assertFalse(visible(activity.cards).contains("Secret note"));assertTrue(visible(activity.cards).contains("No matching notes"));
        activity.db.execSQL("UPDATE notes SET deleted=1 WHERE id=?",new Object[]{id});activity.trash=true;activity.query="";activity.home();
        assertTrue(visible(activity.cards).contains("Secret note"));assertFalse(visible(activity.cards).contains("watermelon"));
    }
    @Test public void secretChecklistEditsSaveEncryptedAndRelockOnPause()throws Exception{
        long id=secret("shopping","[ ] milk\n[x] apples");unlock(id);assertTrue(activity.currentSecret);assertTrue(activity.checklistMode);
        activity.setItem(0,"[x] milk");assertTrue(activity.save());
        assertEquals(WindowManager.LayoutParams.FLAG_SECURE,activity.getWindow().getAttributes().flags&WindowManager.LayoutParams.FLAG_SECURE);
        assertFalse(activity.title.isSaveEnabled());assertFalse(activity.body.isSaveEnabled());
        controller.pause();assertNull(activity.title);assertEquals(-1,activity.unlockedId);assertFalse(visible(activity.root).contains("milk"));controller.resume();
        unlock(id);assertTrue(activity.body.getText().toString().startsWith("[x] milk"));
    }
    @Test public void unlockedSecretCanShareButLeavingLocksIt()throws Exception{
        long id=secret("private list","[ ] milk");unlock(id);activity.shareNote();
        Intent chooser=Shadows.shadowOf(activity).getNextStartedActivity();assertEquals(Intent.ACTION_CHOOSER,chooser.getAction());
        Intent send=chooser.getParcelableExtra(Intent.EXTRA_INTENT);assertEquals(Intent.ACTION_SEND,send.getAction());assertEquals("private list\n\n[ ] milk",send.getStringExtra(Intent.EXTRA_TEXT));
        controller.pause().resume();activity.shareNote();assertNull(Shadows.shadowOf(activity).getNextStartedActivity());assertNull(activity.title);
        activity.editor(id);assertNotNull(activity.requested);
    }
    @Test public void backAndRecreationDoNotKeepAnUnlock()throws Exception{
        long id=secret("private title","private content");unlock(id);
        Bundle state=new Bundle();activity.onSaveInstanceState(state);assertEquals(-1,state.getLong("editing"));
        activity.onBackPressed();assertNull(activity.title);activity.editor(id);assertNotNull(activity.requested);activity.answerCredential(false);
        controller.pause().stop().destroy();controller=Robolectric.buildActivity(TestActivity.class).create(state).start().resume().visible();activity=controller.get();activity.secretCipher=new NoteCipher(()->key);
        assertNull(activity.title);activity.editor(id);assertNotNull(activity.requested);
    }
    @Test public void encryptedBackupRestoresSecretsWithNewPhoneKeyAndFreshRowIds()throws Exception{
        long id=secret("hidden","[ ] pears");activity.credentialEpoch=activity.accessEpoch;
        try{activity.backupBytes(false);fail();}catch(SecurityException expected){}
        byte[] plain=activity.backupBytes(true);byte[] protectedFile=BackupEnvelope.encrypt(plain,"A separate long password".toCharArray());
        JSONObject backup=new JSONObject(new String(BackupEnvelope.decrypt(protectedFile,"A separate long password".toCharArray()),java.nio.charset.StandardCharsets.UTF_8));
        assertTrue(backup.getJSONArray("notes").getJSONObject(0).getBoolean("secret"));
        KeyGenerator fresh=KeyGenerator.getInstance("AES");fresh.init(256);SecretKey replacementPhoneKey=fresh.generateKey();activity.secretCipher=new NoteCipher(()->replacementPhoneKey);
        activity.restoreNotes(backup.getJSONArray("notes"));assertEquals(2,count());
        long imported;try(Cursor c=activity.db.rawQuery("SELECT max(id) FROM notes",null)){c.moveToFirst();imported=c.getLong(0);}assertNotEquals(id,imported);
        unlock(imported);assertEquals("hidden",activity.title.getText().toString());
        controller.pause().resume();try{activity.backupBytes(true);fail();}catch(SecurityException expected){}
    }
    @Test public void corruptedSecretFailsClosedWithoutOverwritingIt()throws Exception{
        long id=secret("hidden","private content");ContentValues v=new ContentValues();v.put("body","v1:bad:tampered");activity.db.update("notes",v,"id=?",new String[]{""+id});
        unlock(id);assertNull(activity.title);assertEquals(-1,activity.editing);assertTrue(activity.isSecret(id));
        try(Cursor c=activity.db.rawQuery("SELECT body FROM notes WHERE id=?",new String[]{""+id})){c.moveToFirst();assertEquals("v1:bad:tampered",c.getString(0));}
    }
    @Test public void oldBackupsRestorePublicNotesAndFailedSecretRestoreIsAtomic()throws Exception{
        JSONObject publicNote=new JSONObject().put("title","ordinary").put("body","hello").put("pinned",1).put("deleted",0).put("updated",123);
        activity.restoreNotes(new JSONArray().put(publicNote));assertEquals(1,count());
        JSONObject privateNote=new JSONObject(publicNote.toString()).put("secret",true);
        activity.secretCipher=new NoteCipher(()->{throw new java.io.IOException("Test key failure");});
        try{activity.restoreNotes(new JSONArray().put(publicNote).put(privateNote));fail();}catch(java.io.IOException expected){}
        assertEquals(1,count());
    }
    @Test public void unencryptedBackupCannotSmuggleSecretPlaintextThroughRestore()throws Exception{
        JSONObject note=new JSONObject().put("title","hidden").put("body","do not display").put("pinned",0).put("deleted",0).put("updated",1).put("secret",true);
        JSONObject plain=new JSONObject().put("format","wormwright-notes-v1").put("notes",new JSONArray().put(note));
        activity.offerRestore(plain.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8),false);assertEquals(0,count());
    }
}

package ai.wormwright.notes;

import android.app.Instrumentation;
import android.content.Intent;
import android.os.*;
import android.graphics.Rect;
import android.view.accessibility.AccessibilityNodeInfo;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.Callable;
import java.util.concurrent.FutureTask;

/** Uses only invented notes and the disposable emulator's PIN. Never targets user devices. */
public final class SecretUiInstrumentation extends Instrumentation {
    volatile MainActivity activity;
    long id;
    boolean screenshots;String upgradeMode;
    static final String TITLE="Test-only private checklist",BODY="[ ] invented pears\n[x] invented milk";
    public void onCreate(Bundle arguments){super.onCreate(arguments);upgradeMode=arguments==null?null:arguments.getString("upgrade");screenshots=arguments!=null&&"true".equals(arguments.getString("screenshots"));start();}
    public void onStart(){
        Bundle result=new Bundle();
        try{
            trackMainActivity();
            if(upgradeMode!=null){ReleaseUpgradeCheck.run(this,"seed".equals(upgradeMode));result.putString("stream","PASS release upgrade "+upgradeMode+"\n");finish(-1,result);return;}
            if(screenshots){ScreenshotCapture.run(this);result.putString("stream","PASS website screenshots captured from actual app screens with fictional sample notes\n");finish(-1,result);return;}
            activity=(MainActivity)startActivitySync(new Intent(getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            android.app.KeyguardManager screen=(android.app.KeyguardManager)getTargetContext().getSystemService(android.content.Context.KEYGUARD_SERVICE);
            key(224);
            waitFor(()->screen.isKeyguardLocked()||main(()->activity.resumed),30000);
            if(screen.isKeyguardLocked()){
                // The disposable emulator can finish booting locked after locksettings set-pin.
                key(82);SystemClock.sleep(600);shell("input text 246813");key(66);
                waitFor(()->!screen.isKeyguardLocked(),15000);
            }
            waitFor(()->main(()->activity.resumed),30000);
            main(()->{activity.editor(-1);activity.title.setText(TITLE);activity.body.setText(BODY);check(activity.save(),"initial save");id=activity.editing;activity.confirmMakeSecret();return null;});
            tapText("Make secret");waitForCredential();cancelCredential();
            check(!main(()->activity.isSecret(id)),"cancel did not create a secret");
            main(()->{activity.confirmMakeSecret();return null;});tapText("Make secret");enterPin("246813");
            waitFor(()->main(()->activity.isSecret(id)&&activity.title==null&&activity.resumed),15000);
            check(main(()->{try(android.database.Cursor c=activity.db.rawQuery("SELECT title,body FROM notes WHERE id="+id,null)){return c.moveToFirst()&&c.getString(0).isEmpty()&&!c.getString(1).contains("invented");}}),"secret stored as ciphertext");
            main(()->{activity.editor(id);return null;});enterPin("111111");SystemClock.sleep(1200);
            check(!main(()->activity.currentSecret),"wrong PIN did not reveal text");
            cancelCredential();
            check(main(()->activity.title==null),"cancel kept text hidden");
            main(()->{activity.editor(id);return null;});enterPin("246813");
            waitFor(()->main(()->activity.currentSecret&&activity.title!=null&&BODY.equals(activity.body.getText().toString())),15000);
            check(main(()->TITLE.equals(activity.title.getText().toString())&&activity.checklistMode),"unlocked checklist contents");
            main(()->{activity.shareNote();return null;});waitFor(()->main(()->!activity.currentSecret&&activity.title==null),10000);
            closeShareSheet();
            check(main(()->activity.title==null&&activity.unlockedId==-1),"share exit relocked editor");
            main(()->{activity.editor(id);return null;});waitForCredential();cancelCredential();
            String sdkJson=new com.squareup.moshi.Moshi.Builder().build().adapter(java.util.Map.class).toJson(java.util.Collections.singletonMap("sdk","Notes"));
            check(sdkJson.contains("Notes"),"SDK JSON runtime dependencies");
            check(com.yubico.yubikit.fido.Cbor.encode(java.util.Collections.singletonMap(1,"Notes")).length>0,"SDK CBOR runtime");
            main(()->{activity.hardwareBackups().manage();return null;});
            waitFor(()->button(getUiAutomation().getRootInActiveWindow(),"Close")!=null,10000);tapText("Close");
            main(()->{activity.hardwareBackups().enroll("Disposable emulator key",BackupKeyRegistry.empty());return null;});
            waitFor(()->button(getUiAutomation().getRootInActiveWindow(),"Continue")!=null,10000);tapText("Cancel");
            check(main(()->activity.hardwareBackups().state().getJSONArray("keys").length()==0),"cancel did not register a key");
            // Android resolves a real ACTION_SEND into the review activity; no write happens on receipt.
            int beforeImport=main(()->{try(android.database.Cursor c=activity.db.rawQuery("SELECT count(*) FROM notes",null)){c.moveToFirst();return c.getInt(0);}});
            Intent shared=new Intent(Intent.ACTION_SEND).setType("text/plain").setPackage(getTargetContext().getPackageName()).putExtra(Intent.EXTRA_TEXT,"- Milk\n- [x] Bread").putExtra(Intent.EXTRA_SUBJECT,"Sample groceries").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            check(getTargetContext().getPackageManager().resolveActivity(shared,0)!=null,"Android text share target resolves");
            TextImportActivity review=(TextImportActivity)startActivitySync(shared);
            check(main(()->{try(android.database.Cursor c=activity.db.rawQuery("SELECT count(*) FROM notes",null)){c.moveToFirst();return c.getInt(0)==beforeImport;}}),"sharing did not save automatically");
            tapText("Checklist");main(()->{review.title.setText("Reviewed groceries");return null;});captureImportReview();tapText("Save");
            waitFor(()->main(()->{try(android.database.Cursor c=activity.db.rawQuery("SELECT title,body,secret,kind FROM notes WHERE title='Reviewed groceries'",null)){return c.moveToFirst()&&"[ ] Milk\n[x] Bread".equals(c.getString(1))&&c.getInt(2)==0&&c.getInt(3)==1;}}),10000);
            check(main(()->activity.isSecret(id)),"text import did not change existing secret note");
            TextImportActivity noteReview=(TextImportActivity)startActivitySync(new Intent(Intent.ACTION_SEND).setClass(getTargetContext(),TextImportActivity.class).setType("text/plain").putExtra(Intent.EXTRA_TEXT,"[ ] Literal text for a note").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            main(()->{noteReview.title.setText("Reviewed written note");return null;});tapText("Save");
            waitFor(()->main(()->{try(android.database.Cursor c=activity.db.rawQuery("SELECT kind,body FROM notes WHERE title='Reviewed written note'",null)){return c.moveToFirst()&&c.getInt(0)==0&&"[ ] Literal text for a note".equals(c.getString(1));}}),10000);
            waitFor(()->main(()->activity.resumed&&activity.title!=null&&"Reviewed written note".contentEquals(activity.title.getText())),10000);
            String longItem="A collection of action figures with a large transforming robot and matching accessories";
            long wrappedId=main(()->{activity.editor(-1);activity.title.setText("A sample checklist");activity.body.setText("[ ] "+longItem+"\n[x] Board games for rainy afternoons");activity.checklistMode=true;activity.showChecklist();check(activity.save(),"save long checklist");return activity.editing;});
            waitFor(()->main(()->{android.widget.LinearLayout row=(android.widget.LinearLayout)activity.checklist.getChildAt(0);android.widget.EditText field=(android.widget.EditText)row.getChildAt(1);return field.getLayout()!=null&&field.getLineCount()>1;}),10000);
            main(()->{android.widget.LinearLayout row=(android.widget.LinearLayout)activity.checklist.getChildAt(0);((android.widget.CheckBox)row.getChildAt(0)).setChecked(true);check(activity.save(),"save wrapped checked item");activity.home();activity.editor(wrappedId);return null;});
            check(main(()->activity.body.getText().toString().equals("[x] "+longItem+"\n[x] Board games for rainy afternoons")&&activity.checklist.getChildCount()==3),"wrapped text stays one item through save and reopen");
            capturePublicScreen("notes-wrapped-checklist.png");
            result.putString("stream","PASS real Android credential-only PIN, cancel, wrong PIN, encrypted secret checklist, sharing, relock native YubiKey dialog cancellation, and reviewed text-share imports as note/checklist\n");finish(-1,result);
        }catch(Throwable error){
            StringWriter trace=new StringWriter();error.printStackTrace(new PrintWriter(trace));
            result.putString("stream","FAIL secret-note device regression\n"+trace+"\n"+tree(getUiAutomation().getRootInActiveWindow(),0));finish(1,result);
        }
    }
    void trackMainActivity(){
        ((android.app.Application)getTargetContext().getApplicationContext()).registerActivityLifecycleCallbacks(new android.app.Application.ActivityLifecycleCallbacks(){
            public void onActivityResumed(android.app.Activity current){if(current instanceof MainActivity)activity=(MainActivity)current;}
            public void onActivityCreated(android.app.Activity a,Bundle state){}public void onActivityStarted(android.app.Activity a){}public void onActivityPaused(android.app.Activity a){}public void onActivityStopped(android.app.Activity a){}public void onActivitySaveInstanceState(android.app.Activity a,Bundle state){}public void onActivityDestroyed(android.app.Activity a){}
        });
    }
    void captureImportReview()throws Exception{capturePublicScreen("notes-text-import.png");}
    void capturePublicScreen(String name)throws Exception{
        waitForIdleSync();SystemClock.sleep(500);
        android.graphics.Bitmap bitmap=getUiAutomation().takeScreenshot();check(bitmap!=null,"import review screenshot");
        File folder=getTargetContext().getExternalFilesDir("screenshots");check(folder!=null,"screenshot directory");
        try(FileOutputStream out=new FileOutputStream(new File(folder,name))){check(bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,out),"PNG screenshot");}finally{bitmap.recycle();}
    }
    interface Condition{boolean get()throws Exception;}
    void waitFor(Condition condition,long timeout)throws Exception{long end=SystemClock.elapsedRealtime()+timeout;while(SystemClock.elapsedRealtime()<end){if(condition.get())return;SystemClock.sleep(100);}throw new AssertionError("Timed out waiting for expected test state");}
    <T>T main(Callable<T> callable)throws Exception{FutureTask<T> task=new FutureTask<>(callable);runOnMainSync(task);return task.get();}
    static void check(boolean value,String label){if(!value)throw new AssertionError(label);}
    void key(int number)throws Exception{shell("input keyevent "+number);}
    void shell(String command)throws Exception{try(ParcelFileDescriptor p=getUiAutomation().executeShellCommand(command);InputStream in=new ParcelFileDescriptor.AutoCloseInputStream(p)){byte[] b=new byte[1024];while(in.read(b)!=-1){}}}
    AccessibilityNodeInfo editable(AccessibilityNodeInfo node){
        if(node==null)return null;
        if(node.isVisibleToUser()&&node.isEnabled()&&(node.isEditable()||(node.getClassName()!=null&&node.getClassName().toString().contains("EditText"))))return node;
        for(int i=0;i<node.getChildCount();i++){AccessibilityNodeInfo found=editable(node.getChild(i));if(found!=null)return found;}return null;
    }
    boolean credentialWindow(){AccessibilityNodeInfo root=getUiAutomation().getRootInActiveWindow();return root!=null&&root.getPackageName()!=null&&!root.getPackageName().toString().equals(getTargetContext().getPackageName())&&editable(root)!=null;}
    void waitForCredential()throws Exception{waitFor(this::credentialWindow,15000);}
    void closeShareSheet()throws Exception{
        waitFor(()->{AccessibilityNodeInfo root=getUiAutomation().getRootInActiveWindow();return root!=null&&"com.android.intentresolver".contentEquals(root.getPackageName()==null?"":root.getPackageName());},10000);
        try{getUiAutomation().waitForIdle(300,5000);}catch(java.util.concurrent.TimeoutException busy){}
        for(int i=0;i<3;i++){key(4);try{waitFor(()->main(()->activity.resumed),1500);return;}catch(AssertionError pending){}}
        throw new AssertionError("Share sheet did not close");
    }
    void cancelCredential()throws Exception{
        for(int i=0;i<3;i++){key(4);try{waitFor(()->main(()->activity.resumed&&!activity.authenticating),1000);return;}catch(AssertionError pending){}}
        throw new AssertionError("Credential prompt did not cancel");
    }
    void enterPin(String pin)throws Exception{
        waitForCredential();AccessibilityNodeInfo field=editable(getUiAutomation().getRootInActiveWindow());
        field.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
        Bundle args=new Bundle();args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,pin);
        if(!field.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,args)){
            Rect r=new Rect();field.getBoundsInScreen(r);shell("input tap "+r.centerX()+" "+r.centerY());shell("input text "+pin);
        }
        key(66);
    }
    AccessibilityNodeInfo button(AccessibilityNodeInfo node,String text){
        if(node==null)return null;if(node.isClickable()&&node.isVisibleToUser()&&text.equalsIgnoreCase(node.getText()==null?"":node.getText().toString()))return node;
        for(int i=0;i<node.getChildCount();i++){AccessibilityNodeInfo found=button(node.getChild(i),text);if(found!=null)return found;}return null;
    }
    void tapText(String text)throws Exception{waitFor(()->button(getUiAutomation().getRootInActiveWindow(),text)!=null,10000);check(button(getUiAutomation().getRootInActiveWindow(),text).performAction(AccessibilityNodeInfo.ACTION_CLICK),"tap "+text);}
    String tree(AccessibilityNodeInfo n,int depth){if(n==null||depth>12)return "";StringBuilder b=new StringBuilder();b.append(n.getPackageName()).append(' ').append(n.getClassName()).append(' ').append(n.getText()).append(' ').append(n.getContentDescription()).append('\n');for(int i=0;i<n.getChildCount();i++)b.append(tree(n.getChild(i),depth+1));return b.toString();}
}

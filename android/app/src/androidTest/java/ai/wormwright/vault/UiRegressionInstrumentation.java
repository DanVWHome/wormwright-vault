package ai.wormwright.vault;

import android.app.*;
import android.content.Intent;
import android.os.*;
import android.view.*;
import android.widget.*;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Real Android dialog/message-loop regression checks; invented sample data only. */
public class UiRegressionInstrumentation extends Instrumentation {
    private MainActivity activity;
    private boolean editorsOnly;
    private String dialogField = "detailDialog";
    private String lockMethod = "lockNow";
    private String sampleButton = "Try the sample vault";
    private String jobMethod = "job";
    @Override public void onCreate(Bundle args) { super.onCreate(args);editorsOnly=args!=null&&"true".equals(args.getString("editorsOnly")); start(); }
    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            unlockFixtureScreen();
            activity = (MainActivity)startActivitySync(new Intent(getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            waitForIdleSync();
            if(!editorsOnly)maintenanceFlow();
            if(editorsOnly){openingFeedback();passwordVisibility();result.putBoolean("ui_regression_ok",true);result.putString("stream","\nPASS opening spinner/password generation in new and existing editors, secure alphabet/length, repeated generation, masking, reveal and cancel.\n");runOnMainSync(()->activity.finish());finish(Activity.RESULT_OK,result);return;}
            openingFeedback();
            searchKeyboard();
            passwordVisibility();
            
            staleCompletion();
            failureFeedback();
            result.putBoolean("ui_regression_ok",true);
            result.putString("stream","\nPASS opening spinner/duplicate taps, required names, named list after reopening, rename persistence, independent NAS settings, selected/current account+PIN deletion preserving another vault, Cancel and typed confirmation, search keyboard/focus/latest results, new/edit password visibility, stale completion, error cleanup.\n");
            runOnMainSync(() -> activity.finish()); finish(Activity.RESULT_OK,result);
        } catch (Throwable error) {
            result.putBoolean("ui_regression_ok",false); result.putString("stream",android.util.Log.getStackTraceString(error));
            finish(Activity.RESULT_CANCELED,result);
        }
    }
    private Object field(String name) throws Exception { Field f=MainActivity.class.getDeclaredField(name); f.setAccessible(true); return f.get(activity); }
    private void check(boolean condition,String message) { if(!condition) throw new AssertionError(message); }
    private void await(java.util.function.BooleanSupplier condition,String label) {
        long limit=SystemClock.uptimeMillis()+120000;
        while(SystemClock.uptimeMillis()<limit) { final boolean[] ready={false}; runOnMainSync(()->ready[0]=condition.getAsBoolean()); if(ready[0])return; SystemClock.sleep(40); }
        final String[] state={""};
        runOnMainSync(()->{try{state[0]="busy="+field("busy")+", resumed="+field("resumed")+", unlocked="+field("unlocked")+", status="+((TextView)field("status")).getText();}catch(Exception e){state[0]=e.toString();}});
        StringBuilder trace=new StringBuilder();
        for(java.util.Map.Entry<Thread,StackTraceElement[]> entry:Thread.getAllStackTraces().entrySet()) {
            if(entry.getKey().getName().startsWith("pool-")) {trace.append("\n"+entry.getKey().getName());for(StackTraceElement frame:entry.getValue())trace.append("\n  "+frame);}
        }
        Thread pythonTrace=new Thread(()->{
            try {
                com.chaquo.python.PyObject file=com.chaquo.python.Python.getInstance().getModule("builtins").callAttr("open",new java.io.File(activity.getNoBackupFilesDir(),"ui-python-trace.txt").getPath(),"w");
                com.chaquo.python.Python.getInstance().getModule("faulthandler").callAttr("dump_traceback",file,true);file.callAttr("close");
            }catch(Exception e){android.util.Log.e("UiRegression","Python diagnostic failed",e);}
        });pythonTrace.setDaemon(true);pythonTrace.start();
        try{pythonTrace.join(5000);java.io.File file=new java.io.File(activity.getNoBackupFilesDir(),"ui-python-trace.txt");if(file.exists())trace.append("\n"+new String(java.nio.file.Files.readAllBytes(file.toPath()),java.nio.charset.StandardCharsets.UTF_8));}catch(Exception ignored){}
        throw new AssertionError("Timed out: "+label+"; "+state[0]+trace);
    }
    private boolean busy() { try{return (Boolean)field("busy");}catch(Exception e){throw new RuntimeException(e);} }
    private boolean unlocked() { try{return (Boolean)field("unlocked");}catch(Exception e){throw new RuntimeException(e);} }
    private ViewGroup root() { try{return (ViewGroup)field("root");}catch(Exception e){throw new RuntimeException(e);} }
    private Button findButton(View view,String label) {
        if(view instanceof Button && label.contentEquals(((Button)view).getText())) return (Button)view;
        if(view instanceof ViewGroup) for(int i=0;i<((ViewGroup)view).getChildCount();i++){Button found=findButton(((ViewGroup)view).getChildAt(i),label);if(found!=null)return found;}
        return null;
    }
    private boolean hasSpinner(View view) {
        if(view instanceof ProgressBar && view.isShown())return true;
        if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++)if(hasSpinner(((ViewGroup)view).getChildAt(i)))return true;
        return false;
    }
    private void waitLatch(CountDownLatch latch,String label) {try{check(latch.await(60,TimeUnit.SECONDS),label);}catch(InterruptedException e){throw new RuntimeException(e);} }
    private void shell(String command) {
        try(android.os.ParcelFileDescriptor descriptor=getUiAutomation().executeShellCommand(command);
            java.io.InputStream input=new android.os.ParcelFileDescriptor.AutoCloseInputStream(descriptor)) {
            byte[] bytes=new byte[4096];while(input.read(bytes)!=-1){}
        }catch(Exception e){throw new RuntimeException(e);}
    }
    private android.view.accessibility.AccessibilityNodeInfo pinField(android.view.accessibility.AccessibilityNodeInfo node) {
        if(node==null)return null;
        if("android.widget.EditText".contentEquals(node.getClassName()==null?"":node.getClassName()))return node;
        for(int i=0;i<node.getChildCount();i++){android.view.accessibility.AccessibilityNodeInfo found=pinField(node.getChild(i));if(found!=null)return found;}
        return null;
    }
    private void appendSystemNodes(android.view.accessibility.AccessibilityNodeInfo node,StringBuilder out,int depth) {
        if(node==null||depth>12)return;
        out.append("\n").append(node.getClassName()).append(" ").append(node.getViewIdResourceName()).append(" text=").append(node.isPassword()?"[password field]":node.getText()).append(" desc=").append(node.getContentDescription());
        for(int i=0;i<node.getChildCount();i++)appendSystemNodes(node.getChild(i),out,depth+1);
    }
    private void unlockFixtureScreen() {
        android.app.KeyguardManager guard=(android.app.KeyguardManager)getTargetContext().getSystemService(android.content.Context.KEYGUARD_SERVICE);
        shell("input keyevent 224");long until=SystemClock.uptimeMillis()+30000;
        while(guard.isKeyguardLocked()&&SystemClock.uptimeMillis()<until){
            android.view.accessibility.AccessibilityNodeInfo root=getUiAutomation().getRootInActiveWindow();
            if(root!=null&&"com.android.systemui".contentEquals(root.getPackageName())){
                java.util.List<android.view.accessibility.AccessibilityNodeInfo> entry=root.findAccessibilityNodeInfosByViewId("com.android.systemui:id/pinEntry");
                if(!entry.isEmpty()) {
                    // This is the isolated emulator's ordinary lock screen, not
                    // the app's auth prompt. Enter only the invented fixture PIN.
                    boolean ready=true;
                    for(char digit:"246813".toCharArray())if(root.findAccessibilityNodeInfosByViewId("com.android.systemui:id/key"+digit).isEmpty())ready=false;
                    if(!ready){SystemClock.sleep(200);continue;}
                    for(char digit:"246813".toCharArray()){
                        java.util.List<android.view.accessibility.AccessibilityNodeInfo> keys=root.findAccessibilityNodeInfosByViewId("com.android.systemui:id/key"+digit);
                        check(!keys.isEmpty(),"fixture PIN keypad exists");keys.get(0).performAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_CLICK);
                    }
                    java.util.List<android.view.accessibility.AccessibilityNodeInfo> enter=root.findAccessibilityNodeInfosByViewId("com.android.systemui:id/key_enter");
                    check(!enter.isEmpty(),"fixture PIN enter exists");enter.get(0).performAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_CLICK);
                    long unlocked=SystemClock.uptimeMillis()+5000;
                    while(guard.isKeyguardLocked()&&SystemClock.uptimeMillis()<unlocked)SystemClock.sleep(100);
                }else {shell("input keyevent 82");shell("input swipe 540 1800 540 400 300");}
            }
            SystemClock.sleep(200);
        }
        check(!guard.isKeyguardLocked(),"isolated emulator unlocked before app tests");
    }
    private void confirmPin() {
        shell("input keyevent 224");
        long limit=SystemClock.uptimeMillis()+30000;
        android.view.accessibility.AccessibilityNodeInfo field=null,root=null;
        while(SystemClock.uptimeMillis()<limit){
            root=getUiAutomation().getRootInActiveWindow();
            if(root!=null&&!root.findAccessibilityNodeInfosByText("Quickstep isn't responding").isEmpty()) {
                java.util.List<android.view.accessibility.AccessibilityNodeInfo> close=root.findAccessibilityNodeInfosByViewId("android:id/aerr_close");
                if(!close.isEmpty())close.get(0).performAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_CLICK);
                SystemClock.sleep(200);continue;
            }
            if(root!=null&&"com.android.systemui".contentEquals(root.getPackageName())){field=pinField(root);if(field!=null&&field.isFocused()&&field.isVisibleToUser()&&field.getActionList().contains(android.view.accessibility.AccessibilityNodeInfo.AccessibilityAction.ACTION_IME_ENTER))break;field=null;}
            SystemClock.sleep(100);
        }
        if(field==null){StringBuilder nodes=new StringBuilder();appendSystemNodes(root,nodes,0);throw new AssertionError("PIN field not found"+nodes);}
        field.performAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_FOCUS);
        // Wait for the system credential view and its keyboard to finish opening.
        // Accessibility IME_ENTER can report success without submitting this view.
        try{getUiAutomation().waitForIdle(1000,5000);}catch(java.util.concurrent.TimeoutException ignored){}
        root=getUiAutomation().getRootInActiveWindow();
        check(root!=null&&"com.android.systemui".contentEquals(root.getPackageName()),"fixture PIN stays in SystemUI");
        field=pinField(root);
        check(field!=null&&field.isFocused()&&field.isVisibleToUser(),"fixture PIN input is ready");
        Bundle value=new Bundle();value.putCharSequence(android.view.accessibility.AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,"");
        check(field.performAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT,value),"fixture PIN input cleared");
        shell("input text 246813");
        try{getUiAutomation().waitForIdle(500,5000);}catch(java.util.concurrent.TimeoutException ignored){}
        root=getUiAutomation().getRootInActiveWindow();field=pinField(root);
        check(root!=null&&"com.android.systemui".contentEquals(root.getPackageName())&&field!=null&&field.isFocused(),"fixture PIN focus preserved");
        check(field.getText()!=null&&field.getText().length()==6,"fixture PIN has six characters");
        shell("input keyevent 66");
        long done=SystemClock.uptimeMillis()+10000;
        while(SystemClock.uptimeMillis()<done){
            root=getUiAutomation().getRootInActiveWindow();
            if(root==null||!"com.android.systemui".contentEquals(root.getPackageName())||pinField(root)==null)return;
            SystemClock.sleep(100);
        }
        StringBuilder nodes=new StringBuilder();appendSystemNodes(root,nodes,0);throw new AssertionError("Invented PIN was not accepted"+nodes);
    }
    private void invoke(String name) {
        try{Method method=MainActivity.class.getDeclaredMethod(name);method.setAccessible(true);method.invoke(activity);}catch(Exception e){throw new RuntimeException(e);}
    }
    private AlertDialog maintenanceDialog() {
        try{Object owner=field("maintenance");Field f=owner.getClass().getDeclaredField("dialog");f.setAccessible(true);return (AlertDialog)f.get(owner);}catch(Exception e){throw new RuntimeException(e);}
    }
    private boolean hasText(View view,String text) {
        if(view instanceof TextView&&text.contentEquals(((TextView)view).getText()))return true;
        if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++)if(hasText(((ViewGroup)view).getChildAt(i),text))return true;
        return false;
    }
    private AlertDialog phoneDialog() {try{return (AlertDialog)field("editorDialog");}catch(Exception e){throw new RuntimeException(e);}}
    private void createNamedPhoneVault(String name,String secret) {
        runOnMainSync(()->invoke("createPhoneVault"));waitForIdleSync();
        runOnMainSync(()->{AlertDialog prompt=phoneDialog();List<EditText> inputs=new ArrayList<>();collectInputs(prompt.getWindow().getDecorView(),inputs);check(inputs.size()==3,"name and two credential fields");inputs.get(1).setText(secret);inputs.get(2).setText(secret);prompt.getButton(AlertDialog.BUTTON_POSITIVE).performClick();check(prompt.isShowing(),"blank vault name rejected");inputs.get(0).setText(name);prompt.getButton(AlertDialog.BUTTON_POSITIVE).performClick();});
        await(()->{try{return !busy()&&((java.io.File)field("vaultFile")).exists();}catch(Exception e){throw new RuntimeException(e);}},"named independent phone vault creation");
        runOnMainSync(()->{try{((EditText)field("password")).setText(secret);invoke("unlock");}catch(Exception e){throw new RuntimeException(e);}});await(()->unlocked()&&!busy(),"named vault unlocks");
    }
    private void maintenanceFlow() throws Exception {
        final String secret="Invented-NAS-New-Vault-Only!";java.io.File first=new java.io.File(activity.getNoBackupFilesDir(),"vault.db");
        createNamedPhoneVault("Family",secret);check(first.equals(field("vaultFile")),"legacy phone path preserved");
        NasSettings firstSettings=new NasSettings(activity,first.getParentFile());firstSettings.save(new org.json.JSONObject().put("invented_label","first connection"));
        createNamedPhoneVault("Travel",secret);java.io.File second=(java.io.File)field("vaultFile");check(!second.equals(first)&&first.exists(),"second phone vault preserves first");
        runOnMainSync(()->invoke("renamePhoneVault"));waitForIdleSync();runOnMainSync(()->{List<EditText> inputs=new ArrayList<>();collectInputs(phoneDialog().getWindow().getDecorView(),inputs);inputs.get(0).setText("Renamed travel vault");phoneDialog().getButton(AlertDialog.BUTTON_POSITIVE).performClick();});await(()->!busy()&&hasText(root(),"Renamed travel vault · OFFLINE EDITS + NAS SYNC"),"renamed vault heading");
        NasSettings secondSettings=new NasSettings(activity,second.getParentFile());secondSettings.save(new org.json.JSONObject().put("invented_label","second connection"));
        runOnMainSync(()->activity.finish());waitForIdleSync();SystemClock.sleep(300);
        activity=(MainActivity)startActivitySync(new Intent(getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));waitForIdleSync();
        await(()->phoneDialog()!=null&&phoneDialog().isShowing()&&phoneDialog().getListView()!=null,"named chooser appears after reopening");
        runOnMainSync(()->{android.widget.ListView list=phoneDialog().getListView();check(list.getAdapter().getCount()==2,"both named phone vaults survive reopening");boolean found=false;for(int i=0;i<list.getAdapter().getCount();i++)if(list.getAdapter().getItem(i).toString().startsWith("Renamed travel vault"))found=true;check(found,"renamed name persisted");phoneDialog().getButton(AlertDialog.BUTTON_NEGATIVE).performClick();});
        runOnMainSync(()->{try{java.lang.reflect.Method method=MainActivity.class.getDeclaredMethod("listVaults",boolean.class);method.setAccessible(true);method.invoke(activity,true);}catch(Exception e){throw new RuntimeException(e);}});
        await(()->phoneDialog()!=null&&phoneDialog().isShowing()&&phoneDialog().getListView()!=null,"selected deletion name list");
        runOnMainSync(()->{android.widget.ListView list=phoneDialog().getListView();int chosen=-1;for(int i=0;i<list.getAdapter().getCount();i++)if(list.getAdapter().getItem(i).toString().startsWith("Family ·"))chosen=i;check(chosen>=0,"Family name identifies selected vault");list.performItemClick(null,chosen,list.getAdapter().getItemId(chosen));});waitForIdleSync();
        runOnMainSync(()->phoneDialog().getButton(AlertDialog.BUTTON_NEGATIVE).performClick());check(first.exists()&&second.exists(),"Cancel before authorization preserves both vaults");
        for(boolean remove:new boolean[]{false,true}) {
            runOnMainSync(()->invoke("deletePhoneVault"));waitForIdleSync();
            runOnMainSync(()->{AlertDialog prompt=phoneDialog();List<EditText> inputs=new ArrayList<>();collectInputs(prompt.getWindow().getDecorView(),inputs);inputs.get(1).setText(secret);prompt.getButton(AlertDialog.BUTTON_POSITIVE).performClick();});
            await(()->{try{Object owner=field("maintenance");Field auth=owner.getClass().getDeclaredField("authenticating");auth.setAccessible(true);return auth.getBoolean(owner);}catch(Exception e){throw new RuntimeException(e);}},"fresh account authorization precedes PIN");
            confirmPin();await(()->maintenanceDialog()!=null&&maintenanceDialog().isShowing(),"fresh account and PIN deletion review");
            runOnMainSync(()->{AlertDialog review=maintenanceDialog();if(!remove){review.getButton(AlertDialog.BUTTON_NEGATIVE).performClick();return;}review.getButton(AlertDialog.BUTTON_POSITIVE).performClick();check(first.exists()&&review.isShowing(),"typed DELETE required");List<EditText> inputs=new ArrayList<>();collectInputs(review.getWindow().getDecorView(),inputs);inputs.get(0).setText("DELETE");review.getButton(AlertDialog.BUTTON_POSITIVE).performClick();});
            if(!remove)check(first.exists()&&second.exists(),"Cancel final review preserves both vaults");
        }
        await(()->!busy()&&!first.exists()&&findButton(root(),"Create new vault")!=null,"deleted current vault returns to creation and chooser");
        check(second.exists()&&"second connection".equals(secondSettings.load().getString("invented_label")),"selected deletion preserves other vault and its separate NAS key/settings");
        check(!firstSettings.exists(),"deleted vault connection removed");
    }
    private void openingFeedback() throws Exception {
        ExecutorService worker=(ExecutorService)field("worker");CountDownLatch held=new CountDownLatch(1),release=new CountDownLatch(1);
        worker.execute(()->{held.countDown();waitLatch(release,"release worker");});waitLatch(held,"worker held");
        try {runOnMainSync(()->{
            Button opening=findButton(root(),sampleButton);check(opening!=null,"sample button exists");opening.performClick();
            check(busy() && hasSpinner(root()),"opening immediately shows spinner");check(!opening.isEnabled(),"opening disabled until complete");
            opening.performClick();check(busy(),"duplicate tap does not finish opening");
        });}finally{release.countDown();}
        await(()->!busy()&&unlocked()&&hasEntryRows(),"sample opens");waitForIdleSync();
        runOnMainSync(()->check(!hasSpinner(root()),"spinner hides on success"));
    }
    private AlertDialog dialog() {try{return (AlertDialog)field(dialogField);}catch(Exception e){throw new RuntimeException(e);} }
    private void editTransitions() {
        for(int pass=0;pass<4;pass++) {
            runOnMainSync(()->{try{ViewGroup rows=(ViewGroup)field("rows");check(rows.getChildCount()>0,"sample entries exist");rows.getChildAt(0).performClick();}catch(Exception e){throw new RuntimeException(e);}});
            await(()->dialog()!=null&&dialog().isShowing(),"record opens");
            runOnMainSync(()->{Button edit=findButton(dialog().getWindow().getDecorView(),"Edit entry");check(edit!=null,"edit exists");edit.performClick();});
            waitForIdleSync();
            await(()->dialog()!=null&&dialog().isShowing()&&dialog().getButton(AlertDialog.BUTTON_POSITIVE)!=null,"editor remains tracked after old dismissal");
            final int iteration=pass;
            runOnMainSync(()->{
                AlertDialog editor=dialog();check("Save".contentEquals(editor.getButton(AlertDialog.BUTTON_POSITIVE).getText()),"editor Save exists");
                List<EditText> inputs=new ArrayList<>();collectInputs(editor.getWindow().getDecorView(),inputs);check(inputs.size()==5,"all editor fields present");
                inputs.get(4).setText("UI regression notes "+iteration);
                editor.getButton(iteration%2==0?AlertDialog.BUTTON_POSITIVE:AlertDialog.BUTTON_NEGATIVE).performClick();
            });
            await(()->!busy()&&dialog()==null,"save/cancel returns safely");waitForIdleSync();
        }
    }
    private void collectInputs(View view,List<EditText> values) {
        if(view instanceof EditText)values.add((EditText)view);
        if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++)collectInputs(((ViewGroup)view).getChildAt(i),values);
    }
    private boolean hasEntryRows() {
        try { ViewGroup rows=(ViewGroup)field("rows"); return rows!=null&&rows.getChildCount()>0&&rows.getChildAt(0) instanceof Button&&rows.getChildAt(0).isEnabled(); }catch(Exception e){return false;}
    }
    private boolean keyboardVisible() {android.view.WindowInsets insets=activity.getWindow().getDecorView().getRootWindowInsets();return insets!=null&&insets.isVisible(android.view.WindowInsets.Type.ime());}
    private void searchKeyboard() throws Exception {
        final EditText input=(EditText)field("search");final String[] entry={""};
        runOnMainSync(()->{try{entry[0]=((Button)((ViewGroup)field("rows")).getChildAt(0)).getText().toString().split("\n",2)[0];}catch(Exception e){throw new RuntimeException(e);}input.requestFocus();((android.view.inputmethod.InputMethodManager)activity.getSystemService(android.content.Context.INPUT_METHOD_SERVICE)).showSoftInput(input,android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT);});
        await(()->keyboardVisible(),"search keyboard opens");
        for(int length=1;length<=Math.min(3,entry[0].length());length++) {
            final String query=entry[0].substring(0,length);
            runOnMainSync(()->{input.setText(query);input.setSelection(query.length());});
            await(()->hasEntryRows(),"search results update after each letter");
            runOnMainSync(()->check(input.isEnabled()&&input.hasFocus()&&keyboardVisible(),"typing preserves enabled search, focus and keyboard"));
        }
        runOnMainSync(()->{input.setText("invented-no-match-938271");input.setText(entry[0]);});
        await(()->hasEntryRows(),"latest query wins");
        runOnMainSync(()->{try{ViewGroup rows=(ViewGroup)field("rows");check(rows.getChildCount()==1,"latest query filtered results");check(input.hasFocus()&&keyboardVisible(),"rapid typing keeps keyboard");input.setText("");}catch(Exception e){throw new RuntimeException(e);}});
        await(()->hasEntryRows(),"clear search restores results");
        runOnMainSync(()->((android.view.inputmethod.InputMethodManager)activity.getSystemService(android.content.Context.INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(input.getWindowToken(),0));
        await(()->!keyboardVisible(),"test closes keyboard");
    }
    private AlertDialog detail(){try{return (AlertDialog)field("detailDialog");}catch(Exception e){throw new RuntimeException(e);}}
    private AlertDialog editor() {try{return (AlertDialog)field("editorDialog");}catch(Exception e){throw new RuntimeException(e);}}
    private void passwordVisibility() {
        for(boolean existing:new boolean[]{false,true}) {
            runOnMainSync(()->{try{if(existing)((ViewGroup)field("rows")).getChildAt(0).performClick();else findButton(root(),"New entry").performClick();}catch(Exception e){throw new RuntimeException(e);}});
            if(existing) {
                await(()->detail()!=null&&detail().isShowing(),"entry opens for visibility test");
                runOnMainSync(()->findButton(detail().getWindow().getDecorView(),"Edit entry").performClick());
            }
            await(()->editor()!=null&&editor().isShowing()&&editor().getButton(AlertDialog.BUTTON_POSITIVE)!=null,"new/edit entry editor opens");
            runOnMainSync(()-> {
                List<EditText> fields=new ArrayList<>();collectInputs(editor().getWindow().getDecorView(),fields);EditText password=fields.get(3);
                CheckBox show=(CheckBox)findButton(editor().getWindow().getDecorView(),"Show password");check(show!=null&&!show.isChecked(),"password starts hidden");
                check(password.getTransformationMethod() instanceof android.text.method.PasswordTransformationMethod,"password is masked");
                Button generate=findButton(editor().getWindow().getDecorView(),"Generate password");check(generate!=null,"generator is available in new/edit entries");
                List<String> before=new ArrayList<>();for(EditText inputField:fields)before.add(inputField.getText().toString());generate.performClick();String generated=password.getText().toString();
                check(generated.length()==24&&generated.matches("[a-zA-Z0-9!@#$%&*+_=?.\\-]{24}"),"generated password length and safe alphabet");
                check(password.getTransformationMethod() instanceof android.text.method.PasswordTransformationMethod,"generated password stays hidden");
                for(int i=0;i<fields.size();i++)if(i!=3)check(before.get(i).equals(fields.get(i).getText().toString()),"generation preserves other fields");
                show.performClick();check(password.getTransformationMethod()==null&&generated.equals(password.getText().toString()),"generated password can be revealed");show.performClick();
                generate.performClick();check(!generated.equals(password.getText().toString()),"generate again replaces with a fresh password");
                password.setText("Invented-Visible-Password!");password.setSelection(5);show.performClick();
                check(password.getTransformationMethod()==null&&password.getSelectionStart()==5,"reveal preserves cursor");
                password.getText().append("Typed");String expected=password.getText().toString();show.performClick();
                check(password.getTransformationMethod() instanceof android.text.method.PasswordTransformationMethod&&expected.equals(password.getText().toString()),"hide preserves typed password");
                editor().getButton(AlertDialog.BUTTON_NEGATIVE).performClick();
            });waitForIdleSync();
        }
    }
    private void enqueue(String label,CountDownLatch entered,CountDownLatch release,AtomicInteger completed,boolean fail) {
        try {
            Method target=Arrays.stream(MainActivity.class.getDeclaredMethods()).filter(m->m.getName().equals(jobMethod)&&m.getParameterTypes()[0]==String.class).findFirst().get();target.setAccessible(true);
            Class<?>[] types=target.getParameterTypes();
            Object job=Proxy.newProxyInstance(types[1].getClassLoader(),new Class[]{types[1]},(p,m,a)->{entered.countDown();waitLatch(release,"release injected job");if(fail)throw new Exception("Injected failure");return "{}";});
            Object done=Proxy.newProxyInstance(types[2].getClassLoader(),new Class[]{types[2]},(p,m,a)->{completed.incrementAndGet();return null;});
            if(types.length==3)target.invoke(activity,label,job,done);else target.invoke(activity,label,job,done,"Injected job failed.");
        }catch(Exception e){throw new RuntimeException(e);}
    }
    private void staleCompletion() {
        CountDownLatch first=new CountDownLatch(1),releaseFirst=new CountDownLatch(1),second=new CountDownLatch(1),releaseSecond=new CountDownLatch(1);
        AtomicInteger oldDone=new AtomicInteger(),newDone=new AtomicInteger();
        runOnMainSync(()->enqueue("Old operation…",first,releaseFirst,oldDone,false));waitLatch(first,"old job begins");
        runOnMainSync(()->{try{Method lock=MainActivity.class.getDeclaredMethod(lockMethod,String.class);lock.setAccessible(true);lock.invoke(activity,"Regression lock");}catch(Exception e){throw new RuntimeException(e);}enqueue("New operation…",second,releaseSecond,newDone,false);});
        releaseFirst.countDown();waitLatch(second,"new job begins");waitForIdleSync();
        try{runOnMainSync(()->check(busy()&&hasSpinner(root()),"stale completion cannot hide current spinner"));check(oldDone.get()==0,"old success discarded");}finally{releaseSecond.countDown();}
        await(()->!busy(),"current operation completes");check(newDone.get()==1,"current success delivered");
    }
    private void failureFeedback() {
        CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(0);AtomicInteger completed=new AtomicInteger();
        runOnMainSync(()->enqueue("Failing operation…",entered,release,completed,true));waitLatch(entered,"failure begins");await(()->!busy(),"failure clears busy");
        runOnMainSync(()->{check(!hasSpinner(root()),"failure hides spinner");Button opening=findButton(root(),sampleButton);check(opening!=null&&opening.isEnabled(),"opening reenabled after failure");});check(completed.get()==0,"failed success not delivered");
    }
}

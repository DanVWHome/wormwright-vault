package ai.wormwright.pocket;

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
    private String dialogField = "dialog";
    private String lockMethod = "lock";
    private String sampleButton = "Open invented sample vault";
    private String jobMethod = "task";
    @Override public void onCreate(Bundle args) { super.onCreate(args); start(); }
    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            activity = (MainActivity)startActivitySync(new Intent(getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            waitForIdleSync();
            openingFeedback();
            searchKeyboard();
            editTransitions();
            deleteAndRestore();
            staleCompletion();
            failureFeedback();
            result.putBoolean("ui_regression_ok",true);
            result.putString("stream","\nPASS opening spinner/duplicate taps, search keyboard/focus/latest results, edit/save/cancel transitions, delete/restore list refresh, stale completion, error cleanup.\n");
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
            runOnMainSync(()->{try{((ViewGroup)field("rows")).getChildAt(0).performClick();}catch(Exception e){throw new RuntimeException(e);}});
            await(()->dialog()!=null&&dialog().isShowing(),"saved entry reopens");
            final String expected="UI regression notes "+(pass%2==0?pass:pass-1);
            runOnMainSync(()->{check(hasText(dialog().getWindow().getDecorView(),expected),"save persisted and cancel retained previous notes");dialog().dismiss();});
            await(()->dialog()==null,"record closes");waitForIdleSync();
        }
    }
    private void deleteAndRestore() {
        final String[] label={""}; final int[] count={0};
        runOnMainSync(()->{try{
            ViewGroup rows=(ViewGroup)field("rows");count[0]=rows.getChildCount();
            label[0]=((Button)rows.getChildAt(0)).getText().toString(); rows.getChildAt(0).performClick();
        }catch(Exception e){throw new RuntimeException(e);}});
        await(()->dialog()!=null&&dialog().isShowing(),"entry to delete opens");
        runOnMainSync(()->findButton(dialog().getWindow().getDecorView(),"Delete entry").performClick());waitForIdleSync();
        runOnMainSync(()->dialog().getButton(AlertDialog.BUTTON_NEGATIVE).performClick());waitForIdleSync();
        runOnMainSync(()->check(findButton(root(),label[0])!=null,"cancel keeps entry"));
        runOnMainSync(()->findButton(root(),label[0]).performClick());
        await(()->dialog()!=null&&dialog().isShowing(),"entry reopens for deletion");
        runOnMainSync(()->findButton(dialog().getWindow().getDecorView(),"Delete entry").performClick());waitForIdleSync();
        runOnMainSync(()->dialog().getButton(AlertDialog.BUTTON_POSITIVE).performClick());
        await(()->!busy()&&dialog()==null&&findButton(root(),label[0])==null,"deleted entry immediately disappears");
        runOnMainSync(()->{try{check(((ViewGroup)field("rows")).getChildCount()==count[0]-1,"list shrinks after deletion");findButton(root(),"Recently deleted").performClick();}catch(Exception e){throw new RuntimeException(e);}});
        await(()->!busy()&&dialog()!=null&&dialog().isShowing(),"recently deleted opens");
        runOnMainSync(()->{Button restore=findButton(dialog().getWindow().getDecorView(),"Restore "+label[0].split("\n",2)[0]);check(restore!=null,"deleted entry is recoverable");restore.performClick();});
        await(()->!busy()&&findButton(root(),label[0])!=null,"restored entry immediately reappears");
    }
    private boolean hasText(View view,String expected) {
        if(view instanceof TextView && expected.contentEquals(((TextView)view).getText()))return true;
        if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++)if(hasText(((ViewGroup)view).getChildAt(i),expected))return true;
        return false;
    }
    private void collectInputs(View view,List<EditText> values) {
        if(view instanceof EditText)values.add((EditText)view);
        if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++)collectInputs(((ViewGroup)view).getChildAt(i),values);
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

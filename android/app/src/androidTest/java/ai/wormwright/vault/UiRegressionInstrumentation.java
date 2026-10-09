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
    private String dialogField = "detailDialog";
    private String lockMethod = "lockNow";
    private String sampleButton = "Try the sample vault";
    private String jobMethod = "job";
    @Override public void onCreate(Bundle args) { super.onCreate(args); start(); }
    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            activity = (MainActivity)startActivitySync(new Intent(getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            waitForIdleSync();
            openingFeedback();
            
            staleCompletion();
            failureFeedback();
            result.putBoolean("ui_regression_ok",true);
            result.putString("stream","\nPASS opening spinner/duplicate taps, stale completion, error cleanup.\n");
            runOnMainSync(() -> activity.finish()); finish(Activity.RESULT_OK,result);
        } catch (Throwable error) {
            result.putBoolean("ui_regression_ok",false); result.putString("stream",android.util.Log.getStackTraceString(error));
            finish(Activity.RESULT_CANCELED,result);
        }
    }
    private Object field(String name) throws Exception { Field f=MainActivity.class.getDeclaredField(name); f.setAccessible(true); return f.get(activity); }
    private void check(boolean condition,String message) { if(!condition) throw new AssertionError(message); }
    private void await(java.util.function.BooleanSupplier condition,String label) {
        long limit=SystemClock.uptimeMillis()+60000;
        while(SystemClock.uptimeMillis()<limit) { final boolean[] ready={false}; runOnMainSync(()->ready[0]=condition.getAsBoolean()); if(ready[0])return; SystemClock.sleep(40); }
        final String[] state={""};
        runOnMainSync(()->{try{state[0]="busy="+field("busy")+", resumed="+field("resumed")+", unlocked="+field("unlocked")+", status="+((TextView)field("status")).getText();}catch(Exception e){state[0]=e.toString();}});
        throw new AssertionError("Timed out: "+label+"; "+state[0]);
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
        await(()->!busy()&&unlocked(),"sample opens");waitForIdleSync();
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

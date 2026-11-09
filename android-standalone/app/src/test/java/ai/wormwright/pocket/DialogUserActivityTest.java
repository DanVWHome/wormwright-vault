package ai.wormwright.pocket;
import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.view.MotionEvent;
import android.view.Window;
import android.widget.EditText;
import java.lang.reflect.Proxy;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import static org.robolectric.Shadows.shadowOf;
import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class)
@Config(manifest=Config.NONE,sdk=35,application=android.app.Application.class)
public class DialogUserActivityTest {
 @Test public void typingResetsButDoesNotDisableTheTwoMinuteLock(){
  Activity a=Robolectric.buildActivity(Activity.class).setup().get();EditText field=new PrivatePasswordInput(a);Handler timer=new Handler(Looper.getMainLooper());AtomicInteger locked=new AtomicInteger();Runnable lock=locked::incrementAndGet;Runnable activity=()->{timer.removeCallbacks(lock);timer.postDelayed(lock,120000);};DialogUserActivity.watch(field,activity);activity.run();
  shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(90));field.setText("Invented NAS password");shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(90));assertEquals(0,locked.get());field.getText().append("-continued");shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(119));assertEquals(0,locked.get());shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(2));assertEquals(1,locked.get());
 }
 @Test public void scrollingAndTouchesAreCountedAndCallbacksPreserved(){
  AtomicInteger events=new AtomicInteger(),delivered=new AtomicInteger();Window.Callback original=(Window.Callback)Proxy.newProxyInstance(Window.Callback.class.getClassLoader(),new Class<?>[]{Window.Callback.class},(p,m,args)->{delivered.incrementAndGet();return false;});Window.Callback tracked=DialogUserActivity.wrap(original,events::incrementAndGet);MotionEvent event=MotionEvent.obtain(0,0,MotionEvent.ACTION_MOVE,10,20,0);
  try{assertFalse(tracked.dispatchTouchEvent(event));assertFalse(tracked.dispatchGenericMotionEvent(event));assertEquals(2,events.get());assertFalse(tracked.onSearchRequested());assertEquals(2,events.get());assertEquals(3,delivered.get());}finally{event.recycle();}
 }
}

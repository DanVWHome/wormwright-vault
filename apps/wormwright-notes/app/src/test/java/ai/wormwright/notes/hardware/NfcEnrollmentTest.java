package ai.wormwright.notes.hardware;

import android.app.Activity;
import android.app.AlertDialog;
import android.widget.TextView;
import com.yubico.yubikit.android.transport.nfc.NfcYubiKeyDevice;
import org.json.JSONObject;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import java.lang.reflect.*;
import static org.junit.Assert.*;

/** Exercises the NFC handoff without claiming to emulate a physical authenticator. */
@RunWith(RobolectricTestRunner.class) @Config(sdk=35)
public class NfcEnrollmentTest {
 static class Device extends NfcYubiKeyDevice {
  Runnable removed;
  Device(){super(null,15000,null);}
  @Override public void remove(Runnable action){removed=action;}
 }
 Activity activity;YubiKeyUnlock hardware;Object pending;Class<?> attempt;Device device;int completed,failed;
 Object get(Object target,String name)throws Exception{Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(target);}
 void set(Object target,String name,Object value)throws Exception{Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);f.set(target,value);}
 @Before public void setup()throws Exception{
  activity=Robolectric.buildActivity(Activity.class).setup().get();hardware=new YubiKeyUnlock(activity);device=new Device();
  attempt=Class.forName(YubiKeyUnlock.class.getName()+"$Attempt");
  Constructor<?> constructor=attempt.getDeclaredConstructors()[0];constructor.setAccessible(true);
  pending=constructor.newInstance(hardware,new JSONObject(),true,new YubiKeyUnlock.Callback(){public void complete(JSONObject value){completed++;}public void failed(String message){failed++;}});
  set(hardware,"current",pending);set(pending,"dialog",new AlertDialog.Builder(activity).create());set(pending,"note",new TextView(activity));
 }
 @After public void cleanup(){hardware.dispose();activity.finish();}
 void handoff()throws Exception{
  Method method=YubiKeyUnlock.class.getDeclaredMethod("awaitEnrollmentRemoval",attempt,NfcYubiKeyDevice.class,JSONObject.class);method.setAccessible(true);
  method.invoke(hardware,pending,device,new JSONObject().put("credential","public credential").put("salt","public salt"));
 }
 @Test public void firstTapWaitsForPhysicalRemovalWithoutRegisteringOrReusingPin()throws Exception{
  handoff();assertNotNull(device.removed);assertSame(pending,get(hardware,"current"));assertEquals(0,completed);
  device.removed.run();Shadows.shadowOf(android.os.Looper.getMainLooper()).idle();
  Object verification=get(hardware,"current");assertNotNull(verification);assertNotSame(pending,verification);assertEquals(false,get(verification,"enroll"));
  assertNotSame(get(pending,"connectionOwner"),get(verification,"connectionOwner"));
  assertNotSame(get(pending,"pinBuffer"),get(verification,"pinBuffer"));
  assertEquals("public credential",((JSONObject)get(verification,"request")).getString("credential"));assertEquals(0,completed);assertEquals(0,failed);
 }
 @Test public void cancellationWhileWaitingForRemovalCannotRestartOrRegister()throws Exception{
  handoff();hardware.stop();device.removed.run();Shadows.shadowOf(android.os.Looper.getMainLooper()).idle();assertFalse(hardware.active());assertEquals(0,completed);assertEquals(0,failed);
 }
}

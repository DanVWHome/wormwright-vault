package ai.wormwright.hardware;
import android.view.Window;
import java.lang.reflect.Proxy;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.Test;
import static org.junit.Assert.*;
public class YubiKeyKeyboardGuardTest {
 @Test public void identifiesKeyWithoutBlockingOtherKeyboards(){
  assertTrue(YubiKeyKeyboardGuard.isYubiKey(0x1050,"USB keyboard"));
  assertTrue(YubiKeyKeyboardGuard.isYubiKey(0,"Yubico YubiKey OTP"));
  assertFalse(YubiKeyKeyboardGuard.isYubiKey(0,"Phone keyboard"));
  assertFalse(YubiKeyKeyboardGuard.isYubiKey(0x1234,"External keyboard"));
 }
 @Test public void keyEventsCannotActivateFocusedButtonsOrShortcuts(){
  AtomicInteger delivered=new AtomicInteger();
  Window.Callback target=(Window.Callback)Proxy.newProxyInstance(Window.Callback.class.getClassLoader(),new Class<?>[]{Window.Callback.class},(p,m,a)->{delivered.incrementAndGet();return false;});
  Window.Callback guard=YubiKeyKeyboardGuard.wrap(target,event->true);
  assertTrue(guard.dispatchKeyEvent(null));assertTrue(guard.dispatchKeyShortcutEvent(null));assertEquals(0,delivered.get());
 }
 @Test public void ordinaryKeyboardAndOtherCallbacksStillWork(){
  AtomicInteger delivered=new AtomicInteger();
  Window.Callback target=(Window.Callback)Proxy.newProxyInstance(Window.Callback.class.getClassLoader(),new Class<?>[]{Window.Callback.class},(p,m,a)->{delivered.incrementAndGet();return false;});
  Window.Callback guard=YubiKeyKeyboardGuard.wrap(target,event->false);
  assertFalse(guard.dispatchKeyEvent(null));assertFalse(guard.onSearchRequested());assertEquals(2,delivered.get());
 }
}

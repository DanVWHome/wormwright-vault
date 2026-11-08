package ai.wormwright.notes.hardware;

import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.Window;
import java.lang.reflect.*;
import java.util.Locale;
import java.util.function.Predicate;

/** Ignore the key's separate OTP keyboard interface inside vault windows.
 * This does not alter the key or intercept CTAP/FIDO traffic. */
public final class YubiKeyKeyboardGuard {
    static boolean isYubiKey(int vendor,String name) {
        String label=name==null?"":name.toLowerCase(Locale.ROOT);
        return vendor==0x1050 || (vendor==0 && (label.contains("yubico")||label.contains("yubikey")));
    }
    private static boolean block(KeyEvent event) {
        if(event==null)return false;
        InputDevice device=event.getDevice();
        return device!=null&&isYubiKey(device.getVendorId(),device.getName());
    }
    public static void install(Window window) {
        if(window==null)return;
        Window.Callback original=window.getCallback();
        if(original==null||(Proxy.isProxyClass(original.getClass())&&Proxy.getInvocationHandler(original) instanceof Guard))return;
        window.setCallback(wrap(original,YubiKeyKeyboardGuard::block));
    }
    static Window.Callback wrap(Window.Callback original,Predicate<KeyEvent> filter) {
        return (Window.Callback)Proxy.newProxyInstance(Window.Callback.class.getClassLoader(),new Class<?>[]{Window.Callback.class},new Guard(original,filter));
    }
    private static final class Guard implements InvocationHandler {
        private final Window.Callback original;private final Predicate<KeyEvent> filter;
        Guard(Window.Callback original,Predicate<KeyEvent> filter){this.original=original;this.filter=filter;}
        public Object invoke(Object proxy,Method method,Object[] args)throws Throwable {
            if((method.getName().equals("dispatchKeyEvent")||method.getName().equals("dispatchKeyShortcutEvent"))&&filter.test((KeyEvent)args[0]))return true;
            try{return method.invoke(original,args);}catch(InvocationTargetException error){throw error.getCause();}
        }
    }
    private YubiKeyKeyboardGuard(){}
}

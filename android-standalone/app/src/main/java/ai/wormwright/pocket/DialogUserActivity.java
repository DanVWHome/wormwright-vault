package ai.wormwright.pocket;

import android.text.Editable;
import android.text.TextWatcher;
import android.view.MotionEvent;
import android.view.Window;
import android.widget.EditText;
import java.lang.reflect.*;

/** Count dialog typing and touches without extending idle time for background work. */
final class DialogUserActivity {
    static void watch(EditText input,Runnable activity) {
        input.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s,int start,int count,int after) { }
            public void onTextChanged(CharSequence s,int start,int before,int count) { activity.run(); }
            public void afterTextChanged(Editable value) { }
        });
    }
    static void install(Window window,Runnable activity) {
        Window.Callback original=window.getCallback();
        if(original==null||(Proxy.isProxyClass(original.getClass())&&Proxy.getInvocationHandler(original) instanceof Tracker))return;
        window.setCallback(wrap(original,activity));
    }
    static Window.Callback wrap(Window.Callback original,Runnable activity) {
        return (Window.Callback)Proxy.newProxyInstance(Window.Callback.class.getClassLoader(),new Class<?>[]{Window.Callback.class},new Tracker(original,activity));
    }
    private static final class Tracker implements InvocationHandler {
        private final Window.Callback original;private final Runnable activity;
        Tracker(Window.Callback original,Runnable activity){this.original=original;this.activity=activity;}
        public Object invoke(Object proxy,Method method,Object[] args)throws Throwable {
            if((method.getName().equals("dispatchTouchEvent")||method.getName().equals("dispatchGenericMotionEvent"))&&args!=null&&args[0] instanceof MotionEvent)activity.run();
            try{return method.invoke(original,args);}catch(InvocationTargetException error){throw error.getCause();}
        }
    }
    private DialogUserActivity() { }
}

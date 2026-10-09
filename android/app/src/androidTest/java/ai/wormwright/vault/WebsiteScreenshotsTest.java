package ai.wormwright.vault;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.view.View;
import android.widget.LinearLayout;
import android.app.AlertDialog;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Test;
import org.junit.runner.RunWith;
import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import static org.junit.Assert.*;
@RunWith(AndroidJUnit4.class)
public class WebsiteScreenshotsTest {
    private static Object field(Object object, String name) throws Exception {
        Field f=object.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(object);
    }
    private static void invoke(Object object,String name) throws Exception {
        Method m=object.getClass().getDeclaredMethod(name);m.setAccessible(true);m.invoke(object);
    }
    // Draw only the isolated demo/test view. Production FLAG_SECURE is retained.
    private static void save(MainActivity activity,View view,String name) throws Exception {
        assertTrue(view.getWidth()>0 && view.getHeight()>0);
        Bitmap bitmap=Bitmap.createBitmap(view.getWidth(),view.getHeight(),Bitmap.Config.ARGB_8888);
        view.draw(new Canvas(bitmap));
        File directory=new File(activity.getFilesDir(),"screenshots");directory.mkdirs();
        try(FileOutputStream stream=new FileOutputStream(new File(directory,name))){bitmap.compress(Bitmap.CompressFormat.PNG,100,stream);}
        bitmap.recycle();
    }
    @Test public void captureDemo() throws Exception {
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            Thread.sleep(1800);
            scenario.onActivity(a->{try{save(a,a.getWindow().getDecorView(),"android-unlock.png");invoke(a,"openSample");}catch(Exception e){throw new RuntimeException(e);}});
            boolean[] ready={false};
            for(int i=0;i<40&&!ready[0];i++){
                Thread.sleep(500);
                scenario.onActivity(a->{try{ready[0]=(Boolean)field(a,"sampleMode") && !(Boolean)field(a,"busy");}catch(Exception e){throw new RuntimeException(e);}});
            }
            assertTrue("Sample vault opened",ready[0]);Thread.sleep(900);
            scenario.onActivity(a->{try{
                save(a,a.getWindow().getDecorView(),"android-entries.png");
                LinearLayout rows=(LinearLayout)field(a,"rows");assertTrue(rows.getChildCount()>3);rows.getChildAt(0).performClick();
            }catch(Exception e){throw new RuntimeException(e);}});
            Thread.sleep(1800);
            scenario.onActivity(a->{try{
                AlertDialog dialog=(AlertDialog)field(a,"detailDialog");assertNotNull(dialog);
                save(a,dialog.getWindow().getDecorView(),"android-entry-details.png");
            }catch(Exception e){throw new RuntimeException(e);}});
        }
    }
}

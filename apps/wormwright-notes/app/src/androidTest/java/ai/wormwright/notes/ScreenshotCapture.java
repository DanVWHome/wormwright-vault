package ai.wormwright.notes;

import android.content.ContentValues;
import android.content.Intent;
import android.graphics.Bitmap;
import android.os.SystemClock;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.view.inputmethod.InputMethodManager;
import java.io.File;
import java.io.FileOutputStream;

/** Website screenshots from real app screens, using only fictional disposable data. */
final class ScreenshotCapture {
    static void run(SecretUiInstrumentation driver)throws Exception{
        driver.activity=(MainActivity)driver.startActivitySync(new Intent(driver.getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        MainActivity app=driver.activity;
        driver.waitFor(()->driver.main(()->app.resumed),30000);
        long[] ids=driver.main(()->{
            app.db.delete("notes",null,null);
            long shopping=note(app,"Everyday essentials","[x] Apples\n[ ] Fresh bread\n[ ] Milk\n[ ] Coffee\n[x] Tomatoes\n[ ] Pasta",1);
            long weekend=note(app,"A little weekend plan","Saturday\nCoffee and a walk by the water.\nVisit the farmers market.\n\nSunday\nPlant the herbs on the patio.\nMake a big pot of soup.\n\nRemember to leave room for a quiet afternoon.",0);
            long secret=note(app,"Fictional private reminder","Sample content only",0);
            app.makeSecret(secret);
            app.home();return new long[]{shopping,weekend};
        });
        capture(driver,"notes-overview.png");
        driver.main(()->{app.editor(ids[0]);return null;});capture(driver,"notes-checklist.png");
        driver.main(()->{app.editor(ids[1]);return null;});capture(driver,"notes-writing.png");
    }
    private static long note(MainActivity app,String title,String body,int pinned){
        ContentValues value=new ContentValues();value.put("title",title);value.put("body",body);value.put("pinned",pinned);value.put("deleted",0);value.put("secret",0);value.put("updated",System.currentTimeMillis());
        return app.db.insertOrThrow("notes",null,value);
    }
    private static void capture(SecretUiInstrumentation driver,String name)throws Exception{
        driver.main(()->{
            MainActivity app=driver.activity;
            app.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN);
            ((InputMethodManager)app.getSystemService(android.content.Context.INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(app.root.getWindowToken(),0);
            app.root.setFocusableInTouchMode(true);app.root.setDescendantFocusability(ViewGroup.FOCUS_BEFORE_DESCENDANTS);app.root.requestFocus();return null;
        });
        driver.waitForIdleSync();SystemClock.sleep(1200);
        Bitmap screenshot=driver.getUiAutomation().takeScreenshot();
        if(screenshot==null)throw new AssertionError("Screenshot capture failed: "+name);
        File directory=driver.getTargetContext().getExternalFilesDir("screenshots");
        if(directory==null||(!directory.isDirectory()&&!directory.mkdirs()))throw new AssertionError("Screenshot directory unavailable");
        try(FileOutputStream out=new FileOutputStream(new File(directory,name))){if(!screenshot.compress(Bitmap.CompressFormat.PNG,100,out))throw new AssertionError("PNG encoding failed");}
        finally{screenshot.recycle();}
    }
}

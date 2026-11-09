package ai.wormwright.notes;
import android.widget.*;
import android.view.View;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;
import org.robolectric.android.controller.ActivityController;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class) @Config(sdk=35) @GraphicsMode(GraphicsMode.Mode.NATIVE)
public class ChecklistWrappingTest {
 @Test public void wrappedEditingTickingAndSavingKeepOneLogicalItem()throws Exception{
  RuntimeEnvironment.getApplication().deleteDatabase("notes.db");
  try(ActivityController<MainActivity> c=Robolectric.buildActivity(MainActivity.class).setup()){
   MainActivity a=c.get();a.editor(-1);a.title.setText("Sample wishes");a.body.setText("[ ] A long fictional item with action figures and a much larger transforming robot\n[x] Board games for rainy afternoons");a.checklistMode=true;a.showChecklist();assertTrue(a.save());long id=a.editing;
   Shadows.shadowOf(android.os.Looper.getMainLooper()).idle();
   a.root.measure(View.MeasureSpec.makeMeasureSpec(360,View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(900,View.MeasureSpec.EXACTLY));a.root.layout(0,0,360,900);
   LinearLayout row=(LinearLayout)a.checklist.getChildAt(0);EditText item=(EditText)row.getChildAt(1);
   assertTrue("Expected wrapped text at width "+item.getWidth()+", got "+item.getLineCount()+" lines",item.getLineCount()>1);assertTrue(item.getHeight()>item.getLineHeight());
   item.append("\nwith accessories");assertTrue(item.getText().toString().endsWith("robot with accessories"));assertEquals(2,a.body.getText().toString().split("\n",-1).length);
   ((CheckBox)row.getChildAt(0)).setChecked(true);assertTrue(a.body.getText().toString().startsWith("[x] "));assertTrue(a.save());a.home();a.editor(id);
   assertEquals(2,a.checklist.getChildCount()-1);LinearLayout reopened=(LinearLayout)a.checklist.getChildAt(0);assertTrue(((CheckBox)reopened.getChildAt(0)).isChecked());assertTrue(((EditText)reopened.getChildAt(1)).getText().toString().endsWith("robot with accessories"));
   reopened.getChildAt(2).performClick();assertEquals(1,a.body.getText().toString().split("\n",-1).length);assertTrue(a.body.getText().toString().contains("Board games"));
  }
 }
}

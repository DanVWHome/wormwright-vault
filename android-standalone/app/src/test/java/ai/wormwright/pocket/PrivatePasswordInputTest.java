package ai.wormwright.pocket;
import android.app.Activity;
import android.text.method.PasswordTransformationMethod;
import android.view.View;
import android.view.autofill.AutofillValue;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class)
@Config(manifest=Config.NONE,sdk=35,application=android.app.Application.class)
public class PrivatePasswordInputTest {
 @Test public void storedAndTypedSecretsStayMaskedAndPrivate(){
  Activity activity=Robolectric.buildActivity(Activity.class).setup().get();PrivatePasswordInput field=new PrivatePasswordInput(activity);activity.setContentView(field);field.setText("Invented NAS secret!");
  assertTrue(field.getTransformationMethod() instanceof PasswordTransformationMethod);assertFalse(field.getTransformationMethod().getTransformation(field.getText(),field).toString().contains("Invented"));
  assertEquals(View.AUTOFILL_TYPE_NONE,field.getAutofillType());assertNull(field.getAutofillValue());field.autofill(AutofillValue.forText("Unwanted replacement"));assertEquals("Invented NAS secret!",field.getText().toString());
  assertFalse(field.isSuggestionsEnabled());assertFalse(field.isSaveEnabled());assertEquals(View.IMPORTANT_FOR_CONTENT_CAPTURE_NO_EXCLUDE_DESCENDANTS,field.getImportantForContentCapture());
 }
 @Test public void keyboardReceivesNoLearningOrSurroundingSecret(){
  Activity activity=Robolectric.buildActivity(Activity.class).setup().get();PrivatePasswordInput field=new PrivatePasswordInput(activity);activity.setContentView(field);field.setText("InventedSecret");field.setSelection(field.length());
  EditorInfo info=new EditorInfo();InputConnection connection=field.onCreateInputConnection(info);assertNotNull(connection);assertTrue((info.imeOptions&EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING)!=0);assertTrue((info.imeOptions&EditorInfo.IME_FLAG_NO_EXTRACT_UI)!=0);CharSequence context=info.getInitialTextBeforeCursor(100,0);assertTrue(context==null||context.length()==0);
  connection.commitText("!Ab9",1);assertEquals("InventedSecret!Ab9",field.getText().toString());
 }
}

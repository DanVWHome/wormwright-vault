package ai.wormwright.notes.hardware;

import android.app.Activity;
import android.text.Editable;
import android.text.InputType;
import android.text.method.PasswordTransformationMethod;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.widget.EditText;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import static org.junit.Assert.*;

/** Actual Android widgets in both app test tasks, without using a real key. */
@RunWith(RobolectricTestRunner.class)
@Config(manifest = Config.NONE, sdk = 35, application = android.app.Application.class)
public class YubiKeyPinInputTest {
    private YubiKeyPinInput create() {
        Activity activity = Robolectric.buildActivity(Activity.class).setup().get();
        YubiKeyPinInput entry = new YubiKeyPinInput(activity);
        activity.setContentView(entry);
        return entry;
    }
    private void privateAndMasked(EditText input) {
        assertTrue(input.getTransformationMethod() instanceof PasswordTransformationMethod);
        assertFalse(input.isSuggestionsEnabled());
        assertEquals(0, input.getInputType() & InputType.TYPE_TEXT_FLAG_AUTO_CORRECT);
        assertFalse(input.isSaveEnabled());
        assertEquals(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS, input.getImportantForAutofill());
        assertEquals(View.IMPORTANT_FOR_CONTENT_CAPTURE_NO_EXCLUDE_DESCENDANTS, input.getImportantForContentCapture());
        assertTrue((input.getImeOptions() & EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING) != 0);
        assertTrue((input.getImeOptions() & EditorInfo.IME_FLAG_NO_EXTRACT_UI) != 0);
    }
    @Test public void defaultsToNumberPasswordKeyboardWithVisibleSwitch() {
        YubiKeyPinInput entry = create();
        assertEquals(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD, entry.input.getInputType());
        assertEquals("Use letters and symbols", entry.keyboardToggle.getText().toString());
        assertEquals(View.VISIBLE, entry.keyboardToggle.getVisibility());
        privateAndMasked(entry.input);
    }
    @Test public void bothDirectionsPreserveEditableSelectionAndMixedPin() {
        YubiKeyPinInput entry = create();
        entry.input.setText("12aB!#9"); entry.input.setSelection(2, 5);
        Editable original = entry.input.getText();
        for (int i = 0; i < 4; i++) {
            entry.keyboardToggle.performClick();
            assertEquals(InputType.TYPE_CLASS_TEXT, entry.input.getInputType() & InputType.TYPE_MASK_CLASS);
            assertTrue((entry.input.getInputType() & InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS) != 0);
            assertEquals("Use numbers", entry.keyboardToggle.getText().toString());
            privateAndMasked(entry.input);
            entry.keyboardToggle.performClick();
            assertEquals(InputType.TYPE_CLASS_NUMBER, entry.input.getInputType() & InputType.TYPE_MASK_CLASS);
            assertEquals("Use letters and symbols", entry.keyboardToggle.getText().toString());
            assertSame(original, entry.input.getText());
            assertEquals("12aB!#9", entry.input.getText().toString());
            assertEquals(2, entry.input.getSelectionStart()); assertEquals(5, entry.input.getSelectionEnd());
            privateAndMasked(entry.input);
        }
    }
    @Test public void numericPreferenceDoesNotFilterAlphanumericInput() {
        YubiKeyPinInput entry = create();
        android.view.inputmethod.InputConnection connection = entry.input.onCreateInputConnection(new EditorInfo());
        assertNotNull(connection);
        connection.commitText("Ab!29", 1);
        assertEquals("Ab!29", entry.input.getText().toString());
        entry.keyboardToggle.performClick();
        connection = entry.input.onCreateInputConnection(new EditorInfo());
        connection.commitText("@Z", 1);
        entry.keyboardToggle.performClick();
        assertEquals("Ab!29@Z", entry.input.getText().toString());
        privateAndMasked(entry.input);
    }
    @Test public void newPromptReturnsToNumericWithoutRememberingPin() {
        YubiKeyPinInput first = create(); first.input.setText("Dummy!123"); first.keyboardToggle.performClick();
        YubiKeyPinInput next = create();
        assertEquals(0, next.input.length());
        assertEquals(InputType.TYPE_CLASS_NUMBER, next.input.getInputType() & InputType.TYPE_MASK_CLASS);
        privateAndMasked(next.input);
    }
}

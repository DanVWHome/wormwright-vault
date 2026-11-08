package ai.wormwright.pocket;

import android.content.Context;
import android.text.InputType;
import android.text.method.PasswordTransformationMethod;
import android.view.View;
import android.view.ViewStructure;
import android.view.autofill.AutofillValue;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.EditText;

/** App-owned secrets: no password-manager handoff or keyboard learning. */
final class PrivatePasswordInput extends EditText {
    PrivatePasswordInput(Context context) {
        super(context);
        setSingleLine(true);
        setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD
            | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        setTransformationMethod(PasswordTransformationMethod.getInstance());
        setImeOptions(EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING | EditorInfo.IME_FLAG_NO_EXTRACT_UI);
        setSaveEnabled(false);
        setAutofillHints((String[])null);
        setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);
        setImportantForContentCapture(View.IMPORTANT_FOR_CONTENT_CAPTURE_NO_EXCLUDE_DESCENDANTS);
    }
    @Override public int getAutofillType() { return View.AUTOFILL_TYPE_NONE; }
    @Override public AutofillValue getAutofillValue() { return null; }
    @Override public void autofill(AutofillValue value) { }
    @Override public void onProvideAutofillStructure(ViewStructure structure,int flags) {
        structure.setAutofillType(View.AUTOFILL_TYPE_NONE);
        structure.setDataIsSensitive(true);
    }
    @Override public InputConnection onCreateInputConnection(EditorInfo attributes) {
        InputConnection connection=super.onCreateInputConnection(attributes);
        attributes.imeOptions |= EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING | EditorInfo.IME_FLAG_NO_EXTRACT_UI;
        attributes.inputType |= InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS;
        attributes.setInitialSurroundingText("");
        return connection;
    }
}

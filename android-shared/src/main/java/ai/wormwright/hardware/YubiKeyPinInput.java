package ai.wormwright.hardware;

import android.content.Context;
import android.text.InputType;
import android.text.method.PasswordTransformationMethod;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;

/** Keyboard preference only: the editor always accepts a full FIDO2 PIN. */
final class YubiKeyPinInput extends LinearLayout {
    final EditText input;
    final Button keyboardToggle;
    private boolean numbers = true;
    private static final int TEXT_PASSWORD = InputType.TYPE_CLASS_TEXT
        | InputType.TYPE_TEXT_VARIATION_PASSWORD | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS;

    YubiKeyPinInput(Context context) {
        super(context);
        setOrientation(VERTICAL);
        input = new EditText(context);
        input.setHint("YubiKey PIN");
        // A text key listener keeps existing alphanumeric PINs valid. Changing
        // only the raw type below avoids installing a digits-only filter.
        input.setInputType(TEXT_PASSWORD);
        input.setSingleLine(true);
        input.setTransformationMethod(PasswordTransformationMethod.getInstance());
        input.setImeOptions(EditorInfo.IME_ACTION_DONE | EditorInfo.IME_FLAG_NO_EXTRACT_UI
            | EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING);
        input.setSaveEnabled(false);
        input.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);
        input.setImportantForContentCapture(View.IMPORTANT_FOR_CONTENT_CAPTURE_NO_EXCLUDE_DESCENDANTS);
        addView(input, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT));
        keyboardToggle = new Button(context);
        keyboardToggle.setAllCaps(false);
        addView(keyboardToggle, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT));
        applyKeyboardPreference();
        keyboardToggle.setOnClickListener(v -> {
            numbers = !numbers;
            applyKeyboardPreference();
            input.requestFocus();
            InputMethodManager keyboard = context.getSystemService(InputMethodManager.class);
            if (keyboard != null) {
                keyboard.restartInput(input);
                keyboard.showSoftInput(input, InputMethodManager.SHOW_IMPLICIT);
            }
        });
    }

    private void applyKeyboardPreference() {
        // Keep the same masked Editable and selection, including letters and
        // symbols when switching back to the numeric keyboard.
        input.setRawInputType(numbers
            ? InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD
            : TEXT_PASSWORD);
        keyboardToggle.setText(numbers ? "Use letters and symbols" : "Use numbers");
    }
}

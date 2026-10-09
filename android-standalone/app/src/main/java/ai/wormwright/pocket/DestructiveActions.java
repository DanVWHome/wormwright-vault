package ai.wormwright.pocket;

import android.app.*;
import android.content.*;
import android.hardware.biometrics.*;
import android.os.*;
import android.net.Uri;
import android.provider.DocumentsContract;
import android.provider.OpenableColumns;
import android.view.WindowManager;
import android.widget.*;
import java.util.*;

/** Explicit user-selected documents only. No folder traversal or inferred deletion. */
final class DestructiveActions {
    static final int BACKUPS = 903;
    private final Activity activity;
    private boolean resumed, authenticating;
    private int generation;
    private Runnable pending;
    private CancellationSignal cancellation;
    private AlertDialog dialog;
    DestructiveActions(Activity activity) { this.activity=activity; }
    void onResume() { resumed=true; if(pending!=null) { Runnable action=pending; pending=null; action.run(); } }
    void onPause() { resumed=false; if(dialog!=null)dialog.dismiss(); if(!authenticating){generation++;pending=null;} }
    void onDestroy() { generation++;pending=null;if(cancellation!=null)cancellation.cancel(); }
    void authenticate(Runnable action) {
        if(!((KeyguardManager)activity.getSystemService(Context.KEYGUARD_SERVICE)).isDeviceSecure()) { notice("Set a secure phone PIN, pattern or password first.");return; }
        final int token=++generation;authenticating=true;pending=null;
        cancellation=new CancellationSignal();
        new BiometricPrompt.Builder(activity).setTitle("Authorize permanent deletion")
            .setDescription("Confirm your identity before reviewing what will be deleted.")
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG | BiometricManager.Authenticators.DEVICE_CREDENTIAL)
            .build().authenticate(cancellation,activity.getMainExecutor(),new BiometricPrompt.AuthenticationCallback(){
                @Override public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult result){
                    if(token!=generation||activity.isFinishing())return;
                    // Credential UI can finish before the app resumes. Keep its result
                    // only until that resume; leaving the final review invalidates it.
                    pending=()->{if(token!=generation||!resumed)return;authenticating=false;action.run();};
                    if(resumed){Runnable next=pending;pending=null;next.run();}
                }
                @Override public void onAuthenticationError(int code,CharSequence error){if(token==generation){authenticating=false;pending=null;notice("Deletion cancelled. Nothing was removed.");}}
            });
    }
    void confirm(String title,String message,Runnable action) {
        final int token=generation;
        LinearLayout content=new LinearLayout(activity);content.setOrientation(LinearLayout.VERTICAL);int pad=(int)(20*activity.getResources().getDisplayMetrics().density);content.setPadding(pad,pad,pad,pad);
        TextView explanation=new TextView(activity);explanation.setText(message+"\n\nThis cannot be undone in this app. Type DELETE to confirm.");content.addView(explanation);
        EditText typed=new EditText(activity);typed.setSingleLine(true);typed.setHint("DELETE");typed.setImportantForAutofill(android.view.View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);content.addView(typed);
        ScrollView scroll=new ScrollView(activity);scroll.addView(content);
        final AlertDialog review=new AlertDialog.Builder(activity).setTitle(title).setView(scroll).setNegativeButton("Cancel",null).setPositiveButton("Delete permanently",null).create();dialog=review;
        review.setOnDismissListener(d->{typed.setText("");if(dialog==review)dialog=null;});
        review.setOnShowListener(d->review.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            if(!resumed||token!=generation||!review.isShowing())return;
            if(!"DELETE".equals(typed.getText().toString())){typed.setError("Type DELETE exactly.");return;}
            review.dismiss();generation++;action.run();
        }));review.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);review.show();
    }
    void chooseBackups() {
        Intent picker=new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE)
            .putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        activity.startActivityForResult(picker,BACKUPS);
    }
    boolean result(int request,int result,Intent data) {
        if(request!=BACKUPS)return false;
        if(result!=Activity.RESULT_OK||data==null)return true;
        LinkedHashSet<Uri> selected=new LinkedHashSet<>();
        if(data.getClipData()!=null)for(int i=0;i<data.getClipData().getItemCount();i++)selected.add(data.getClipData().getItemAt(i).getUri());
        else if(data.getData()!=null)selected.add(data.getData());
        if(selected.isEmpty())return true;
        StringBuilder names=new StringBuilder();
        for(Uri uri:selected){
            if(!DocumentsContract.isDocumentUri(activity,uri)){notice("This provider does not support document deletion. Nothing was removed.");return true;}
            try(android.database.Cursor cursor=activity.getContentResolver().query(uri,new String[]{OpenableColumns.DISPLAY_NAME,DocumentsContract.Document.COLUMN_FLAGS},null,null,null)){
                if(cursor==null||!cursor.moveToFirst()||(cursor.getInt(1)&DocumentsContract.Document.FLAG_SUPPORTS_DELETE)==0)throw new Exception();
                names.append(cursor.getString(0)).append("\n");
            }catch(Exception e){notice("A selected document cannot be deleted by this app. Nothing was removed.");return true;}
        }
        final String list=names.toString();
        // Authorization is intentionally requested after returning from the picker.
        activity.getWindow().getDecorView().post(()->authenticate(()->confirm("Delete selected backups",selected.size()+" selected documents:\n"+list+"\nOnly these documents will be removed. Select only backups you intend to destroy. Other copies and provider trash may remain.",()->{
            int removed=0;for(Uri uri:selected)try{if(DocumentsContract.deleteDocument(activity.getContentResolver(),uri))removed++;}catch(Exception ignored){}
            notice("Deleted "+removed+" of "+selected.size()+" selected documents. "+(removed==selected.size()?"Other copies and provider trash may remain.":"Some could not be deleted; check them in Files."));
        })));
        return true;
    }
    void notice(String message){activity.getWindow().getDecorView().post(()->{if(!activity.isFinishing())new AlertDialog.Builder(activity).setMessage(message).setPositiveButton("OK",null).show();});}
}

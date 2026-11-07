package ai.wormwright.hardware;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.util.Base64;
import android.view.WindowManager;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import com.yubico.yubikit.android.YubiKitManager;
import com.yubico.yubikit.android.transport.nfc.NfcConfiguration;
import com.yubico.yubikit.android.transport.nfc.NfcNotAvailable;
import com.yubico.yubikit.android.transport.usb.UsbConfiguration;
import com.yubico.yubikit.core.YubiKeyDevice;
import com.yubico.yubikit.core.application.CommandState;
import com.yubico.yubikit.fido.Cbor;
import com.yubico.yubikit.fido.client.BasicWebAuthnClient;

import com.yubico.yubikit.fido.ctap.Ctap2Session;
import com.yubico.yubikit.fido.webauthn.*;
import org.json.JSONObject;
import org.json.JSONArray;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.spec.*;
import java.math.BigInteger;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Explicit, foreground-only native FIDO2/hmac-secret over USB or NFC.
 * No browser, Play Services, OTP slot changes, PIN changes, or reset operations. */
public final class YubiKeyUnlock {
    // Must match desktop yubikey_auth.py. Do not change for existing enrollments.
    public static final String RP_ID = "atlas-portable.local";
    private final Activity activity;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private volatile Attempt current;
    public interface Callback { void complete(JSONObject result); void failed(String message); }
    public YubiKeyUnlock(Activity activity) { this.activity=activity; }
    public boolean active() { return current!=null; }
    public void cancel() {
        Attempt a=current; current=null;
        if(a!=null) a.close();
    }
    /** request contains public enrollment data only: full credential and salt. */
    public void unlock(JSONObject request, Callback done) { begin(request,false,done); }
    public void unlockChoices(JSONArray choices, Callback done) {
        cancel();
        if(choices.length()==0){done.failed("No YubiKey is enrolled for this account. Use the existing unlock method and enroll a key first.");return;}
        try {
            if(choices.length()==1){unlock(choices.getJSONObject(0),done);return;}
            if(choices.length()>4)throw new IllegalArgumentException();
            String[] labels=new String[choices.length()];for(int i=0;i<labels.length;i++)labels[i]=choices.getJSONObject(i).getString("label");
            Attempt selection=new Attempt(new JSONObject(),false,done);current=selection;
            selection.dialog=new AlertDialog.Builder(activity).setTitle("Which YubiKey are you using?").setItems(labels,(d,i)->{
                if(current!=selection)return;
                try{JSONObject request=choices.getJSONObject(i);cancel();unlock(request,done);}catch(Exception e){fail(selection,"Key selection failed.");}
            }).setNegativeButton("Cancel",(d,w)->fail(selection,"Key selection cancelled.")).create();
            selection.dialog.setOnCancelListener(d->fail(selection,"Key selection cancelled."));
            selection.dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);selection.dialog.show();
        }catch(Exception e){done.failed("Invalid key enrollment list. Existing data was kept.");}
    }
    public void enroll(Callback done) { begin(new JSONObject(),true,done); }
    private void begin(JSONObject request, boolean enroll, Callback done) {
        cancel();
        Attempt a=new Attempt(request,enroll,done);current=a;
        LinearLayout view=new LinearLayout(activity);view.setOrientation(LinearLayout.VERTICAL);view.setPadding(32,16,32,16);
        TextView note=new TextView(activity);note.setText("Enter this YubiKey’s FIDO2 PIN. Then plug it into USB-C or hold it against the phone’s NFC reader until finished. For USB, touch the gold contact when asked.");view.addView(note);
        EditText input=new EditText(activity);input.setHint("YubiKey PIN");input.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);input.setSaveEnabled(false);input.setImportantForAutofill(android.view.View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);view.addView(input);
        a.dialog=new AlertDialog.Builder(activity).setTitle(enroll?"Enroll YubiKey":"Unlock with YubiKey").setView(view)
            .setNegativeButton("Cancel",(d,w)->fail(a,"YubiKey operation cancelled. Existing unlock methods remain available."))
            .setPositiveButton("Continue",null).create();
        a.dialog.setOnCancelListener(d->fail(a,"YubiKey operation cancelled."));
        a.dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        a.dialog.show();
        a.dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            if(input.length()<4){input.setError("Enter the key’s PIN (at least 4 characters).");return;}
            a.pin=new char[input.length()];android.text.TextUtils.getChars(input.getText(),0,input.length(),a.pin,0);input.getText().clear();
            input.setVisibility(android.view.View.GONE);a.dialog.getButton(AlertDialog.BUTTON_POSITIVE).setEnabled(false);
            note.setText("Connect one YubiKey over USB-C, or hold it against the NFC reader. Keep it in place. Touch the gold contact if requested.");
            try { a.manager=new YubiKitManager(activity);
                a.manager.startUsbDiscovery(new UsbConfiguration(), device->connect(a,device));
            } catch(RuntimeException e){fail(a,"USB key access is unavailable. Check device permissions and retry.");return;}
            try { a.manager.startNfcDiscovery(new NfcConfiguration(),activity,device->connect(a,device)); }
            catch(NfcNotAvailable e){note.append("\nNFC is unavailable or off; USB-C is still available.");}
            if(current!=a)return;
            a.timeout=()->fail(a,"YubiKey operation timed out. Reopen and try again.");ui.postDelayed(a.timeout,60000);
        });
    }
    private void connect(Attempt a,YubiKeyDevice device) {
        if(current!=a || !a.claimed.compareAndSet(false,true))return;
        Ctap2Session.create(device, value->{
            JSONObject result=null;String error=null;
            try(Ctap2Session session=value.getValue()) {
                a.session=session;
                if(a.cancelled) return;
                {
                    // The outer scope owns the session; close it exactly once.
                    BasicWebAuthnClient client=new BasicWebAuthnClient(session,Collections.singletonList(new RawHmacSecretExtension()));
                    if(!client.isPinConfigured())throw new GeneralSecurityException("Set the key’s FIDO2 PIN on your computer first.");
                    if(a.cancelled)throw new GeneralSecurityException("Cancelled");
                    if(a.enroll) {
                        byte[] challenge=random(32);byte[] data=clientData("webauthn.create",challenge);
                        PublicKeyCredentialCreationOptions options=new PublicKeyCredentialCreationOptions(
                            new PublicKeyCredentialRpEntity("Wormwright Vault",RP_ID),
                            new PublicKeyCredentialUserEntity("Wormwright vault",random(32),"Wormwright vault"),challenge,
                            Collections.singletonList(new PublicKeyCredentialParameters("public-key",-7)),60000L,null,
                            new AuthenticatorSelectionCriteria("cross-platform","discouraged","required"),"none",
                            Extensions.fromMap(Collections.singletonMap("hmacCreateSecret",true)));
                        PublicKeyCredential registration=client.makeCredential(data,options,RP_ID,a.pin,null,a.command);
                        AuthenticatorAttestationResponse response=(AuthenticatorAttestationResponse)registration.getResponse();
                        byte[] auth=response.getAuthenticatorData().getBytes();
                        if(!Arrays.equals(data,response.getClientDataJson()) || (auth[32]&5)!=5
                            || !MessageDigest.isEqual(Arrays.copyOf(auth,32),MessageDigest.getInstance("SHA-256").digest(RP_ID.getBytes(StandardCharsets.UTF_8))))throw new GeneralSecurityException("Invalid key registration");
                        Map<String,Object> outputs=registration.getClientExtensionResults().toMap(SerializationType.CBOR);
                        if(!Boolean.TRUE.equals(outputs.get("hmacCreateSecret")))throw new GeneralSecurityException("Key lacks offline vault support");
                        AttestedCredentialData cred=response.getAuthenticatorData().getAttestedCredentialData();
                        byte[] full=ByteBuffer.allocate(18+cred.getCredentialId().length+Cbor.encode(cred.getCosePublicKey()).length)
                            .put(cred.getAaguid()).putShort((short)cred.getCredentialId().length).put(cred.getCredentialId()).put(Cbor.encode(cred.getCosePublicKey())).array();
                        byte[] salt=random(32);
                        // A verified assertion proves the new credential works before vault metadata is changed.
                        byte[] secret=assertKey(client,cred,salt,a);
                        try{result=new JSONObject().put("credential",b64(full)).put("salt",b64(salt)).put("response",b64(secret));}
                        finally{Arrays.fill(secret,(byte)0);}
                    } else {
                        byte[] full=decode(a.request.getString("credential"));
                        AttestedCredentialData cred=AttestedCredentialData.parseFrom(ByteBuffer.wrap(full));
                        byte[] secret=assertKey(client,cred,decode(a.request.getString("salt")),a);
                        try{result=new JSONObject().put("response",b64(secret)).put("request",a.request.toString());}finally{Arrays.fill(secret,(byte)0);}
                    }
                }
            } catch(Exception e) {
                // Never log exceptions, PINs, CTAP payloads or hmac-secret output.
                error="YubiKey authentication failed. Check the key and PIN, then retry explicitly. Wrong PINs consume the key’s limited attempts; the app never retries automatically. Existing vault data was kept.";
            } finally { a.session=null;if(a.pin!=null)Arrays.fill(a.pin,'\0'); }
            final JSONObject output=result;final String problem=error;
            ui.post(()->{if(current!=a||a.cancelled)return;current=null;a.close();if(problem!=null)a.done.failed(problem);else a.done.complete(output);});
        });
    }
    private static byte[] assertKey(BasicWebAuthnClient client,AttestedCredentialData cred,byte[] salt,Attempt a)throws Exception {
        if(a.cancelled)throw new GeneralSecurityException("Cancelled");
        if(salt.length!=32)throw new GeneralSecurityException("Invalid wrapping salt");
        byte[] challenge=random(32);byte[] data=clientData("webauthn.get",challenge);
        Map<String,Object> get=new HashMap<>();get.put("salt1",b64url(salt));
        PublicKeyCredentialRequestOptions options=new PublicKeyCredentialRequestOptions(challenge,60000L,RP_ID,
            Collections.singletonList(new PublicKeyCredentialDescriptor("public-key",cred.getCredentialId(),null)),"required",
            Extensions.fromMap(Collections.singletonMap("hmacGetSecret",get)));
        PublicKeyCredential result;
        try{result=client.getAssertion(data,options,RP_ID,a.pin,a.command);}
        catch(com.yubico.yubikit.fido.client.MultipleAssertionsAvailable e){throw new GeneralSecurityException("Unexpected multiple key assertions");}
        AuthenticatorAssertionResponse r=(AuthenticatorAssertionResponse)result.getResponse();
        Map<String,Object> outputs=result.getClientExtensionResults().toMap(SerializationType.CBOR);
        @SuppressWarnings("unchecked") Map<String,Object> hmac=(Map<String,Object>)outputs.get("hmacGetSecret");
        byte[] secret=hmac==null?null:(byte[])hmac.get("output1");
        try{AssertionVerifier.verify(publicKey(cred.getCosePublicKey()),cred.getCredentialId(),result.getRawId(),RP_ID,data,r.getClientDataJson(),r.getAuthenticatorData(),r.getSignature(),secret);return secret;}
        catch(Exception e){if(secret!=null)Arrays.fill(secret,(byte)0);throw e;}
    }
    private static PublicKey publicKey(Map<Integer,?> cose)throws Exception {
        if(!Integer.valueOf(2).equals(cose.get(1)) || !Integer.valueOf(-7).equals(cose.get(3)) || !Integer.valueOf(1).equals(cose.get(-1)))
            throw new GeneralSecurityException("Only ES256 vault credentials are supported");
        AlgorithmParameters p=AlgorithmParameters.getInstance("EC");p.init(new ECGenParameterSpec("secp256r1"));
        return KeyFactory.getInstance("EC").generatePublic(new ECPublicKeySpec(new ECPoint(new BigInteger(1,(byte[])cose.get(-2)),new BigInteger(1,(byte[])cose.get(-3))),p.getParameterSpec(ECParameterSpec.class)));
    }
    private void fail(Attempt a,String message){if(current!=a)return;current=null;a.close();a.done.failed(message);}
    private static byte[] random(int n){byte[] b=new byte[n];new SecureRandom().nextBytes(b);return b;}
    private static byte[] clientData(String type,byte[] challenge)throws Exception{return new JSONObject().put("type",type).put("challenge",b64url(challenge)).put("origin","https://"+RP_ID).put("crossOrigin",false).toString().getBytes(StandardCharsets.UTF_8);}
    public static String b64(byte[] v){return Base64.encodeToString(v,Base64.NO_WRAP);}
    private static String b64url(byte[] v){return Base64.encodeToString(v,Base64.URL_SAFE|Base64.NO_WRAP|Base64.NO_PADDING);}
    private static byte[] decode(String v){return Base64.decode(v,Base64.DEFAULT);}
    private final class Attempt {
        final JSONObject request;final boolean enroll;final Callback done;final AtomicBoolean claimed=new AtomicBoolean();
        final CommandState command=new CommandState();volatile boolean cancelled;char[] pin;volatile Ctap2Session session;
        YubiKitManager manager;AlertDialog dialog;Runnable timeout;
        Attempt(JSONObject r,boolean e,Callback d){request=r;enroll=e;done=d;}
        void close(){cancelled=true;command.cancel();if(timeout!=null)ui.removeCallbacks(timeout);if(manager!=null){try{manager.stopNfcDiscovery(activity);}catch(RuntimeException ignored){}try{manager.stopUsbDiscovery();}catch(RuntimeException ignored){}}if(dialog!=null)dialog.dismiss();if(pin!=null)Arrays.fill(pin,'\0');}
    }
}

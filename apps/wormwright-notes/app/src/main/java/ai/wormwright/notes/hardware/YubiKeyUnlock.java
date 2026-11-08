package ai.wormwright.notes.hardware;

import android.app.Activity;
import android.app.PendingIntent;
import android.content.*;
import android.hardware.usb.UsbManager;
import android.os.Build;
import com.yubico.yubikit.android.transport.usb.UsbYubiKeyDevice;
import android.app.AlertDialog;
import android.os.Handler;
import android.os.Looper;
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
import com.yubico.yubikit.core.YubiKeyConnection;
import com.yubico.yubikit.core.fido.FidoConnection;
import com.yubico.yubikit.core.smartcard.SmartCardConnection;
import com.yubico.yubikit.android.transport.nfc.NfcYubiKeyDevice;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
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
    // Dedicated Notes namespace; never reuse or modify Vault enrollments.
    public static final String RP_ID = "notes.wormwright.local";
    private final Activity activity;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private volatile Attempt current;
    private final ExecutorService hardwareWorker=Executors.newSingleThreadExecutor();
    public interface Callback { void complete(JSONObject result); void failed(String message); }
    private final ForegroundNfcLease<YubiKitManager> nfcLease;
    public YubiKeyUnlock(Activity activity) {
        this.activity=activity;
        nfcLease=new ForegroundNfcLease<>(manager->{try{manager.stopNfcDiscovery(activity);}catch(RuntimeException ignored){}});
    }
    private boolean foreground=true;
    /** Only the exact USB permission overlay may temporarily pause discovery.
     * The host hides its content and cancels if it is actually stopped. */
    public boolean pauseForUsbPermission() {
        if(current==null||!current.permissionPending)return false;
        foreground=false;return true;
    }
    public void resume() {
        foreground=true;Attempt a=current;
        if(a!=null&&a.pending!=null){Runnable next=a.pending;a.pending=null;ui.post(()->{if(current==a)next.run();});}
    }
    public boolean active() { return current!=null; }
    public void cancel() {
        Attempt a=current; current=null;
        if(a!=null) a.close(true);
    }
    /** Host must call this when actually leaving the foreground. */
    public void stop() {
        Attempt a=current;current=null;if(a!=null)a.close(false);nfcLease.release();
    }
    public void dispose(){stop();hardwareWorker.shutdownNow();}
    /** request contains public enrollment data only: full credential and salt. */
    public void unlock(JSONObject request, Callback done) { begin(request,false,done); }
    public void unlockChoices(JSONArray choices, Callback done) {
        if(choices.length()==0){done.failed("No YubiKey is enrolled for this account. Use the existing unlock method and enroll a key first.");return;}
        if(choices.length()>4){done.failed("Invalid key enrollment list. Existing data was kept.");return;}
        try{begin(new JSONObject().put("choices",choices),false,done);}
        catch(Exception e){done.failed("Invalid key enrollment list. Existing data was kept.");}
    }
    public void enroll(Callback done) { enroll(new JSONArray(),done); }
    public void enroll(JSONArray existing,Callback done) {
        if(existing.length()>=4){done.failed("Four keys are already registered.");return;}
        try{begin(new JSONObject().put("exclude",existing),true,done);}catch(Exception e){done.failed("Invalid existing keys");}
    }
    private void begin(JSONObject request, boolean enroll, Callback done) {
        cancel();
        Attempt a=new Attempt(request,enroll,done);current=a;
        LinearLayout view=new LinearLayout(activity);view.setOrientation(LinearLayout.VERTICAL);view.setPadding(32,16,32,16);
        TextView note=new TextView(activity);a.note=note;note.setText("Connect your YubiKey over USB-C or hold it against the NFC reader, and enter its PIN. Either order works. Keep an NFC key in place until the backup operation finishes.");view.addView(note);
        YubiKeyPinInput pinEntry=new YubiKeyPinInput(activity);EditText input=pinEntry.input;view.addView(pinEntry);
        a.dialog=new AlertDialog.Builder(activity).setTitle(enroll?"Enroll YubiKey":"Unlock with YubiKey").setView(view)
            .setNegativeButton("Cancel",(d,w)->fail(a,"YubiKey operation cancelled. Existing unlock methods remain available."))
            .setPositiveButton("Continue",null).create();
        a.dialog.setOnCancelListener(d->fail(a,"YubiKey operation cancelled."));
        YubiKeyKeyboardGuard.install(a.dialog.getWindow());a.dialog.getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        a.dialog.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE|WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        a.dialog.show();
        input.requestFocus();
        a.dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            if(current!=a||a.cancelled)return;
            if(input.length()<4){input.setError("Enter the key’s PIN (at least 4 characters).");return;}
            char[] enteredPin=new char[input.length()];android.text.TextUtils.getChars(input.getText(),0,input.length(),enteredPin,0);a.pinBuffer.set(enteredPin);input.getText().clear();
            pinEntry.setVisibility(android.view.View.GONE);a.dialog.getButton(AlertDialog.BUTTON_POSITIVE).setVisibility(android.view.View.GONE);
            note.setText("Waiting for your YubiKey. Connect it over USB-C or hold it against the NFC reader. When the key flashes, touch its gold contact. No more on-screen confirmation is needed.");
            a.timeout=()->fail(a,"YubiKey authentication timed out. Connect the key or keep it against the NFC reader, then try again.");ui.postDelayed(a.timeout,60000);
            if(a.device!=null&&a.device.getTransport()==com.yubico.yubikit.core.Transport.NFC&&usbKeyPresent()){a.device=null;a.readiness.deviceLost();}
            if(a.readiness.pinSubmitted())connect(a,a.device);
        });
        try { a.manager=new YubiKitManager(activity);
                a.manager.startUsbDiscovery(new UsbConfiguration().handlePermissions(false), device->ui.post(()->usbConnect(a,device)));
            } catch(RuntimeException e){fail(a,"USB key access is unavailable. Check device permissions and retry.");return;}
            try { nfcLease.release();a.manager.startNfcDiscovery(NfcReaderSettings.create(),activity,device->ui.post(()->keyDetected(a,device)));a.nfcStarted=true; }
            catch(NfcNotAvailable e){note.append("\nNFC is unavailable or off; USB-C is still available.");}

    }
    private void usbConnect(Attempt a,UsbYubiKeyDevice device) {
        if(current!=a||a.cancelled)return;
        device.setOnClosed(()->ui.post(()->{
            if(current!=a||a.cancelled||a.device!=device)return;
            if(a.claimed.get())fail(a,"The USB key was disconnected during authentication. Reconnect it and start a new attempt.");
            else{a.device=null;a.readiness.deviceLost();if(a.note!=null)a.note.setText("USB key removed. Reconnect it to continue.");}
        }));
        if(device.hasPermission()){keyDetected(a,device);return;}
        if(a.permissionPending)return;
        String action=activity.getPackageName()+".YUBIKEY_PERMISSION."+UUID.randomUUID();
        a.permissionReceiver=new BroadcastReceiver(){
            @Override public void onReceive(Context context,Intent intent){
                if(!action.equals(intent.getAction())||current!=a)return;
                a.permissionPending=false;a.unregisterPermission();
                Runnable next=()->{if(current!=a)return;if(device.hasPermission())keyDetected(a,device);else fail(a,"USB permission was not granted. No key was added. Retry and allow access to the YubiKey.");};
                if(foreground)next.run();else a.pending=next;
            }
        };
        if(Build.VERSION.SDK_INT>=33)activity.registerReceiver(a.permissionReceiver,new IntentFilter(action),Context.RECEIVER_NOT_EXPORTED);
        else activity.registerReceiver(a.permissionReceiver,new IntentFilter(action));
        a.permissionPending=true;
        try {
            int flags=PendingIntent.FLAG_UPDATE_CURRENT;if(Build.VERSION.SDK_INT>=31)flags|=PendingIntent.FLAG_MUTABLE;
            PendingIntent permission=PendingIntent.getBroadcast(activity,0,new Intent(action).setPackage(activity.getPackageName()),flags);
            ((UsbManager)activity.getSystemService(Context.USB_SERVICE)).requestPermission(device.getUsbDevice(),permission);
        }catch(RuntimeException e){a.permissionPending=false;fail(a,"USB permission could not be requested. Existing notes and backups was kept.");}
    }
    private boolean usbKeyPresent(){
        UsbManager manager=(UsbManager)activity.getSystemService(Context.USB_SERVICE);
        for(android.hardware.usb.UsbDevice device:manager.getDeviceList().values())if(device.getVendorId()==0x1050)return true;
        return false;
    }
    private void keyDetected(Attempt a,YubiKeyDevice device) {
        if(current!=a||a.cancelled||a.claimed.get())return;
        if(device.getTransport()==com.yubico.yubikit.core.Transport.NFC&&usbKeyPresent())return;
        a.device=device;
        if(a.readiness.deviceDetected())connect(a,device);
        else if(a.note!=null)a.note.setText(device.getTransport()==com.yubico.yubikit.core.Transport.NFC?"NFC key detected. Keep it here and enter its PIN.":"YubiKey connected. Enter its PIN and continue.");
    }
    private void progress(Attempt a,String stage,String message) {
        a.stage=stage;ui.post(()->{if(current==a&&!a.cancelled&&a.note!=null)a.note.setText(a.nfc?"Keep the YubiKey against the phone until the backup operation finishes. No gold-contact touch is needed for NFC.":message);});
    }
    private void connect(Attempt a,YubiKeyDevice device) {
        if(current!=a || a.cancelled || !a.claimed.compareAndSet(false,true))return;
        a.nfc=device.getTransport()==com.yubico.yubikit.core.Transport.NFC;
        progress(a,"CONNECT",a.nfc?"NFC key detected. Hold it steadily against the phone until finished.":"Key connected. Reading its FIDO2 application…");
        hardwareWorker.execute(()->{
            JSONObject result=null;String error=null;char[] operationPin=null;
            try {
                if(a.cancelled)return;
                operationPin=a.pinBuffer.copyForOperation();
                Ctap2Session session=openSession(a,device);
                if(session==null)return;
                if(a.cancelled)return;
                {
                    // The physical connection owner handles cancellation and cleanup.
                    BasicWebAuthnClient client=new BasicWebAuthnClient(session,Collections.singletonList(new RawHmacSecretExtension()));
                    if(!client.isPinConfigured())throw new GeneralSecurityException("Set the key’s FIDO2 PIN on your computer first.");
                    if(a.cancelled)throw new GeneralSecurityException("Cancelled");
                    if(a.enroll) {
                        byte[] challenge=random(32);byte[] data=clientData("webauthn.create",challenge);
                        List<PublicKeyCredentialDescriptor> excluded=new ArrayList<>();
                        JSONArray existing=a.request.optJSONArray("exclude");
                        if(existing!=null)for(int i=0;i<existing.length();i++){
                            AttestedCredentialData prior=AttestedCredentialData.parseFrom(ByteBuffer.wrap(decode(existing.getJSONObject(i).getString("credential"))));
                            excluded.add(new PublicKeyCredentialDescriptor("public-key",prior.getCredentialId(),null));
                        }
                        PublicKeyCredentialCreationOptions options=new PublicKeyCredentialCreationOptions(
                            new PublicKeyCredentialRpEntity("Wormwright Notes backups",RP_ID),
                            new PublicKeyCredentialUserEntity("Wormwright Notes backup",random(32),"Wormwright Notes backup"),challenge,
                            Collections.singletonList(new PublicKeyCredentialParameters("public-key",-7)),60000L,excluded,
                            new AuthenticatorSelectionCriteria("cross-platform","discouraged","required"),"none",
                            Extensions.fromMap(Collections.singletonMap("hmacCreateSecret",true)));
                        progress(a,"CREATE","Creating the Notes backup credential. Wait for the key to flash, then touch its gold contact.");
                        PublicKeyCredential registration=client.makeCredential(data,options,RP_ID,operationPin,null,a.command);
                        AuthenticatorAttestationResponse response=(AuthenticatorAttestationResponse)registration.getResponse();
                        byte[] auth=response.getAuthenticatorData().getBytes();
                        if(!Arrays.equals(data,response.getClientDataJson()) || (auth[32]&5)!=5
                            || !MessageDigest.isEqual(Arrays.copyOf(auth,32),MessageDigest.getInstance("SHA-256").digest(RP_ID.getBytes(StandardCharsets.UTF_8))))throw new GeneralSecurityException("Invalid key registration");
                        Map<String,Object> outputs=registration.getClientExtensionResults().toMap(SerializationType.CBOR);
                        if(!Boolean.TRUE.equals(outputs.get("hmacCreateSecret")))throw new GeneralSecurityException("Key lacks offline encrypted-backup support");
                        AttestedCredentialData cred=response.getAuthenticatorData().getAttestedCredentialData();
                        byte[] full=ByteBuffer.allocate(18+cred.getCredentialId().length+Cbor.encode(cred.getCosePublicKey()).length)
                            .put(cred.getAaguid()).putShort((short)cred.getCredentialId().length).put(cred.getCredentialId()).put(Cbor.encode(cred.getCosePublicKey())).array();
                        byte[] salt=random(32);
                        // A verified assertion proves the new credential works before backup registration is changed.
                        progress(a,"VERIFY-NEW","Checking the new credential. Keep the key connected; touch again when it flashes.");
                        byte[] secret=assertKey(client,cred,salt,a,operationPin);
                        try{result=new JSONObject().put("credential",b64(full)).put("salt",b64(salt)).put("response",b64(secret));}
                        finally{Arrays.fill(secret,(byte)0);}
                    } else {
                        JSONArray choices=a.request.optJSONArray("choices");if(choices==null)choices=new JSONArray().put(a.request);
                        List<AttestedCredentialData> credentials=new ArrayList<>();Map<String,JSONObject> requests=new HashMap<>();Map<String,Object> salts=new HashMap<>();
                        for(int i=0;i<choices.length();i++){
                            JSONObject request=choices.getJSONObject(i);AttestedCredentialData cred=AttestedCredentialData.parseFrom(ByteBuffer.wrap(decode(request.getString("credential"))));
                            String id=CredentialSaltSelector.id(cred.getCredentialId());
                            if(requests.put(id,request)!=null)throw new GeneralSecurityException("Duplicate credential enrollment");
                            credentials.add(cred);salts.put(id,b64url(decode(request.getString("salt"))));
                        }
                        progress(a,"UNLOCK","Authenticating your enrolled YubiKey. Touch its gold contact when it flashes.");
                        byte[] secret=assertKeys(client,credentials,salts,a,operationPin);
                        JSONObject request=requests.get(CredentialSaltSelector.id(a.selectedCredential));
                        try{result=new JSONObject().put("response",b64(secret)).put("request",request.toString());}finally{Arrays.fill(secret,(byte)0);}

                    }
                }
            } catch(Exception e) {
                // Never log exceptions, PINs, CTAP payloads or hmac-secret output.
                error=KeyFailureMessage.describe(e,(a.nfc?"NFC-":"USB-")+a.stage);
             } finally {
                try{a.connectionOwner.close();}catch(Exception closing){if(error==null)error=KeyFailureMessage.describe(closing,(a.nfc?"NFC-":"USB-")+"CLOSE");}
                if(operationPin!=null)Arrays.fill(operationPin,'\0');a.pinBuffer.clear();
            }
            final JSONObject output=result;final String problem=error;
            ui.post(()->{if(current!=a||a.cancelled)return;
                Runnable finish=()->{if(current!=a||a.cancelled)return;current=null;a.close(true);if(problem!=null)a.done.failed(problem);else a.done.complete(output);};
                if(foreground)finish.run();else a.pending=finish;
            });
        });
    }
    /** Own the physical connection before constructing the session (which does
     * I/O). Cancellation can abort GetInfo/PIN exchange too. The owner closes
     * once; neither the SDK callback wrapper nor Ctap2Session closes it again. */
    private static Ctap2Session openSession(Attempt a,YubiKeyDevice device)throws Exception{
        YubiKeyConnection connection;
        if(device instanceof UsbYubiKeyDevice){
            UsbYubiKeyDevice usb=(UsbYubiKeyDevice)device;
            connection=usb.supportsConnection(FidoConnection.class)?usb.openConnection(FidoConnection.class):usb.openConnection(SmartCardConnection.class);
        }else if(device instanceof NfcYubiKeyDevice)connection=((NfcYubiKeyDevice)device).openConnection(SmartCardConnection.class);
        else throw new java.io.IOException("Unsupported key connection");
        if(!a.connectionOwner.attach(connection))return null;
        if(a.cancelled)return null;
        return connection instanceof FidoConnection?new Ctap2Session((FidoConnection)connection):new Ctap2Session((SmartCardConnection)connection);
    }
    private static byte[] assertKey(BasicWebAuthnClient client,AttestedCredentialData cred,byte[] salt,Attempt a,char[] operationPin)throws Exception {
        if(a.cancelled)throw new GeneralSecurityException("Cancelled");
        if(salt.length!=32)throw new GeneralSecurityException("Invalid wrapping salt");
        Map<String,Object> salts=new HashMap<>();salts.put(CredentialSaltSelector.id(cred.getCredentialId()),b64url(salt));
        return assertKeys(client,Collections.singletonList(cred),salts,a,operationPin);
    }
    private static byte[] assertKeys(BasicWebAuthnClient client,List<AttestedCredentialData> credentials,Map<String,Object> salts,Attempt a,char[] operationPin)throws Exception {
        if(a.cancelled||credentials.isEmpty()||credentials.size()>4)throw new GeneralSecurityException("Invalid key request");
        List<PublicKeyCredentialDescriptor> allowed=new ArrayList<>();for(AttestedCredentialData cred:credentials)allowed.add(new PublicKeyCredentialDescriptor("public-key",cred.getCredentialId(),null));
        byte[] challenge=random(32);byte[] data=clientData("webauthn.get",challenge);
        Map<String,Object> get=new HashMap<>();get.put("saltByCredential",salts);
        PublicKeyCredentialRequestOptions options=new PublicKeyCredentialRequestOptions(challenge,60000L,RP_ID,
            allowed,"required",
            Extensions.fromMap(Collections.singletonMap("hmacGetSecret",get)));
        PublicKeyCredential result;
        try{result=client.getAssertion(data,options,RP_ID,operationPin,a.command);}
        catch(com.yubico.yubikit.fido.client.MultipleAssertionsAvailable e){throw new GeneralSecurityException("Unexpected multiple key assertions");}
        AuthenticatorAssertionResponse r=(AuthenticatorAssertionResponse)result.getResponse();
        Map<String,Object> outputs=result.getClientExtensionResults().toMap(SerializationType.CBOR);
        @SuppressWarnings("unchecked") Map<String,Object> hmac=(Map<String,Object>)outputs.get("hmacGetSecret");
        byte[] secret=hmac==null?null:(byte[])hmac.get("output1");
        AttestedCredentialData cred=null;for(AttestedCredentialData candidate:credentials)if(MessageDigest.isEqual(candidate.getCredentialId(),result.getRawId())){cred=candidate;break;}
        if(cred==null){if(secret!=null)Arrays.fill(secret,(byte)0);throw new GeneralSecurityException("Unknown credential returned");}
        a.selectedCredential=cred.getCredentialId();
        try{AssertionVerifier.verify(publicKey(cred.getCosePublicKey()),cred.getCredentialId(),result.getRawId(),RP_ID,data,r.getClientDataJson(),r.getAuthenticatorData(),r.getSignature(),secret);return secret;}
        catch(Exception e){if(secret!=null)Arrays.fill(secret,(byte)0);throw e;}
    }
    private static PublicKey publicKey(Map<Integer,?> cose)throws Exception {
        if(!Integer.valueOf(2).equals(cose.get(1)) || !Integer.valueOf(-7).equals(cose.get(3)) || !Integer.valueOf(1).equals(cose.get(-1)))
            throw new GeneralSecurityException("Only ES256 Notes backup credentials are supported");
        AlgorithmParameters p=AlgorithmParameters.getInstance("EC");p.init(new ECGenParameterSpec("secp256r1"));
        return KeyFactory.getInstance("EC").generatePublic(new ECPublicKeySpec(new ECPoint(new BigInteger(1,(byte[])cose.get(-2)),new BigInteger(1,(byte[])cose.get(-3))),p.getParameterSpec(ECParameterSpec.class)));
    }
    private void fail(Attempt a,String message){if(current!=a)return;if(!foreground){a.close(false);a.pending=()->fail(a,message);return;}current=null;a.close(true);a.done.failed(message);}
    private static byte[] random(int n){byte[] b=new byte[n];new SecureRandom().nextBytes(b);return b;}
    private static byte[] clientData(String type,byte[] challenge)throws Exception{return new JSONObject().put("type",type).put("challenge",b64url(challenge)).put("origin","https://"+RP_ID).put("crossOrigin",false).toString().getBytes(StandardCharsets.UTF_8);}
    public static String b64(byte[] v){return Base64.encodeToString(v,Base64.NO_WRAP);}
    private static String b64url(byte[] v){return Base64.encodeToString(v,Base64.URL_SAFE|Base64.NO_WRAP|Base64.NO_PADDING);}
    private static byte[] decode(String v){return Base64.decode(v,Base64.DEFAULT);}
    private final class Attempt {
        final KeyReadiness readiness=new KeyReadiness();final PinBuffer pinBuffer=new PinBuffer();final SessionOwner<YubiKeyConnection> connectionOwner=new SessionOwner<>();YubiKeyDevice device;
        final JSONObject request;final boolean enroll;final Callback done;final AtomicBoolean claimed=new AtomicBoolean();
        byte[] selectedCredential;volatile String stage="DISCOVERY";volatile boolean nfc;boolean nfcStarted;TextView note;
        final CommandState command=new CommandState(){
            @Override public void onKeepAliveStatus(byte status){
                if(status==STATUS_UPNEEDED)ui.post(()->{if(current==Attempt.this&&!cancelled&&note!=null&&!nfc){dialog.setTitle("Touch your YubiKey now");note.setTextSize(22);note.setTypeface(null,android.graphics.Typeface.BOLD);note.setText(stage.equals("VERIFY-NEW")?"Touch the gold contact again now to verify the new key.":"The key is ready. Touch its flashing gold contact to continue.");}});
            }
        };volatile boolean cancelled;
        YubiKitManager manager;AlertDialog dialog;Runnable timeout,pending;
        boolean permissionPending;BroadcastReceiver permissionReceiver;
        void unregisterPermission(){if(permissionReceiver!=null){try{activity.unregisterReceiver(permissionReceiver);}catch(IllegalArgumentException ignored){}permissionReceiver=null;}}
        Attempt(JSONObject r,boolean e,Callback d){request=r;enroll=e;done=d;}
        void close(boolean keepNfc){cancelled=true;readiness.cancel();command.cancel();pinBuffer.clear();try{connectionOwner.close();}catch(Exception ignored){}device=null;permissionPending=false;pending=null;unregisterPermission();if(timeout!=null)ui.removeCallbacks(timeout);if(manager!=null){if(nfcStarted){if(keepNfc)nfcLease.retain(manager);else try{manager.stopNfcDiscovery(activity);}catch(RuntimeException ignored){}}try{manager.stopUsbDiscovery();}catch(RuntimeException ignored){}}if(dialog!=null)dialog.dismiss();}
    }
}

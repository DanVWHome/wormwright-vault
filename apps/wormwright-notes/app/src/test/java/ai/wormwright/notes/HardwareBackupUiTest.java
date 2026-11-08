package ai.wormwright.notes;
import ai.wormwright.notes.hardware.YubiKeyUnlock;
import android.app.AlertDialog;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.Config;
import org.robolectric.android.controller.ActivityController;
import org.robolectric.shadows.ShadowAlertDialog;
import java.nio.charset.StandardCharsets;
import java.util.*;
import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class) @Config(sdk=35)
public class HardwareBackupUiTest {
 public static class Host extends SecretNotesTest.TestActivity {
  byte[] delivered,restored;boolean protectedFile;
  @Override void runBackupTask(BackupTask task,BytesAction done){try{done.run(task.run());}catch(Exception e){throw new RuntimeException(e);}}
  @Override void deliverBackup(byte[] bytes,boolean nas,boolean protectedBackup){delivered=bytes;protectedFile=protectedBackup;}
  @Override void offerRestore(byte[] bytes,boolean encrypted,Runnable after){restored=bytes.clone();Arrays.fill(bytes,(byte)0);}
 }
 static class Store implements HardwareBackupUi.Store {
  JSONObject value;
  public JSONObject load()throws Exception{return value==null?null:new JSONObject(value.toString());}
  public void save(JSONObject v)throws Exception{value=new JSONObject(v.toString());}
 }
 static class Device implements HardwareBackupUi.Transport {
  JSONArray choices;YubiKeyUnlock.Callback callback;int enrolls,unlocks,stops;boolean permission;
  public void enroll(JSONArray keys,YubiKeyUnlock.Callback cb){choices=keys;callback=cb;enrolls++;}
  public void unlock(JSONArray keys,YubiKeyUnlock.Callback cb){choices=keys;callback=cb;unlocks++;}
  public boolean pauseForUsbPermission(){return permission;}
  public void resume(){}public void stop(){stops++;}public void dispose(){stop();}
 }
 ActivityController<Host> controller;Host host;Store store;Device device;HardwareBackupUi ui;KeyBackupTest fixture=new KeyBackupTest();
 @Before public void setup()throws Exception{
  RuntimeEnvironment.getApplication().deleteDatabase("notes.db");controller=Robolectric.buildActivity(Host.class).setup();host=controller.get();host.credentialEpoch=host.accessEpoch;
  store=new Store();device=new Device();ui=new HardwareBackupUi(host,store,device);host.backupHardware=ui;
 }
 @After public void cleanup(){controller.pause().stop().destroy();}
 JSONObject state(int count)throws Exception{JSONObject state=BackupKeyRegistry.empty();for(int i=1;i<=count;i++)state=BackupKeyRegistry.add(state,fixture.record(i));return state;}
 JSONObject response(int n)throws Exception{return new JSONObject().put("response",KeyBackupEnvelope.b64(fixture.response(n))).put("request",fixture.record(n).toString());}
 void note(){host.editor(-1);host.title.setText("ordinary");host.body.setText("milk");assertTrue(host.save());host.home();}
 @Test public void registrationPassesExclusionsAndKeepsOnlyPublicData()throws Exception{
  store.value=state(3);ui.enroll("Spare four",store.load());assertEquals(3,device.choices.length());
  JSONObject r=fixture.record(4);JSONObject result=new JSONObject().put("credential",r.getString("credential")).put("salt",r.getString("salt")).put("response",KeyBackupEnvelope.b64(fixture.response(4)));
  device.callback.complete(result);assertEquals(4,store.value.getJSONArray("keys").length());assertFalse(store.value.toString().contains("response"));assertFalse(result.has("response"));
  ui.register();assertEquals(1,device.enrolls);
 }
 @Test public void cancelledOrBackgroundedEnrollmentNeverWritesRegistry()throws Exception{
  store.value=state(1);ui.enroll("Spare",store.load());YubiKeyUnlock.Callback pending=device.callback;ui.stop();
  JSONObject r=fixture.record(2);pending.complete(new JSONObject().put("credential",r.getString("credential")).put("salt",r.getString("salt")).put("response",KeyBackupEnvelope.b64(fixture.response(2))));assertEquals(1,store.value.getJSONArray("keys").length());
 }
 @Test public void registeredFourAllDecryptOneCreatedFile()throws Exception{
  note();store.value=state(4);ui.createBackup(false);assertEquals(4,device.choices.length());device.callback.complete(response(2));
  assertNotNull(host.delivered);assertTrue(host.protectedFile);for(int i=1;i<=4;i++)assertTrue(new String(KeyBackupEnvelope.decrypt(host.delivered,fixture.record(i).getString("id"),fixture.response(i)),StandardCharsets.UTF_8).contains("milk"));
 }
 @Test public void wrongKeyOrHardwareFailureNeverFallsBackToPlaintext()throws Exception{
  note();store.value=state(2);ui.createBackup(false);JSONObject wrong=response(1);wrong.put("response",KeyBackupEnvelope.b64(fixture.response(3)));device.callback.complete(wrong);assertNull(host.delivered);
  ui.createBackup(false);device.callback.failed("Wrong PIN");assertNull(host.delivered);assertEquals(2,device.unlocks);assertEquals(2,store.value.getJSONArray("keys").length());
 }
 @Test public void restoreUsesBackupRecipientsWithoutPhoneRegistry()throws Exception{
  byte[] plain="{\"format\":\"wormwright-notes-v1\",\"notes\":[]}".getBytes(StandardCharsets.UTF_8);
  byte[] file=KeyBackupEnvelope.encrypt(plain,state(4).getJSONArray("keys"));ui.restore(file);assertEquals(4,device.choices.length());device.callback.complete(response(3));assertArrayEquals(plain,host.restored);assertNull(store.value);
 }
 @Test public void onlyUsbPermissionOverlayPreservesOperation()throws Exception{
  store.value=state(1);note();ui.createBackup(false);long epoch=host.accessEpoch;device.permission=true;controller.pause();assertEquals(epoch,host.accessEpoch);assertEquals(0,device.stops);
  controller.stop();assertTrue(host.accessEpoch>epoch);assertTrue(device.stops>0);YubiKeyUnlock.Callback pending=device.callback;controller.start().resume();pending.complete(response(1));assertNull(host.delivered);
 }
 @Test public void managerAlwaysRequiresFreshPhoneAuthentication()throws Exception{
  ui.manage();assertNotNull(host.requested);host.answerCredential(false);assertNull(store.value);
 }
}

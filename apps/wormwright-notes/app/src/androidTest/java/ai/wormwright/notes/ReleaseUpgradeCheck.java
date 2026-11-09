package ai.wormwright.notes;
import android.content.*;
import android.database.Cursor;
import java.util.Arrays;
import org.json.*;

/** Disposable-emulator fixtures only: verifies an actual APK update retains data and Keystore keys. */
final class ReleaseUpgradeCheck {
 static void run(SecretUiInstrumentation driver,boolean seed)throws Exception{
  driver.activity=(MainActivity)driver.startActivitySync(new Intent(driver.getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
  MainActivity app=driver.activity;
  android.app.KeyguardManager screen=(android.app.KeyguardManager)app.getSystemService(android.content.Context.KEYGUARD_SERVICE);
  driver.key(224);driver.waitFor(()->screen.isKeyguardLocked()||driver.main(()->app.resumed),30000);
  if(screen.isKeyguardLocked()){driver.key(82);android.os.SystemClock.sleep(600);driver.shell("input text 246813");driver.key(66);driver.waitFor(()->!screen.isKeyguardLocked(),15000);}
  driver.waitFor(()->driver.main(()->app.resumed),30000);
  driver.main(()->{
   if(seed){
    app.editor(-1);app.title.setText("Upgrade fixture");app.body.setText("[x] A long sample checklist item that must survive the release naming update");app.checklistMode=true;app.save();long publicId=app.editing;
    app.db.execSQL("UPDATE notes SET pinned=1,deleted=1 WHERE id=?",new Object[]{publicId});
    app.editor(-1);app.title.setText("Upgrade secret");app.body.setText("Only invented upgrade fixture text");app.save();long secretId=app.editing;app.makeSecret(secretId);app.home();
    new NasSettings(app).save(new JSONObject().put("host","192.0.2.25").put("share","fixture").put("folder","fixture-folder").put("user","fixture-user").put("domain","").put("password","invented-fixture-password"));
    byte[] secret=new byte[32],credential=new byte[64],salt=new byte[32];Arrays.fill(secret,(byte)7);Arrays.fill(credential,(byte)4);Arrays.fill(salt,(byte)6);
    JSONObject key=KeyBackupEnvelope.registration("Upgrade fixture key",KeyBackupEnvelope.b64(credential),KeyBackupEnvelope.b64(salt),secret);
    new BackupKeyStore(app).save(BackupKeyRegistry.add(BackupKeyRegistry.empty(),key));Arrays.fill(secret,(byte)0);
    app.getSharedPreferences("upgrade-fixture",0).edit().putLong("public",publicId).putLong("secret",secretId).commit();
   }else{
    android.content.pm.PackageInfo info=app.getPackageManager().getPackageInfo(app.getPackageName(),0);SecretUiInstrumentation.check("Release 8".equals(info.versionName)&&info.versionCode==9,"new Android release identity");
    android.content.SharedPreferences saved=app.getSharedPreferences("upgrade-fixture",0);long publicId=saved.getLong("public",-1),secretId=saved.getLong("secret",-1);
    try(Cursor row=app.db.rawQuery("SELECT title,body,pinned,deleted,secret FROM notes WHERE id=?",new String[]{""+publicId})){SecretUiInstrumentation.check(row.moveToFirst()&&"Upgrade fixture".equals(row.getString(0))&&row.getString(1).startsWith("[x] A long sample")&&row.getInt(2)==1&&row.getInt(3)==1&&row.getInt(4)==0,"public checklist, pin and Trash preserved");}
    try(Cursor row=app.db.rawQuery("SELECT title,body,secret FROM notes WHERE id=?",new String[]{""+secretId})){SecretUiInstrumentation.check(row.moveToFirst()&&row.getString(0).isEmpty()&&row.getInt(2)==1,"secret stays encrypted");JSONObject plain=new JSONObject(app.secretCipher.decrypt(secretId,row.getString(1)));SecretUiInstrumentation.check("Upgrade secret".equals(plain.getString("title"))&&"Only invented upgrade fixture text".equals(plain.getString("body")),"phone encryption key retained");}
    JSONObject nas=new NasSettings(app).load();SecretUiInstrumentation.check(nas!=null&&"fixture-user".equals(nas.getString("user"))&&"invented-fixture-password".equals(nas.getString("password")),"encrypted NAS settings retained");
    JSONObject keys=BackupKeyRegistry.valid(new BackupKeyStore(app).load());SecretUiInstrumentation.check(keys.getJSONArray("keys").length()==1&&"Upgrade fixture key".equals(keys.getJSONArray("keys").getJSONObject(0).getString("label")),"encrypted key registrations retained");
   }
   return null;
  });
 }
}

package ai.wormwright.notes;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import org.json.*;
import java.util.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class) @Config(sdk=35)
public class KeyBackupTest {
 interface Checked{void run()throws Exception;}
 void rejects(Checked action)throws Exception{try{action.run();fail("Invalid key or backup accepted");}catch(GeneralSecurityException|IllegalArgumentException expected){}}
 byte[] response(int n)throws Exception{return MessageDigest.getInstance("SHA-256").digest(("synthetic-hardware-secret-"+n).getBytes(StandardCharsets.UTF_8));}
 JSONObject record(int n)throws Exception{byte[] full=new byte[64];Arrays.fill(full,(byte)n);return KeyBackupEnvelope.registration("Key "+n,KeyBackupEnvelope.b64(full),KeyBackupEnvelope.b64(response(n+100)),response(n));}
 byte[] text="{private title and checklist: milk, pears}".getBytes(StandardCharsets.UTF_8);
 @Test public void eachOfFourIndependentKeysRestoresSameFileOnNewPhone()throws Exception{
  JSONArray keys=new JSONArray();for(int i=1;i<=4;i++)keys.put(record(i));byte[] file=KeyBackupEnvelope.encrypt(text,keys);
  assertTrue(KeyBackupEnvelope.isEncrypted(file));assertFalse(new String(file,StandardCharsets.UTF_8).contains("milk"));
  for(int i=1;i<=4;i++)assertArrayEquals(text,KeyBackupEnvelope.decrypt(file,record(i).getString("id"),response(i)));
  assertNotEquals(KeyBackupEnvelope.b64(file),KeyBackupEnvelope.b64(KeyBackupEnvelope.encrypt(text,keys)));
  assertEquals(4,KeyBackupEnvelope.recipients(file).length());
  rejects(()->KeyBackupEnvelope.decrypt(file,record(1).getString("id"),response(5)));
  rejects(()->KeyBackupEnvelope.decrypt(file,record(5).getString("id"),response(5)));
 }
 @Test public void fifthDuplicateAndInvalidRecipientsRejected()throws Exception{
  JSONArray keys=new JSONArray();for(int i=1;i<=5;i++)keys.put(record(i));rejects(()->KeyBackupEnvelope.encrypt(text,keys));
  rejects(()->KeyBackupEnvelope.encrypt(text,new JSONArray().put(record(1)).put(record(1))));
  rejects(()->KeyBackupEnvelope.encrypt(text,new JSONArray()));
  JSONObject bad=record(1);bad.put("public",KeyBackupEnvelope.b64(new byte[32]));rejects(()->KeyBackupEnvelope.encrypt(text,new JSONArray().put(bad)));
  JSONObject wrong=record(1).put("id",record(2).getString("id"));rejects(()->KeyBackupEnvelope.record(wrong));
 }
 @Test public void changingAnyHeaderOrPayloadFailsAuthentication()throws Exception{
  JSONArray keys=new JSONArray().put(record(1)).put(record(2));byte[] file=KeyBackupEnvelope.encrypt(text,keys);
  byte[] changed=file.clone();changed[changed.length-1]^=1;rejects(()->KeyBackupEnvelope.decrypt(changed,record(1).getString("id"),response(1)));
  JSONObject header=KeyBackupEnvelope.header(file);header.getJSONArray("keys").getJSONObject(1).put("label","Tampered label");
  int original=KeyBackupEnvelope.MAGIC.length+4+ByteBuffer.wrap(file,KeyBackupEnvelope.MAGIC.length,4).getInt();
  byte[] h=header.toString().getBytes(StandardCharsets.UTF_8);byte[] modified=ByteBuffer.allocate(KeyBackupEnvelope.MAGIC.length+4+h.length+file.length-original).put(KeyBackupEnvelope.MAGIC).putInt(h.length).put(h).put(file,original,file.length-original).array();
  rejects(()->KeyBackupEnvelope.decrypt(modified,record(1).getString("id"),response(1)));
  rejects(()->KeyBackupEnvelope.decrypt(Arrays.copyOf(file,file.length-1),record(1).getString("id"),response(1)));
  byte[] oversized=file.clone();ByteBuffer.wrap(oversized,KeyBackupEnvelope.MAGIC.length,4).putInt(Integer.MAX_VALUE);rejects(()->KeyBackupEnvelope.recipients(oversized));
 }
 @Test public void newAndRemovedKeysAffectNewBackupsOnly()throws Exception{
  JSONObject state=BackupKeyRegistry.add(BackupKeyRegistry.empty(),record(1));byte[] old=KeyBackupEnvelope.encrypt(text,state.getJSONArray("keys"));
  state=BackupKeyRegistry.add(state,record(2));byte[] both=KeyBackupEnvelope.encrypt(text,state.getJSONArray("keys"));
  rejects(()->KeyBackupEnvelope.decrypt(old,record(2).getString("id"),response(2)));
  assertArrayEquals(text,KeyBackupEnvelope.decrypt(both,record(2).getString("id"),response(2)));
  state=BackupKeyRegistry.remove(state,record(1).getString("id"));byte[] future=KeyBackupEnvelope.encrypt(text,state.getJSONArray("keys"));
  rejects(()->KeyBackupEnvelope.decrypt(future,record(1).getString("id"),response(1)));
  assertArrayEquals(text,KeyBackupEnvelope.decrypt(old,record(1).getString("id"),response(1)));
 }
 @Test public void registryRetainsPublicDataOnlyAndMergesAtMostFour()throws Exception{
  JSONObject state=BackupKeyRegistry.empty();for(int i=1;i<=4;i++)state=BackupKeyRegistry.add(state,record(i));final JSONObject full=state;
  rejects(()->BackupKeyRegistry.add(full,record(5)));
  assertFalse(state.toString().contains("response"));assertFalse(state.toString().contains("private"));
  for(int i=1;i<=4;i++)assertFalse(state.toString().contains(KeyBackupEnvelope.b64(response(i))));
  assertEquals(4,BackupKeyRegistry.merge(state,new JSONArray().put(record(1))).getJSONArray("keys").length());
  assertEquals("Spare",BackupKeyRegistry.rename(state,record(2).getString("id"),"Spare").getJSONArray("keys").getJSONObject(1).getString("label"));
  rejects(()->BackupKeyRegistry.merge(full,new JSONArray().put(record(1).put("public",record(2).getString("public")))));
 }
 @Test public void hkdfMatchesRfc5869FirstBlock()throws Exception{
  byte[] ikm=new byte[22];Arrays.fill(ikm,(byte)0x0b);
  byte[] salt=org.bouncycastle.util.encoders.Hex.decode("000102030405060708090a0b0c");byte[] info=org.bouncycastle.util.encoders.Hex.decode("f0f1f2f3f4f5f6f7f8f9");
  assertArrayEquals(org.bouncycastle.util.encoders.Hex.decode("3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf"),KeyBackupEnvelope.hkdf(ikm,salt,info));
 }
 @Test public void passwordBackupFormatStillRestores()throws Exception{
  char[] password="Existing password option".toCharArray();byte[] file=BackupEnvelope.encrypt(text,password);
  assertTrue(BackupEnvelope.isEncrypted(file));assertFalse(KeyBackupEnvelope.isEncrypted(file));assertArrayEquals(text,BackupEnvelope.decrypt(file,password));
 }
}

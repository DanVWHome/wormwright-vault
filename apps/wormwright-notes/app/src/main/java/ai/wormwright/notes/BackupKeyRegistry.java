package ai.wormwright.notes;
import org.json.*;
import java.security.GeneralSecurityException;
/** Versioned, public-only registry; storage adapter authenticates it on the phone. */
public final class BackupKeyRegistry {
 public static JSONObject empty()throws Exception{return new JSONObject().put("revision",0).put("keys",new JSONArray());}
 public static JSONObject valid(JSONObject data)throws Exception{
  if(data==null)return empty();int rev=data.getInt("revision");if(rev<0)throw new GeneralSecurityException("Invalid revision");return new JSONObject().put("revision",rev).put("keys",KeyBackupEnvelope.records(data.getJSONArray("keys")));
 }
 public static JSONObject add(JSONObject state,JSONObject record)throws Exception{
  JSONObject result=valid(state);JSONArray keys=result.getJSONArray("keys");keys.put(KeyBackupEnvelope.record(record));KeyBackupEnvelope.records(keys);return result.put("revision",result.getInt("revision")+1);
 }
 public static JSONObject remove(JSONObject state,String id)throws Exception{
  JSONObject result=valid(state);JSONArray old=result.getJSONArray("keys"),keys=new JSONArray();for(int i=0;i<old.length();i++)if(!old.getJSONObject(i).getString("id").equals(id))keys.put(old.getJSONObject(i));return result.put("keys",keys).put("revision",result.getInt("revision")+1);
 }
 public static JSONObject rename(JSONObject state,String id,String label)throws Exception{
  JSONObject result=valid(state);JSONArray keys=result.getJSONArray("keys");for(int i=0;i<keys.length();i++)if(keys.getJSONObject(i).getString("id").equals(id))keys.getJSONObject(i).put("label",label);
  KeyBackupEnvelope.records(keys);return result.put("revision",result.getInt("revision")+1);
 }
 public static JSONObject merge(JSONObject state,JSONArray incoming)throws Exception{
  JSONObject result=valid(state);for(int i=0;i<incoming.length();i++){
   JSONObject key=KeyBackupEnvelope.record(incoming.getJSONObject(i));boolean exists=false;JSONArray keys=result.getJSONArray("keys");
   for(int j=0;j<keys.length();j++)if(keys.getJSONObject(j).getString("id").equals(key.getString("id"))){exists=true;if(!keys.getJSONObject(j).getString("public").equals(key.getString("public"))||!keys.getJSONObject(j).getString("salt").equals(key.getString("salt")))throw new GeneralSecurityException("Conflicting registration");}
   if(!exists)result=add(result,key);
  }return result;
 }
}

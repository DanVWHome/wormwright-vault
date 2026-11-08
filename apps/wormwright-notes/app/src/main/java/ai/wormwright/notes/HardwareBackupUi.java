package ai.wormwright.notes;

import android.app.AlertDialog;
import android.widget.EditText;
import org.json.*;
import java.util.*;
import ai.wormwright.notes.hardware.YubiKeyUnlock;

/** Foreground-only enrollment and portable backup UI. No hardware secret is persisted. */
public final class HardwareBackupUi {
    interface Store{JSONObject load()throws Exception;void save(JSONObject state)throws Exception;}
    interface Transport{
        void enroll(JSONArray existing,YubiKeyUnlock.Callback callback);
        void unlock(JSONArray choices,YubiKeyUnlock.Callback callback);
        boolean pauseForUsbPermission();void resume();void stop();void dispose();
    }
    final MainActivity host;final Store store;final Transport transport;long generation=0;
    public HardwareBackupUi(MainActivity host){this(host,new Store(){
        final BackupKeyStore disk=new BackupKeyStore(host);
        public JSONObject load()throws Exception{return disk.load();}public void save(JSONObject state)throws Exception{disk.save(state);}
    },new Transport(){
        final YubiKeyUnlock hardware=new YubiKeyUnlock(host);
        public void enroll(JSONArray choices,YubiKeyUnlock.Callback cb){hardware.enroll(choices,cb);}
        public void unlock(JSONArray choices,YubiKeyUnlock.Callback cb){hardware.unlockChoices(choices,cb);}
        public boolean pauseForUsbPermission(){return hardware.pauseForUsbPermission();}
        public void resume(){hardware.resume();}public void stop(){hardware.stop();}public void dispose(){hardware.dispose();}
    });}
    HardwareBackupUi(MainActivity host,Store store,Transport transport){this.host=host;this.store=store;this.transport=transport;}
    boolean pauseForUsbPermission(){return transport.pauseForUsbPermission();}
    void resume(){transport.resume();}
    void stop(){generation++;transport.stop();}
    void dispose(){generation++;transport.dispose();}
    JSONObject state()throws Exception{return BackupKeyRegistry.valid(store.load());}
    void phone(Runnable action){if(host.resumed&&host.credentialEpoch==host.accessEpoch)action.run();else host.requestCredential(action);}
    public void manage(){host.requestCredential(this::showManager);}
    void showManager(){
        try{JSONObject data=state();JSONArray keys=data.getJSONArray("keys");String[] labels=new String[keys.length()+1];
            for(int i=0;i<keys.length();i++)labels[i]=keys.getJSONObject(i).getString("label");labels[keys.length()]=keys.length()<4?"+ Register YubiKey":"Four keys registered";
            new AlertDialog.Builder(host).setTitle("Backup YubiKeys · "+keys.length()+" of 4").setItems(labels,(d,n)->{
                if(n==keys.length()){if(keys.length()<4)register();else host.toast("Four keys are already registered");}
                else try{keyOptions(keys.getJSONObject(n));}catch(Exception e){host.toast("Could not read key registration");}
            }).setNegativeButton("Close",null).show();
        }catch(Exception e){host.toast("Could not read backup key registrations. Existing backups are unchanged.");}
    }
    void labelDialog(String title,String previous,java.util.function.Consumer<String> success){
        EditText input=new EditText(host);input.setSingleLine();input.setHint("Key name, for example Spare key");input.setText(previous);
        AlertDialog dialog=new AlertDialog.Builder(host).setTitle(title).setView(input).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();
        dialog.setOnShowListener(d->dialog.getButton(-1).setOnClickListener(v->{String label=input.getText().toString().trim();if(label.isEmpty()||label.length()>40){input.setError("Use 1–40 characters");return;}dialog.dismiss();success.accept(label);}));dialog.show();
    }
    void register(){phone(()->{
        try{JSONObject before=state();JSONArray keys=before.getJSONArray("keys");if(keys.length()>=4){host.toast("Four keys are already registered");return;}
            labelDialog("Name this YubiKey","",label->{
                new AlertDialog.Builder(host).setTitle("Register a backup YubiKey?")
                    .setMessage("Use a different physical key for each slot. Enter its FIDO2 PIN, connect USB-C or hold it at the NFC reader, and follow the touch prompts. Notes creates a separate credential; Vault enrollments remain unchanged. Make a new backup after adding a key so it can restore that backup.")
                    .setNegativeButton("Cancel",null).setPositiveButton("Register",(d,w)->phone(()->enroll(label,before))).show();
            });
        }catch(Exception e){host.toast("Could not prepare key registration");}
    });}
    void enroll(String label,JSONObject before){
        try{JSONArray choices=before.getJSONArray("keys");int revision=before.getInt("revision");long token=++generation;
            transport.enroll(choices,new YubiKeyUnlock.Callback(){
                public void complete(JSONObject result){byte[] response=null;
                    try{response=KeyBackupEnvelope.bytes(result.getString("response"),32);result.remove("response");
                        if(token!=generation||!host.resumed)return;
                        JSONObject current=state();if(current.getInt("revision")!=revision)throw new IllegalStateException();
                        JSONObject key=KeyBackupEnvelope.registration(label,result.getString("credential"),result.getString("salt"),response);
                        store.save(BackupKeyRegistry.add(current,key));host.toast("YubiKey registered. Make a new backup to include it.");showManager();
                    }catch(Exception e){host.toast("No key was added. The key list may have changed; try again.");}finally{if(response!=null)Arrays.fill(response,(byte)0);result.remove("response");}
                }
                public void failed(String message){if(token==generation&&host.resumed)host.toast(message);}
            });
        }catch(Exception e){host.toast("Could not start YubiKey registration");}
    }
    void keyOptions(JSONObject key)throws Exception{
        String id=key.getString("id"),label=key.getString("label");
        new AlertDialog.Builder(host).setTitle(label).setItems(new String[]{"Rename","Remove from future backups"},(d,n)->{
            if(n==0)labelDialog("Rename YubiKey",label,name->phone(()->{try{store.save(BackupKeyRegistry.rename(state(),id,name));showManager();}catch(Exception e){host.toast("Could not rename key");}}));
            else new AlertDialog.Builder(host).setTitle("Remove "+label+"?").setMessage("New backups will no longer include this key. Older backups still accept their original keys. This does not erase or reset the physical YubiKey.")
                .setNegativeButton("Cancel",null).setPositiveButton("Remove",(x,w)->phone(()->{try{store.save(BackupKeyRegistry.remove(state(),id));showManager();}catch(Exception e){host.toast("Could not remove key registration");}})).show();
        }).show();
    }
    JSONObject selected(JSONArray choices,JSONObject result)throws Exception{
        JSONObject request=new JSONObject(result.getString("request"));String id=request.getString("id");
        for(int i=0;i<choices.length();i++){JSONObject key=choices.getJSONObject(i);if(key.getString("id").equals(id)&&key.getString("credential").equals(request.getString("credential")))return key;}
        throw new SecurityException("Unknown key response");
    }
    public void createBackup(boolean nas){
        if(host.hasSecrets()&&(!host.resumed||host.credentialEpoch!=host.accessEpoch)){host.requestCredential(()->createBackup(nas));return;}
        try{JSONArray keys=state().getJSONArray("keys");if(keys.length()==0){new AlertDialog.Builder(host).setTitle("Register a YubiKey first").setMessage("Register up to four keys for encrypted backups. Password backups remain available.").setNegativeButton("Cancel",null).setPositiveButton("Register keys",(d,w)->manage()).show();return;}
            long token=++generation;
            transport.unlock(keys,new YubiKeyUnlock.Callback(){
                public void complete(JSONObject result){byte[] response=null;
                    try{response=KeyBackupEnvelope.bytes(result.getString("response"),32);result.remove("response");if(token!=generation||!host.resumed)return;
                        KeyBackupEnvelope.verifyResponse(selected(keys,result),response);
                        byte[] plain=host.backupBytes(host.hasSecrets());
                        host.runBackupTask(()->{try{return KeyBackupEnvelope.encrypt(plain,keys);}finally{Arrays.fill(plain,(byte)0);}},bytes->{if(token==generation&&host.resumed)host.deliverBackup(bytes,nas,true);else Arrays.fill(bytes,(byte)0);});
                    }catch(Exception e){host.toast("Could not create a YubiKey backup. No unencrypted backup was written.");}finally{if(response!=null)Arrays.fill(response,(byte)0);result.remove("response");}
                }
                public void failed(String message){if(token==generation&&host.resumed)host.toast(message);}
            });
        }catch(Exception e){host.toast("Could not read backup keys");}
    }
    public void restore(byte[] file){
        try{JSONArray choices=KeyBackupEnvelope.recipients(file);long token=++generation;
            transport.unlock(choices,new YubiKeyUnlock.Callback(){
                public void complete(JSONObject result){byte[] response=null;
                    try{response=KeyBackupEnvelope.bytes(result.getString("response"),32);result.remove("response");if(token!=generation||!host.resumed)return;
                        JSONObject key=selected(choices,result);final byte[] keyResponse=response;response=null;
                        host.runBackupTask(()->{try{return KeyBackupEnvelope.decrypt(file,key.getString("id"),keyResponse);}finally{Arrays.fill(keyResponse,(byte)0);}},plain->{if(token==generation&&host.resumed)host.offerRestore(plain,true,()->remember(choices));else Arrays.fill(plain,(byte)0);});
                    }catch(Exception e){host.toast("Could not unlock this YubiKey backup");}finally{if(response!=null)Arrays.fill(response,(byte)0);result.remove("response");}
                }
                public void failed(String message){if(token==generation&&host.resumed)host.toast(message);}
            });
        }catch(Exception e){host.toast("Invalid or unsupported YubiKey backup");}
    }
    void remember(JSONArray choices){
        new AlertDialog.Builder(host).setTitle("Remember these backup keys?")
            .setMessage("Keep the public registrations from this backup so you can use these keys for new backups on this phone. No YubiKey PIN or private encryption key is stored. Up to four keys total.")
            .setNegativeButton("Not now",null).setPositiveButton("Remember",(d,w)->host.requestCredential(()->{try{store.save(BackupKeyRegistry.merge(state(),choices));host.toast("Backup keys remembered");}catch(Exception e){host.toast("Key list was not changed. There may be more than four keys or a conflicting registration.");}})).show();
    }
}

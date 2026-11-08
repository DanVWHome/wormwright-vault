package ai.wormwright.notes;

import org.json.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.*;
import javax.crypto.*;
import javax.crypto.spec.*;
import org.bouncycastle.math.ec.rfc7748.X25519;

/** Multi-recipient envelope: the phone retains public registrations only. */
public final class KeyBackupEnvelope {
    static final byte[] MAGIC="WWNOTES3\n".getBytes(StandardCharsets.US_ASCII);
    static final String FORMAT="wormwright-notes-yubikey-v1";
    static final int MAX_HEADER=32768,MAX_FILE=20*1024*1024;
    static byte[] random(int n){byte[] b=new byte[n];new SecureRandom().nextBytes(b);return b;}
    static String b64(byte[] b){return Base64.getEncoder().encodeToString(b);}
    static byte[] bytes(String value,int expected)throws Exception{
        if(value.length()>4096)throw new GeneralSecurityException("Field too large");
        byte[] result=Base64.getDecoder().decode(value);
        if(expected>0&&result.length!=expected)throw new GeneralSecurityException("Invalid field length");return result;
    }
    static byte[] hkdf(byte[] ikm,byte[] salt,byte[] info)throws Exception{
        Mac mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec(salt,"HmacSHA256"));byte[] prk=mac.doFinal(ikm);
        try{mac.init(new SecretKeySpec(prk,"HmacSHA256"));mac.update(info);mac.update((byte)1);return mac.doFinal();}finally{Arrays.fill(prk,(byte)0);}
    }
    static byte[] privateKey(byte[] response)throws Exception{
        if(response.length!=32)throw new GeneralSecurityException("Invalid key response");
        return hkdf(response,"wormwright-notes-backup-private-v1".getBytes(StandardCharsets.UTF_8),"X25519 recovery key".getBytes(StandardCharsets.UTF_8));
    }
    public static byte[] publicKey(byte[] response)throws Exception{
        byte[] privateKey=privateKey(response),publicKey=new byte[32];
        try{X25519.scalarMultBase(privateKey,0,publicKey,0);return publicKey;}finally{Arrays.fill(privateKey,(byte)0);}
    }
    static String id(String credential)throws Exception{
        byte[] full=bytes(credential,0);if(full.length<20||full.length>2048)throw new GeneralSecurityException("Invalid credential");
        StringBuilder out=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(full))out.append(String.format(Locale.ROOT,"%02x",b&255));return out.toString();
    }
    public static JSONObject registration(String label,String credential,String salt,byte[] response)throws Exception{
        return record(new JSONObject().put("id",id(credential)).put("label",label).put("credential",credential).put("salt",salt).put("public",b64(publicKey(response))));
    }
    public static JSONObject record(JSONObject source)throws Exception{
        String credential=source.getString("credential"),id=id(credential),label=source.getString("label").trim();
        if(!id.equals(source.getString("id"))||label.isEmpty()||label.length()>40)throw new GeneralSecurityException("Invalid registration");
        byte[] pub=bytes(source.getString("public"),32);bytes(source.getString("salt"),32);
        int nonzero=0;for(byte b:pub)nonzero|=b;if(nonzero==0)throw new GeneralSecurityException("Invalid public key");
        return new JSONObject().put("id",id).put("label",label).put("credential",credential).put("salt",source.getString("salt")).put("public",source.getString("public"));
    }
    public static JSONArray records(JSONArray input)throws Exception{
        if(input.length()>4)throw new GeneralSecurityException("Maximum four keys");
        JSONArray result=new JSONArray();Set<String> ids=new HashSet<>();
        for(int i=0;i<input.length();i++){JSONObject key=record(input.getJSONObject(i));if(!ids.add(key.getString("id")))throw new GeneralSecurityException("Duplicate key");result.put(key);}return result;
    }
    public static void verifyResponse(JSONObject record,byte[] response)throws Exception{
        if(!MessageDigest.isEqual(publicKey(response),bytes(record.getString("public"),32)))throw new GeneralSecurityException("Key response mismatch");
    }
    public static boolean isEncrypted(byte[] file){return file.length>=MAGIC.length&&Arrays.equals(MAGIC,Arrays.copyOf(file,MAGIC.length));}
    static byte[] context(String backupId,JSONObject record,String ephemeral)throws Exception{
        return ("WWNOTES3-WRAP\n"+backupId+"\n"+record.getString("id")+"\n"+record.getString("credential")+"\n"+record.getString("salt")+"\n"+record.getString("public")+"\n"+ephemeral).getBytes(StandardCharsets.UTF_8);
    }
    static byte[] crypt(int mode,byte[] key,byte[] iv,byte[] aad,byte[] input)throws Exception{
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(mode,new SecretKeySpec(key,"AES"),new GCMParameterSpec(128,iv));cipher.updateAAD(aad);return cipher.doFinal(input);
    }
    public static byte[] encrypt(byte[] plain,JSONArray registrations)throws Exception{
        JSONArray keys=records(registrations);if(keys.length()==0||plain.length>MAX_FILE)throw new GeneralSecurityException("Missing keys or oversized backup");
        byte[] backupId=random(32),dek=random(32);JSONArray recipients=new JSONArray();
        try{
            for(int i=0;i<keys.length();i++){
                JSONObject r=keys.getJSONObject(i);byte[] ephemeral=random(32),publicEphemeral=new byte[32],shared=new byte[32],kek=null;
                try{X25519.scalarMultBase(ephemeral,0,publicEphemeral,0);
                    if(!X25519.calculateAgreement(ephemeral,0,bytes(r.getString("public"),32),0,shared,0))throw new GeneralSecurityException("Invalid recipient key");
                    String encoded=b64(publicEphemeral);byte[] aad=context(b64(backupId),r,encoded);kek=hkdf(shared,backupId,aad);byte[] iv=random(12);
                    recipients.put(new JSONObject(r.toString()).put("ephemeral",encoded).put("iv",b64(iv)).put("wrapped",b64(crypt(Cipher.ENCRYPT_MODE,kek,iv,aad,dek))));
                }finally{Arrays.fill(ephemeral,(byte)0);Arrays.fill(shared,(byte)0);if(kek!=null)Arrays.fill(kek,(byte)0);}
            }
            byte[] header=new JSONObject().put("format",FORMAT).put("backupId",b64(backupId)).put("keys",recipients).toString().getBytes(StandardCharsets.UTF_8);
            if(header.length>MAX_HEADER)throw new GeneralSecurityException("Header too large");
            byte[] aad=ByteBuffer.allocate(MAGIC.length+4+header.length).put(MAGIC).putInt(header.length).put(header).array(),iv=random(12),cipher=crypt(Cipher.ENCRYPT_MODE,dek,iv,aad,plain);
            byte[] result=ByteBuffer.allocate(aad.length+iv.length+cipher.length).put(aad).put(iv).put(cipher).array();
            if(result.length>MAX_FILE)throw new GeneralSecurityException("Backup too large");return result;
        }finally{Arrays.fill(dek,(byte)0);}
    }
    static JSONObject header(byte[] file)throws Exception{
        if(!isEncrypted(file)||file.length<MAGIC.length+4+12+16||file.length>MAX_FILE)throw new GeneralSecurityException("Invalid backup");
        int size=ByteBuffer.wrap(file,MAGIC.length,4).getInt();
        if(size<2||size>MAX_HEADER||size>file.length-MAGIC.length-4-28)throw new GeneralSecurityException("Invalid backup header");
        JSONObject header=new JSONObject(new String(file,MAGIC.length+4,size,StandardCharsets.UTF_8));
        if(!FORMAT.equals(header.getString("format")))throw new GeneralSecurityException("Unsupported format");bytes(header.getString("backupId"),32);
        JSONArray keys=header.getJSONArray("keys");if(keys.length()==0)throw new GeneralSecurityException("No recipients");records(keys);
        for(int i=0;i<keys.length();i++){JSONObject r=keys.getJSONObject(i);bytes(r.getString("ephemeral"),32);bytes(r.getString("iv"),12);bytes(r.getString("wrapped"),48);}
        return header;
    }
    public static JSONArray recipients(byte[] file)throws Exception{return records(header(file).getJSONArray("keys"));}
    public static byte[] decrypt(byte[] file,String id,byte[] response)throws Exception{
        JSONObject header=header(file),recipient=null;JSONArray keys=header.getJSONArray("keys");
        for(int i=0;i<keys.length();i++)if(keys.getJSONObject(i).getString("id").equals(id))recipient=keys.getJSONObject(i);
        if(recipient==null)throw new GeneralSecurityException("Key not in this backup");verifyResponse(recipient,response);
        byte[] privateKey=privateKey(response),shared=new byte[32],kek=null,dek=null;
        try{
            if(!X25519.calculateAgreement(privateKey,0,bytes(recipient.getString("ephemeral"),32),0,shared,0))throw new GeneralSecurityException("Invalid ephemeral key");
            byte[] aad=context(header.getString("backupId"),recipient,recipient.getString("ephemeral"));kek=hkdf(shared,bytes(header.getString("backupId"),32),aad);
            dek=crypt(Cipher.DECRYPT_MODE,kek,bytes(recipient.getString("iv"),12),aad,bytes(recipient.getString("wrapped"),48));
            if(dek.length!=32)throw new GeneralSecurityException("Invalid data key");
            int prefix=MAGIC.length+4+ByteBuffer.wrap(file,MAGIC.length,4).getInt();
            return crypt(Cipher.DECRYPT_MODE,dek,Arrays.copyOfRange(file,prefix,prefix+12),Arrays.copyOf(file,prefix),Arrays.copyOfRange(file,prefix+12,file.length));
        }finally{Arrays.fill(privateKey,(byte)0);Arrays.fill(shared,(byte)0);if(kek!=null)Arrays.fill(kek,(byte)0);if(dek!=null)Arrays.fill(dek,(byte)0);}
    }
}

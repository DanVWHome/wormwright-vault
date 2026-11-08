package ai.wormwright.notes.hardware;
import java.util.*;
import org.junit.Test;
import static org.junit.Assert.*;
public class CredentialSaltSelectorTest {
 @Test public void picksOnlyTheMatchedCredentialsOriginalSalt(){
  Map<String,Object> salts=new HashMap<>();byte[] one=new byte[32],two=new byte[32];Arrays.fill(two,(byte)7);
  salts.put(CredentialSaltSelector.id(new byte[]{1}),CredentialSaltSelector.id(one));salts.put(CredentialSaltSelector.id(new byte[]{2}),CredentialSaltSelector.id(two));
  assertArrayEquals(two,CredentialSaltSelector.select(salts,new byte[]{2}));assertArrayEquals(one,CredentialSaltSelector.select(salts,new byte[]{1}));
 }
 @Test public void unknownAndAbsentIdsNeverFallBackToAnotherSalt(){
  Map<String,Object> salts=Collections.singletonMap(CredentialSaltSelector.id(new byte[]{1}),CredentialSaltSelector.id(new byte[32]));
  for(byte[] id:new byte[][]{null,new byte[]{9}})try{CredentialSaltSelector.select(salts,id);fail();}catch(IllegalArgumentException expected){}
 }
 @Test public void malformedSaltIsRejected(){try{CredentialSaltSelector.select(Collections.singletonMap("AQ",CredentialSaltSelector.id(new byte[2])),new byte[]{1});fail();}catch(IllegalArgumentException expected){}}
}

package ai.wormwright.notes.hardware;

import org.junit.Test;
import java.security.*;
import java.util.Arrays;
import static org.junit.Assert.*;

public class AssertionVerifierTest {
    private static final String RP="atlas-portable.local";
    private static final byte[] ID={1,2,3}, CLIENT="fresh signed challenge".getBytes(), SECRET=new byte[32];
    private static class Fixture {
        final KeyPair key; final byte[] auth=new byte[37]; final byte[] signature;
        Fixture()throws Exception {
            KeyPairGenerator generator=KeyPairGenerator.getInstance("EC");generator.initialize(256);key=generator.generateKeyPair();
            System.arraycopy(MessageDigest.getInstance("SHA-256").digest(RP.getBytes()),0,auth,0,32);auth[32]=5;
            Signature s=Signature.getInstance("SHA256withECDSA");s.initSign(key.getPrivate());s.update(auth);s.update(MessageDigest.getInstance("SHA-256").digest(CLIENT));signature=s.sign();
        }
        void verify(byte[] id,String rp,byte[] expected,byte[] actual,byte[] data,byte[] sig,byte[] secret)throws Exception{
            AssertionVerifier.verify(key.getPublic(),ID,id,rp,expected,actual,data,sig,secret);
        }
    }
    private interface Check{void run()throws Exception;}
    private void rejects(Check c)throws Exception{try{c.run();fail("Accepted invalid assertion");}catch(GeneralSecurityException expected){}}
    @Test public void acceptsValidSignedAssertion()throws Exception{Fixture f=new Fixture();f.verify(ID,RP,CLIENT,CLIENT,f.auth,f.signature,SECRET);}
    @Test public void rejectsChangedChallengeCredentialAndOrigin()throws Exception{
        Fixture f=new Fixture();rejects(()->f.verify(ID,RP,new byte[32],CLIENT,f.auth,f.signature,SECRET));
        rejects(()->f.verify(new byte[]{9},RP,CLIENT,CLIENT,f.auth,f.signature,SECRET));
        rejects(()->f.verify(ID,"other.invalid",CLIENT,CLIENT,f.auth,f.signature,SECRET));
    }
    @Test public void rejectsReplayWithMatchingButUnsignedReplacementChallenge()throws Exception{
        Fixture f=new Fixture();byte[] other="new unsigned challenge".getBytes();rejects(()->f.verify(ID,RP,other,other,f.auth,f.signature,SECRET));
    }
    @Test public void requiresPresenceAndPinVerification()throws Exception{
        Fixture f=new Fixture();for(int flags:new int[]{0,1,4}){byte[] d=f.auth.clone();d[32]=(byte)flags;rejects(()->f.verify(ID,RP,CLIENT,CLIENT,d,f.signature,SECRET));}
    }
    @Test public void rejectsTamperedSignatureAndMissingSecret()throws Exception{
        Fixture f=new Fixture();byte[] sig=f.signature.clone();sig[sig.length-1]^=1;rejects(()->f.verify(ID,RP,CLIENT,CLIENT,f.auth,sig,SECRET));
        rejects(()->f.verify(ID,RP,CLIENT,CLIENT,f.auth,f.signature,null));rejects(()->f.verify(ID,RP,CLIENT,CLIENT,f.auth,f.signature,new byte[31]));
    }
}

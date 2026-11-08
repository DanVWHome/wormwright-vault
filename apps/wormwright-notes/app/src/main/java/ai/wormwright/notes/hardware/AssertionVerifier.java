package ai.wormwright.notes.hardware;

import java.security.*;
import java.util.Arrays;

/** Verify the signed assertion before using any returned wrapping secret. */
public final class AssertionVerifier {
    public static void verify(PublicKey publicKey, byte[] expectedId, byte[] actualId,
            String rpId, byte[] expectedClient, byte[] actualClient, byte[] authData,
            byte[] signature, byte[] secret) throws GeneralSecurityException {
        if (!MessageDigest.isEqual(expectedId, actualId)
                || !MessageDigest.isEqual(expectedClient, actualClient)
                || authData.length < 37 || (authData[32] & 5) != 5
                || secret == null || secret.length != 32) {
            throw new GeneralSecurityException("Incomplete or mismatched key assertion");
        }
        MessageDigest sha = MessageDigest.getInstance("SHA-256");
        if (!MessageDigest.isEqual(sha.digest(rpId.getBytes(java.nio.charset.StandardCharsets.UTF_8)),
                Arrays.copyOf(authData, 32))) throw new GeneralSecurityException("Wrong relying party");
        Signature verifier = Signature.getInstance("SHA256withECDSA");
        verifier.initVerify(publicKey);
        verifier.update(authData);
        verifier.update(sha.digest(actualClient));
        if (!verifier.verify(signature)) throw new GeneralSecurityException("Invalid key signature");
    }
    private AssertionVerifier() {}
}

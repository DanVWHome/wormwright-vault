package ai.wormwright.notes;

import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import java.security.KeyStore;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;

/** Phone-bound encryption key. MainActivity separately enforces fresh credential-only UI access. */
public final class PhoneSecrets implements NoteCipher.KeySource {
    private static final String ALIAS="wormwright-notes-secret-content-v1";
    public synchronized SecretKey get() throws Exception {
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");store.load(null);
        if(!store.containsAlias(ALIAS)){
            KeyGenerator generator=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(ALIAS,KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256).build());
            generator.generateKey();
        }
        return (SecretKey)store.getKey(ALIAS,null);
    }
}

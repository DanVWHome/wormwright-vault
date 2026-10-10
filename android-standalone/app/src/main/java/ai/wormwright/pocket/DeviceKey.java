package ai.wormwright.pocket;

import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import java.nio.charset.StandardCharsets;

/** Each slot has an independent authentication-per-operation key. No key recreation
 * on unlock: missing/inactivated keys require explicit portable-backup recovery. */
final class DeviceKey {
    private static final String PREFIX = "wormwright.pocket.slot.";
    static void deleteAll() throws Exception {
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");store.load(null);
        java.util.List<String> aliases=java.util.Collections.list(store.aliases());
        for(String alias:aliases)if(alias.startsWith(PREFIX))store.deleteEntry(alias);
    }
    static void delete(String slot) throws Exception {
        KeyStore store = KeyStore.getInstance("AndroidKeyStore"); store.load(null); store.deleteEntry(PREFIX + slot);
    }
    /** Called only after BiometricPrompt authenticates this operation. Even AAD
     * updates need the per-operation authentication token on KeyMint devices. */
    static byte[] finish(String slot, Cipher cipher, byte[] input) throws Exception {
        cipher.updateAAD(("WormwrightPocket:1:" + slot).getBytes(StandardCharsets.UTF_8));
        return cipher.doFinal(input);
    }
    static Cipher cipher(String slot, boolean create, byte[] iv) throws Exception {
        KeyStore store = KeyStore.getInstance("AndroidKeyStore"); store.load(null);
        String alias = PREFIX + slot;
        if (create) {
            if (store.containsAlias(alias)) throw new IllegalStateException("Key slot already exists");
            KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256).setUserAuthenticationRequired(true)
                .setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG | KeyProperties.AUTH_DEVICE_CREDENTIAL)
                .setInvalidatedByBiometricEnrollment(false).build());
            generator.generateKey();
        }
        SecretKey key = (SecretKey) store.getKey(alias, null);
        if (key == null) throw new IllegalStateException("Device key unavailable. Restore an exported backup; existing vault files were kept.");
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        if (create) cipher.init(Cipher.ENCRYPT_MODE, key);
        else cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, iv));
        return cipher;
    }
}

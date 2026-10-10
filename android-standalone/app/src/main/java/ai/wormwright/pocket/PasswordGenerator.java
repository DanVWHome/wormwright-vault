package ai.wormwright.pocket;

import java.security.SecureRandom;

/** Uses the operating system-backed cryptographic generator; no network or logging. */
final class PasswordGenerator {
    private static final SecureRandom RANDOM = new SecureRandom();
    private static final String ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%&*+-_=?.";
    static String generate() {
        StringBuilder password = new StringBuilder(24);
        for (int i=0;i<24;i++) password.append(ALPHABET.charAt(RANDOM.nextInt(ALPHABET.length())));
        return password.toString();
    }
}

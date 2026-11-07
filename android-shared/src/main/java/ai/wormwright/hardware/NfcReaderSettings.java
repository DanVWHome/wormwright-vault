package ai.wormwright.hardware;
import com.yubico.yubikit.android.transport.nfc.NfcConfiguration;
final class NfcReaderSettings {
    static NfcConfiguration create(){return new NfcConfiguration().skipNdefCheck(true).timeout(15000);}
    private NfcReaderSettings(){}
}

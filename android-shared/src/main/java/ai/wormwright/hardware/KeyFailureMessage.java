package ai.wormwright.hardware;
import com.yubico.yubikit.core.fido.CtapException;
import com.yubico.yubikit.fido.client.PinInvalidClientError;
import java.io.IOException;
final class KeyFailureMessage {
 static String describe(Throwable error,String stage){
  String code="";
  for(Throwable cause=error;cause!=null;cause=cause.getCause()){
   if(cause instanceof PinInvalidClientError){int remaining=((PinInvalidClientError)cause).pinRetries;return "The YubiKey PIN was rejected. This attempt stopped; the app will not retry it automatically."+(remaining>=0?" Attempts remaining on the key: "+remaining+".":"")+" Check the PIN before trying again.";}
   if(cause instanceof CtapException){
    int value=((CtapException)cause).getCtapError()&255;code=String.format(java.util.Locale.ROOT," / CTAP %02X",value);
    if(value==0x31)return "The YubiKey PIN was rejected. This attempt stopped without an automatic retry. Check the PIN before trying again.";
    if(value==0x32)return "The key's FIDO2 PIN is blocked. Stop trying PINs and use another enrolled key or an alternative unlock method.";
    if(value==0x34)return "The key has temporarily blocked PIN authentication. Remove and reconnect it before trying a known correct PIN.";
    if(value==0x2e)return "This YubiKey is not enrolled for this vault account. Use an enrolled key or an alternative unlock method.";
   }
   if(cause instanceof IllegalArgumentException&&"Key is not enrolled for this account".equals(cause.getMessage()))return "This YubiKey is not enrolled for this vault account. Use an enrolled key or an alternative unlock method.";
   if(cause instanceof IOException)return "The connection to the YubiKey failed. Reconnect USB-C or hold the key steadily at the NFC reader, then try again. Existing vault data was kept. Support code: "+stage+".";
  }
  return "YubiKey authentication did not complete. Existing vault data was kept. Support code: "+stage+code+". Check the connection and retry explicitly; the app does not retry PINs automatically.";
 }
 private KeyFailureMessage(){}
}

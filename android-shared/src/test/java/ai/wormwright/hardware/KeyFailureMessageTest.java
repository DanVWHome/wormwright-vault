package ai.wormwright.hardware;
import com.yubico.yubikit.core.fido.CtapException;
import com.yubico.yubikit.fido.client.PinInvalidClientError;
import org.junit.Test;
import static org.junit.Assert.*;
public class KeyFailureMessageTest {
 @Test public void rejectedPinHasClearMessageAndActualRetryCount(){String m=KeyFailureMessage.describe(new PinInvalidClientError(new CtapException(CtapException.ERR_PIN_INVALID),6),"UNLOCK");assertTrue(m.contains("PIN was rejected"));assertTrue(m.contains("6"));assertTrue(m.contains("will not retry"));}
 @Test public void blockedPinDoesNotSuggestRepeatedAttempts(){assertTrue(KeyFailureMessage.describe(new CtapException(CtapException.ERR_PIN_BLOCKED),"UNLOCK").contains("Stop trying PINs"));}
 @Test public void unknownFailureDoesNotExposeExceptionMessage(){assertFalse(KeyFailureMessage.describe(new Exception("synthetic-private-data"),"UNLOCK").contains("synthetic-private-data"));}
}

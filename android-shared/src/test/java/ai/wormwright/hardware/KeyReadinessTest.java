package ai.wormwright.hardware;
import org.junit.Test;
import static org.junit.Assert.*;
public class KeyReadinessTest {
 @Test public void pinFirstWaitsForKey(){KeyReadiness g=new KeyReadiness();assertFalse(g.pinSubmitted());assertTrue(g.deviceDetected());assertFalse(g.deviceDetected());assertFalse(g.pinSubmitted());}
 @Test public void keyFirstWaitsForPin(){KeyReadiness g=new KeyReadiness();assertFalse(g.deviceDetected());assertTrue(g.pinSubmitted());assertFalse(g.deviceDetected());assertFalse(g.pinSubmitted());}
 @Test public void cancellationRejectsLateInputs(){KeyReadiness g=new KeyReadiness();g.deviceDetected();g.cancel();assertFalse(g.pinSubmitted());assertFalse(g.deviceDetected());}
}

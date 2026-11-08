package ai.wormwright.notes.hardware;
import java.util.*;
import org.junit.Test;
import static org.junit.Assert.*;
public class ForegroundNfcLeaseTest {
 @Test public void terminalAuthenticationKeepsReaderUntilBackground(){
  List<String> stopped=new ArrayList<>();ForegroundNfcLease<String> lease=new ForegroundNfcLease<>(stopped::add);
  lease.retain("reader");assertTrue(stopped.isEmpty());lease.release();assertEquals(Arrays.asList("reader"),stopped);
 }
 @Test public void replacingReaderStopsOnlyThePreviousSubscription(){
  List<String> stopped=new ArrayList<>();ForegroundNfcLease<String> lease=new ForegroundNfcLease<>(stopped::add);
  lease.retain("old");lease.retain("new");assertEquals(Arrays.asList("old"),stopped);lease.release();assertEquals(Arrays.asList("old","new"),stopped);
 }
 @Test public void repeatedRetentionAndCleanupAreIdempotent(){
  List<Object> stopped=new ArrayList<>();Object reader=new Object();ForegroundNfcLease<Object> lease=new ForegroundNfcLease<>(stopped::add);
  lease.retain(reader);lease.retain(reader);lease.release();lease.release();assertEquals(Arrays.asList(reader),stopped);
 }
 @Test public void readerSkipsWebLinkInspectionAndAllowsNfcCommandTime(){
  assertTrue(NfcReaderSettings.create().isSkipNdefCheck());assertEquals(15000,NfcReaderSettings.create().getTimeout());
 }
}

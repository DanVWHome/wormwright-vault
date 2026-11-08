package ai.wormwright.notes.hardware;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import org.junit.Test;
import static org.junit.Assert.*;
public class SessionOwnerTest {
 @Test public void cancellationAndCompletionCloseExactlyOnce()throws Exception{
  AtomicInteger calls=new AtomicInteger();SessionOwner<AutoCloseable> owner=new SessionOwner<>();owner.attach(()->calls.incrementAndGet());owner.close();owner.close();assertEquals(1,calls.get());
 }
 @Test public void aSessionOpenedAfterCancellationIsClosedWithoutUse()throws Exception{
  AtomicInteger calls=new AtomicInteger();SessionOwner<AutoCloseable> owner=new SessionOwner<>();owner.close();assertFalse(owner.attach(()->calls.incrementAndGet()));owner.close();assertEquals(1,calls.get());
 }
 @Test public void nextOperationCannotRunUntilPreviousConnectionHasFinishedClosing()throws Exception{
  SessionOwner<AutoCloseable> owner=new SessionOwner<>();CountDownLatch entered=new CountDownLatch(1),finishClose=new CountDownLatch(1),operationReady=new CountDownLatch(1),sdkReturned=new CountDownLatch(1);AtomicBoolean closed=new AtomicBoolean();ExecutorService serial=Executors.newSingleThreadExecutor();
  try{
   Future<?> first=serial.submit(()->{try{owner.attach(()->{entered.countDown();assertTrue(finishClose.await(3,TimeUnit.SECONDS));closed.set(true);});operationReady.countDown();sdkReturned.await();owner.close();}catch(Exception e){throw new RuntimeException(e);}});
   assertTrue(operationReady.await(3,TimeUnit.SECONDS));Thread cancel=new Thread(()->{try{owner.close();}catch(Exception e){throw new RuntimeException(e);}});cancel.start();assertTrue(entered.await(3,TimeUnit.SECONDS));sdkReturned.countDown();
   Future<Boolean> next=serial.submit(()->closed.get());assertFalse(next.isDone());finishClose.countDown();cancel.join(3000);first.get(3,TimeUnit.SECONDS);assertTrue(next.get(3,TimeUnit.SECONDS));
  }finally{finishClose.countDown();sdkReturned.countDown();serial.shutdownNow();}
 }
 @Test public void repeatedTransportCyclesDoNotReusePinOrConnection()throws Exception{
  ExecutorService serial=Executors.newSingleThreadExecutor();AtomicInteger closes=new AtomicInteger();
  try{for(int cycle=0;cycle<40;cycle++){
   final int index=cycle;PinBuffer pin=new PinBuffer();char[] expected=("Demo-"+index+"!").toCharArray();pin.set(expected.clone());SessionOwner<AutoCloseable> owner=new SessionOwner<>();CountDownLatch inFlight=new CountDownLatch(1),readPin=new CountDownLatch(1);
   Future<?> operation=serial.submit(()->{char[] local=pin.copyForOperation();try{assertEquals(index,closes.get());owner.attach(()->closes.incrementAndGet());inFlight.countDown();readPin.await();assertArrayEquals(expected,local);}catch(Exception e){throw new RuntimeException(e);}finally{try{owner.close();}catch(Exception e){throw new RuntimeException(e);}java.util.Arrays.fill(local,'\0');}});
   assertTrue(inFlight.await(3,TimeUnit.SECONDS));pin.clear();if(index%2==0)owner.close();readPin.countDown();operation.get(3,TimeUnit.SECONDS);assertEquals(index+1,closes.get());
  }}finally{serial.shutdownNow();}
 }
}

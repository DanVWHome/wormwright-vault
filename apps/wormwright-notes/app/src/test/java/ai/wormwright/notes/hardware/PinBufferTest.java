package ai.wormwright.notes.hardware;
import java.util.Arrays;
import org.junit.Test;
import static org.junit.Assert.*;
public class PinBufferTest {
 @Test public void cancellingUiCannotZeroThePinBeingReadBySdk(){
  PinBuffer input=new PinBuffer();char[] entered={'1','2','3','4'};input.set(entered);
  assertArrayEquals(new char[4],entered);
  char[] worker=input.copyForOperation();input.clear();
  assertArrayEquals(new char[]{'1','2','3','4'},worker);
  Arrays.fill(worker,'\0');assertArrayEquals(new char[4],worker);
 }
 @Test public void cancelledPinCannotBeUsedForALaterAttempt(){
  PinBuffer input=new PinBuffer();input.set(new char[]{'1','2','3','4'});input.clear();
  try{input.copyForOperation();fail();}catch(IllegalStateException expected){}
 }
 @Test public void aNewAttemptHasIndependentPinStorage(){
  PinBuffer old=new PinBuffer(),next=new PinBuffer();old.set(new char[]{'1','2','3','4'});next.set(new char[]{'5','6','7','8'});old.clear();assertArrayEquals(new char[]{'5','6','7','8'},next.copyForOperation());next.clear();
 }
}

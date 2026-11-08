package ai.wormwright.notes.hardware;
import java.util.Arrays;
/** UI-owned input. An in-flight operation owns a separate copy, wiped by its
 * worker only after I/O has stopped. UI cancellation must not change SDK input. */
final class PinBuffer {
 private char[] value;private boolean closed;
 synchronized void set(char[] entered){
  try{if(closed||value!=null)throw new IllegalStateException("PIN input is no longer active");value=entered.clone();}
  finally{Arrays.fill(entered,'\0');}
 }
 synchronized char[] copyForOperation(){if(closed||value==null)throw new IllegalStateException("PIN input was cancelled");return value.clone();}
 synchronized void clear(){closed=true;if(value!=null){Arrays.fill(value,'\0');value=null;}}
}

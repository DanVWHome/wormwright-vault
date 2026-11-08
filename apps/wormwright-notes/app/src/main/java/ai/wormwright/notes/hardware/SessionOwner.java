package ai.wormwright.notes.hardware;
/** Closing is serialized with attachment and completion. A cancelled operation
 * cannot attach a late session, and the connection is closed exactly once. */
final class SessionOwner<T extends AutoCloseable> implements AutoCloseable {
 private T value;private boolean closed;
 synchronized boolean attach(T incoming)throws Exception{
  if(closed){incoming.close();return false;}
  if(value!=null){incoming.close();throw new IllegalStateException("Session already attached");}
  value=incoming;return true;
 }
 @Override public synchronized void close()throws Exception{
  if(closed)return;closed=true;T previous=value;value=null;if(previous!=null)previous.close();
 }
}

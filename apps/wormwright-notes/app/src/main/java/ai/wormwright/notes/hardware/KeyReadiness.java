package ai.wormwright.notes.hardware;
/** Start exactly once after both inputs arrive, in either order. Holds no PIN. */
final class KeyReadiness {
 private boolean pin,device,started,cancelled;
 synchronized boolean pinSubmitted(){if(cancelled)return false;pin=true;return take();}
 synchronized boolean deviceDetected(){if(cancelled)return false;device=true;return take();}
 private boolean take(){if(started||!pin||!device)return false;started=true;return true;}
 synchronized void deviceLost(){if(!started)device=false;}
 synchronized void cancel(){cancelled=true;pin=false;device=false;}
}

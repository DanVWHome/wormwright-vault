package ai.wormwright.notes.hardware;
import java.util.function.Consumer;

/** Retain only the reader subscription after authentication, never PIN/session
 * material. Release it when the host leaves the foreground or replaces it. */
final class ForegroundNfcLease<T> {
    private T reader;
    private final Consumer<T> stop;
    ForegroundNfcLease(Consumer<T> stop){this.stop=stop;}
    void retain(T next){if(reader==next)return;release();reader=next;}
    void release(){T previous=reader;reader=null;if(previous!=null)stop.accept(previous);}
}

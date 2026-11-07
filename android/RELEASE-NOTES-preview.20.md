# Android .20 — isolated PIN buffers and serialized key connections

A real cancellation race was found: UI cleanup could zero the same mutable PIN
array that YubiKit was still reading. Each hardware operation now receives its
own PIN copy, which is cleared only by its worker after connection cleanup. UI
cancellation clears its separate input copy immediately.

Authentication runs on one worker per app controller. The physical connection
is owned before session construction and closed exactly once, including during
cancellation. Another operation cannot start until the previous worker finishes
cleanup. The SDK callback wrapper no longer also closes that same connection.

USB key removal invalidates a pending device reference. USB takes precedence
when a key is physically plugged in so a nearby NFC detection cannot replace it.
USB keyboard configuration changes no longer recreate the app screen. This does
not change the PIN keyboard layout; the requested numeric/full-keyboard feature
remains deferred. Desktop behavior, enrollment data and the key-plus-PIN model
are unchanged. No PIN reset or re-enrollment is needed.

Connection failures include a transport/stage support code. Existing NFC reader
protection and acknowledged error alerts remain. This build does not retry PINs
automatically.

Synthetic tests cover cancelling while the SDK owns a PIN copy, late connection
attachment after cancellation, close-once ownership, cancellation/completion
races, stale device invalidation and 40 repeated simulated operation cycles.
No physical PIN attempts are consumed by these tests. Physical NFC/USB switching
and repeated lock/unlock still need device confirmation. Network/NAS remains
untested on the physical phone.

Install over the existing apps. After installation, test only with the known
correct PIN and stop at the first unexpected error. Do not reset the key or
repeat wrong-PIN tests while diagnosing connection stability.

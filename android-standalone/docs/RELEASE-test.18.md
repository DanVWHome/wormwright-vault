# Android .18 — keep NFC unlock inside the vault app

Pocket NFC authentication was confirmed working, but Android opened the key's
separate web link immediately afterward and took the user out of the app.

The app now retains its NFC reader subscription after success or failure while
it remains in the foreground, suppressing a second web-link scan while the key
is still against the phone. PIN buffers and FIDO sessions are still cleared at
completion. The retained subscription ignores further tags and does not perform
another authentication. Leaving the foreground explicitly releases it.

NFC scans skip NDEF web-link inspection and use a 15-second communication timeout.
NFC instructions say to keep the key against the phone rather than touch its gold
contact. USB-C unlock steps are unchanged. YubiKey unlock still requires only
the physical key and its PIN; phone and vault-password unlock remain alternatives.

Install over the existing Android apps. Do not uninstall or re-enroll working
keys. Desktop Mint remains 0.3.10. The Network/NAS app remains untested on the
physical phone; the shared fix is included in both Android apps. Physical-device
confirmation of the new NFC handoff behavior is pending.

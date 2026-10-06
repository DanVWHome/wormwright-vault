"""Opt-in desktop-session launcher. Only fixed, validated UI requests allowed."""
import argparse
import os
from pathlib import Path
import subprocess
import signal
import time
from hooks import LocalControl, default_vault, send, agent_vault, launch_command


def main():
    parser = argparse.ArgumentParser(description='Wormwright AI desktop-session launcher')
    parser.add_argument('--vault', type=Path, default=default_vault())
    args = parser.parse_args()
    os.umask(0o077)
    stopping = False
    child = None

    def stop(*unused):
        nonlocal stopping
        stopping = True

    def handle(request):
        nonlocal child
        try:
            send(args.vault, request)
        except (FileNotFoundError, ConnectionRefusedError):
            if request['action'] == 'lock':
                return
            # If startup is already underway, retain the latest request for delivery.
            if child is None or child.poll() is not None:
                command = launch_command(args.vault, request)
                child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL)
            pending[:] = [request]

    pending = []
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    service = LocalControl(agent_vault(args.vault), handle)
    try:
        while not stopping:
            service.poll()
            if pending:
                try:
                    send(args.vault, pending[-1])
                    pending.clear()
                except (FileNotFoundError, ConnectionRefusedError):
                    if child is not None and child.poll() is not None:
                        pending.clear()
            time.sleep(.05)
    finally:
        service.close()


if __name__ == '__main__':
    main()

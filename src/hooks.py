"""Versioned, local-only UI requests. Never returns vault contents or secrets."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import struct
import subprocess
import sys
import time

VERSION = 1
ACTIONS = ('open', 'lookup', 'lock', 'capabilities')


def default_vault():
    data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    legacy = data / 'atlas-portable/demo-vault.sqlite'
    return legacy if legacy.exists() else data / 'vanwormai-vault/demo-vault.sqlite'


def endpoint(vault):
    root = Path(vault).resolve().parent / '.vanwormai-control'
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('The local control directory must be an owner-only directory.')
    identity = hashlib.sha256(str(Path(vault).resolve()).encode()).hexdigest()[:16]
    return root / (identity + '.sock')


def validate(request):
    if not isinstance(request, dict) or request.get('version') != VERSION:
        raise ValueError('Unsupported request version')
    if request.get('action') not in ACTIONS:
        raise ValueError('Unsupported action')
    if set(request) - {'version', 'action', 'query'}:
        raise ValueError('Unsupported field')
    if request['action'] == 'lookup':
        query = request.get('query')
        if not isinstance(query, str) or not query.strip() or len(query) > 512:
            raise ValueError('Invalid lookup query')
    elif 'query' in request:
        raise ValueError('Query is only allowed for lookup')
    return request


def send(vault, request):
    validate(request)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(2)
        client.connect(str(endpoint(vault)))
        client.sendall(json.dumps(request).encode() + b'\n')
        data = b''
        while b'\n' not in data:
            block = client.recv(1024)
            if not block or len(data) > 4096:
                raise ValueError('Invalid control response')
            data += block
        return json.loads(data.split(b'\n', 1)[0])


class LocalControl:
    def __init__(self, vault, callback):
        self.path = endpoint(vault)
        self.callback = callback
        self.clients = {}
        self.lock_fd = os.open(str(self.path) + '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            os.close(self.lock_fd)
            raise RuntimeError('This vault is already open in another instance.')
        self.path.unlink(missing_ok=True)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.server.bind(str(self.path))
            os.chmod(self.path, 0o600)
            self.server.listen(8)
            self.server.setblocking(False)
        except Exception:
            self.server.close()
            os.close(self.lock_fd)
            raise

    def poll(self):
        for _ in range(8):
            try:
                client, _ = self.server.accept()
            except BlockingIOError:
                break
            uid = struct.unpack('3i', client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))[1]
            if uid != os.getuid() or len(self.clients) >= 16:
                client.close()
                continue
            client.setblocking(False)
            self.clients[client] = (b'', time.monotonic())
        for client, (data, started) in list(self.clients.items()):
            done = False
            try:
                if time.monotonic() - started > 2:
                    raise ValueError('Request timed out')
                try:
                    block = client.recv(4097)
                except BlockingIOError:
                    continue
                if not block:
                    raise ValueError('Empty request')
                data += block
                if len(data) > 4096:
                    raise ValueError('Request too large')
                if b'\n' not in data:
                    self.clients[client] = (data, started)
                    continue
                done = True
                request = validate(json.loads(data.split(b'\n', 1)[0]))
                if request['action'] == 'capabilities':
                    response = {'version': VERSION, 'actions': list(ACTIONS), 'returns_secrets': False}
                else:
                    self.callback(request)
                    response = {'version': VERSION, 'accepted': True}
                client.sendall(json.dumps(response).encode() + b'\n')
            except Exception:
                done = True
                try:
                    client.sendall(b'{"version":1,"accepted":false}\n')
                except OSError:
                    pass
            finally:
                if done:
                    self.clients.pop(client, None)
                    client.close()

    def close(self):
        for client in self.clients:
            client.close()
        self.clients.clear()
        self.server.close()
        self.path.unlink(missing_ok=True)
        os.close(self.lock_fd)


def agent_vault(vault):
    path = Path(vault)
    return path.with_name(path.name + '.desktop-agent')


def launch_command(vault, request):
    here = Path(__file__).resolve().parent
    launcher = here / 'start.sh'
    if not launcher.exists():
        launcher = here.parent / 'start.sh'
    command = [str(launcher), str(vault)]
    if request['action'] == 'lookup':
        command += ['--lookup', request['query']]
    return command


def route(vault, request):
    try:
        return send(agent_vault(vault), request)
    except (FileNotFoundError, ConnectionRefusedError):
        return send(vault, request)


def main():
    parser = argparse.ArgumentParser(description='Wormwright Vault UI control; no secret access')
    parser.add_argument('action', choices=ACTIONS)
    parser.add_argument('query', nargs='?')
    parser.add_argument('--vault', type=Path, default=default_vault())
    args = parser.parse_args()
    request = {'version': VERSION, 'action': args.action}
    if args.query is not None:
        request['query'] = args.query
    validate(request)
    try:
        response = route(args.vault, request)
    except (FileNotFoundError, ConnectionRefusedError):
        if args.action == 'capabilities':
            response = {'version': VERSION, 'actions': list(ACTIONS), 'returns_secrets': False}
        elif args.action == 'lock':
            response = {'version': VERSION, 'accepted': True}
        else:
            command = launch_command(args.vault, request)
            subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
            response = {'version': VERSION, 'launch_requested': True}
    print(json.dumps(response))


if __name__ == '__main__':
    main()

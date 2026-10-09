"""Same-user named-pipe UI requests on Windows. No vault contents returned."""
import hashlib
import json
import os
from pathlib import Path
import time
from PySide6.QtCore import QCoreApplication, QLockFile
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from platform_paths import data_home


def pipe_name(vault):
    identity = os.path.normcase(str(Path(vault).resolve()))
    return 'wormwright-vault-' + hashlib.sha256(identity.encode()).hexdigest()


def send(vault, request):
    from hooks import validate
    validate(request)
    # Startup routing happens before QApplication is created.
    owns_application = QCoreApplication.instance() is None
    application = QCoreApplication.instance() or QCoreApplication([])
    client = QLocalSocket()
    try:
        client.connectToServer(pipe_name(vault))
        if not client.waitForConnected(2000):
            raise ConnectionRefusedError(client.errorString())
        client.write(json.dumps(request).encode() + b'\n')
        if client.bytesToWrite() and not client.waitForBytesWritten(2000):
            raise ValueError('Control request timed out')
        data = b''
        deadline = time.monotonic() + 2
        while b'\n' not in data:
            if not client.bytesAvailable() and not client.waitForReadyRead(max(1, int((deadline-time.monotonic())*1000))):
                raise ValueError('Control response timed out')
            data += bytes(client.readAll())
            if len(data) > 4096 or time.monotonic() > deadline:
                raise ValueError('Invalid control response')
        return json.loads(data.split(b'\n', 1)[0])
    finally:
        client.abort()
        # Do not leave a QCoreApplication that prevents later QApplication creation.
        if owns_application:
            from shiboken6 import delete
            delete(application)


class LocalControl:
    def __init__(self, vault, callback):
        self.callback = callback
        self.clients = {}
        folder = data_home() / 'vanwormai-vault/control'
        folder.mkdir(parents=True, exist_ok=True)
        self.lock = QLockFile(str(folder / (pipe_name(vault) + '.lock')))
        if not self.lock.tryLock(0):
            raise RuntimeError('This vault is already open in another instance.')
        self.server = QLocalServer()
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        self.server.setMaxPendingConnections(16)
        if not self.server.listen(pipe_name(vault)):
            self.lock.unlock()
            raise RuntimeError(self.server.errorString())

    def poll(self):
        from hooks import ACTIONS, VERSION, validate
        while self.server.hasPendingConnections():
            client = self.server.nextPendingConnection()
            if len(self.clients) >= 16:
                client.abort(); client.deleteLater()
            else:
                self.clients[client] = (b'', time.monotonic())
        for client, (data, started) in list(self.clients.items()):
            done = False
            try:
                if time.monotonic() - started > 2:
                    raise ValueError('Request timed out')
                data += bytes(client.readAll())
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
                client.write(json.dumps(response).encode() + b'\n')
            except Exception:
                done = True
                client.write(b'{"version":1,"accepted":false}\n')
            finally:
                if done:
                    client.flush(); client.disconnectFromServer()
                    self.clients.pop(client, None)
                    client.deleteLater()

    def close(self):
        for client in self.clients:
            client.abort(); client.deleteLater()
        self.clients.clear()
        self.server.close()
        self.lock.unlock()

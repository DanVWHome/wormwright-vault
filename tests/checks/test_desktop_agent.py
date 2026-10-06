"""Dummy desktop-session agent starts the UI and forwards only fixed requests."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
SOURCE = Path(__file__).resolve().parents[2] / 'src'
sys.path.insert(0, str(SOURCE))
from hooks import agent_vault, send, route
with tempfile.TemporaryDirectory() as directory:
    vault = Path(directory) / 'dummy.sqlite'
    runner = "import sys; sys.path.insert(0, sys.argv[1]); import desktop_agent; source=sys.argv[1]; desktop_agent.launch_command=lambda v,r: [sys.executable, source+'/app.py',str(v),'--lookup',r.get('query','')]; sys.argv=['agent','--vault',sys.argv[2]]; desktop_agent.main()"
    process = subprocess.Popen([sys.executable, '-c', runner, str(SOURCE), str(vault)], start_new_session=True)
    try:
        def wait_send(path, request):
            for attempt in range(100):
                try: return send(path, request)
                except (FileNotFoundError, ConnectionRefusedError): time.sleep(.05)
            raise AssertionError('UI endpoint did not start')
        request = {'version':1, 'action':'lookup', 'query':'Demo Mail'}
        response = wait_send(agent_vault(vault), request)
        assert response == {'version':1,'accepted':True}
        response = wait_send(vault, {'version':1,'action':'capabilities'})
        assert response['returns_secrets'] is False
        assert route(vault, {'version':1,'action':'lock'}) == {'version':1,'accepted':True}
        assert not vault.exists(), 'Launching locked UI must not create or unlock a vault'
    finally:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
print('PASS: optional agent cold start, masked lookup routing, no vault creation/unlock, lock forwarding')

"""Package-upgrade layout checked with a synthetic stage; no installed files touched."""
import importlib.util
from pathlib import Path
import tempfile
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('mint_build',ROOT/'packaging/build-mint.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as directory:
    stage=Path(directory)
    for name in ('usr/lib/wormwright-vault-managed-beta','usr/share/doc/wormwright-vault-managed-beta','usr/share/applications','usr/share/pixmaps','usr/bin','DEBIAN'):(stage/name).mkdir(parents=True)
    (stage/'DEBIAN/control').write_text('Package: wormwright-vault-managed-beta\nVersion: 0.3.0\nDescription: Managed multi-user vault test build, installed alongside personal Vault\n Prototype desktop vault with local UI-only assistant hooks.\n')
    module.prepare(stage)
    control=(stage/'DEBIAN/control').read_text()
    assert 'Package: wormwright-vault-mint\n' in control
    assert 'Conflicts: wormwright-vault-managed-beta\n' in control
    assert 'Replaces: wormwright-vault-managed-beta\n' in control
    for name in ('wormwright-vault-mint','wormwright-vault-manager-mint'):
        assert '/usr/lib/wormwright-vault-mint/vanwormai-vault --beta' in (stage/'usr/bin'/name).read_text()
        assert 'Test' not in (stage/'usr/share/applications'/(name+'.desktop')).read_text()
    assert '--manager' in (stage/'usr/bin/wormwright-vault-manager-mint').read_text()
    assert '/usr/bin/wormwright-vault-mint' in (stage/'usr/bin/wormwright-vault-beta').read_text()
    assert (stage/'usr/share/wormwright-vault-mint/hooks.py').exists()
    assert not (stage/'home').exists() # no vault moves or user data in package
print('Mint package identity, upgrade conflict, launcher compatibility and no-user-data staging checks passed')

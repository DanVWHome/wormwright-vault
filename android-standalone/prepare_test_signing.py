"""Create a dedicated persistent test identity outside the repository.
Never reuse the companion's signing credentials. Production uses Play App Signing
and a separate publisher-controlled upload key, not this test identity.
"""
from pathlib import Path
import os
import secrets
import subprocess
import sys
folder=Path(sys.argv[1]).resolve();folder.mkdir(parents=True,exist_ok=True,mode=0o700)
key=folder/'pocket-test.jks';properties=folder/'pocket-test.properties'
if key.exists() != properties.exists():raise SystemExit('Incomplete identity: preserve it and recover, do not silently regenerate.')
if not key.exists():
    password=secrets.token_urlsafe(48)
    env=dict(os.environ,WORMWRIGHT_KEY_PASSWORD=password)
    subprocess.run(['keytool','-genkeypair','-keystore',str(key),'-storetype','JKS',
                    '-storepass:env','WORMWRIGHT_KEY_PASSWORD','-keypass:env','WORMWRIGHT_KEY_PASSWORD',
                    '-alias','pocket-test','-keyalg','RSA','-keysize','3072','-validity','10000',
                    '-dname','CN=Wormwright Pocket Vault Test, O=Dan Van Wormer'],env=env,check=True)
    key.chmod(0o600)
    properties.write_text('storeFile='+str(key)+'\nstorePassword='+password+'\nkeyAlias=pocket-test\nkeyPassword='+password+'\n')
    properties.chmod(0o600)
print('Dedicated persistent test signing identity prepared outside repository.')

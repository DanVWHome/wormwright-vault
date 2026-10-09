from pathlib import Path
import re,sys
p=Path('android/app/build.gradle');s=p.read_text()
start=s.index('    signingConfigs {');end=s.index('    buildTypes {',start)
s=s[:start]+s[end:];s=s.replace('; signingConfig signingConfigs.preview','')
s=s.replace("versionCode 3","testInstrumentationRunner 'androidx.test.runner.AndroidJUnitRunner'\n        versionCode 3")
s=s.replace("dependencies {","dependencies {\n    androidTestImplementation 'androidx.test:runner:1.6.2'\n    androidTestImplementation 'androidx.test:core:1.6.1'\n    androidTestImplementation 'androidx.test.ext:junit:1.2.1'")
s=s.replace("buildPython rootProject.file('../tools/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13').absolutePath",'buildPython "'+sys.executable+'"')
p.write_text(s)
sys.path.insert(0,str(Path('android/app/src/main/python').resolve()))
from managed_vault import ManagedVault
assets=Path('android/app/src/main/assets');assets.mkdir(parents=True,exist_ok=True)
sample=assets/'sample-vault.db'
if sample.exists():sample.unlink()
v=ManagedVault(sample);v.create('SampleOnly-October2026!',username='Demo')
for i,(description,user,link) in enumerate([
('Family email','demo@example.invalid','https://mail.example.invalid'),
('Home Wi-Fi','Family network',''),('Front door code','Main entrance',''),
('Streaming account','family@example.invalid','https://stream.example.invalid'),
('Work email','work@example.invalid','https://work.example.invalid'),
('Travel booking','demo@example.invalid','https://travel.example.invalid'),
('Garage keypad','Side entrance',''),('Recovery codes','Family account',''),
('Luggage combination','Blue suitcase',''),('Project dashboard','demo@example.invalid','https://projects.example.invalid')]):
 v.save(dict(description=description,user_name=user,link=link,password=f'Fictional-Demo-{i:02d}!',notes='Fictional example for the website. Not a real credential.'))
v.lock()

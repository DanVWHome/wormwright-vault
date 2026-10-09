"""Browser-only Windows update discovery. Never downloads or executes code."""
import json
import re
import sys
import time
from pathlib import Path
from PySide6.QtCore import QObject, QTimer, QUrl, Qt
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QComboBox, QDialogButtonBox, QMessageBox
from shiboken6 import isValid
from platform_paths import data_home
from sync import atomic_json
from version import VERSION

FEED_URL = 'https://wormwright.com/updates/vault-windows.json'
DOWNLOAD_URL = 'https://wormwright.com/vault-windows.html'
CURRENT = VERSION + '-preview.1'
DAY = 86400
MAX_BYTES = 65536

def version_key(value):
    match = re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-preview\.([1-9]\d*))?', value if isinstance(value,str) else '')
    if not match:
        raise ValueError('Invalid release version')
    major,minor,patch,preview = match.groups()
    return (int(major),int(minor),int(patch),1 if preview is None else 0,int(preview or 0))

def release_from_feed(raw, channel):
    if len(raw) > MAX_BYTES:
        raise ValueError('Update response is too large')
    feed = json.loads(raw)
    if not isinstance(feed,dict) or feed.get('schema') != 1 or not isinstance(feed.get('channels'),dict):
        raise ValueError('Invalid update information')
    release = feed['channels'].get(channel)
    if release is None:
        return None
    if not isinstance(release,dict):
        raise ValueError('Invalid release information')
    version_key(release.get('version'))
    if (channel == 'stable') != ('-preview.' not in release['version']):
        raise ValueError('Release channel mismatch')
    if not isinstance(release.get('notes'),str) or len(release['notes']) > 12000:
        raise ValueError('Invalid release notes')
    return release

def settings_path():
    return data_home() / 'wormwright-vault-beta/update-settings.json'

def read_settings():
    defaults = {'automatic':False,'channel':'preview','last_check':0}
    try:
        value=json.loads(settings_path().read_text())
        if type(value.get('automatic')) is bool: defaults['automatic']=value['automatic']
        if value.get('channel') in ('stable','preview'): defaults['channel']=value['channel']
        stamp=value.get('last_check')
        if type(stamp) in (int,float) and 0 <= stamp <= time.time(): defaults['last_check']=stamp
    except (OSError,ValueError,AttributeError,TypeError): pass
    return defaults

class UpdateChecker(QObject):
    def __init__(self,app):
        super().__init__(app)
        self.network=QNetworkAccessManager(self);self.pending=False;self.owner=None
        self.timer=QTimer(self);self.timer.timeout.connect(self.automatic);self.timer.start(3600000)
        QTimer.singleShot(5000,self.automatic)

    def save(self,settings):
        path=settings_path();path.parent.mkdir(parents=True,exist_ok=True)
        atomic_json(path,settings)

    def automatic(self):
        settings=read_settings()
        if settings['automatic'] and time.time()-settings['last_check'] >= DAY:
            self.check(self.owner,False)

    def preferences(self,owner):
        settings=read_settings();dialog=QDialog(owner);dialog.setWindowTitle('Update Settings');dialog.setMinimumWidth(440)
        layout=QVBoxLayout(dialog)
        automatic=QCheckBox('Check automatically once a day while the app is running');automatic.setChecked(settings['automatic']);layout.addWidget(automatic)
        layout.addWidget(QLabel('Release channel:'))
        channel=QComboBox();channel.addItems(['Stable','Preview']);channel.setCurrentIndex(0 if settings['channel']=='stable' else 1);layout.addWidget(channel)
        note=QLabel('Checks fetch public version information only. No vault, account or search data is sent. Updates open the official download page; you install them yourself.');note.setWordWrap(True);layout.addWidget(note)
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec():
            settings.update(automatic=automatic.isChecked(),channel='stable' if channel.currentIndex()==0 else 'preview')
            try:self.save(settings)
            except OSError:QMessageBox.warning(owner,'Cannot save update settings','Your update preferences could not be saved.')

    def check(self,owner,manual=True):
        if self.pending:
            if manual:QMessageBox.information(owner,'Check for Updates','An update check is already running.')
            return
        self.pending=True;settings=read_settings();settings['last_check']=time.time()
        try:self.save(settings)
        except OSError:pass
        request=QNetworkRequest(QUrl(FEED_URL));request.setTransferTimeout(15000)
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute,QNetworkRequest.ManualRedirectPolicy)
        request.setRawHeader(b'User-Agent',b'Wormwright-Vault-Update-Check');request.setRawHeader(b'Cache-Control',b'no-cache')
        reply=self.network.get(request)
        reply.readyRead.connect(lambda:reply.abort() if reply.bytesAvailable()>MAX_BYTES else None)
        def finished():
            self.pending=False
            parent=owner if owner is not None and isValid(owner) else None
            try:
                if reply.error()!=QNetworkReply.NoError or reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)!=200:
                    raise ValueError('Update service is unavailable')
                release=release_from_feed(bytes(reply.readAll()),settings['channel'])
                if release is None:
                    if manual:QMessageBox.information(parent,'Check for Updates','No Windows release is available in the selected channel yet. Use Update Settings to select Preview.')
                elif version_key(release['version']) <= version_key(CURRENT):
                    if manual:QMessageBox.information(parent,'Check for Updates',f'You are up to date for the {settings["channel"]} channel. Running {CURRENT}.')
                else:
                    box=QMessageBox(parent);box.setWindowTitle('Update Available');box.setText(f'Wormwright Vault {release["version"]} is available.');box.setInformativeText('Running '+CURRENT+'\n\n'+release['notes']);box.setTextFormat(Qt.PlainText)
                    download=box.addButton('Download Update',QMessageBox.AcceptRole);box.addButton('Later',QMessageBox.RejectRole);box.exec()
                    if box.clickedButton()==download and not QDesktopServices.openUrl(QUrl(DOWNLOAD_URL)):
                        QMessageBox.information(parent,'Download Update','Open '+DOWNLOAD_URL+' in your browser.')
            except (ValueError,TypeError,KeyError):
                if manual:QMessageBox.warning(parent,'Cannot check for updates','The update service could not be reached or returned invalid information. Try again later or visit wormwright.com.')
            finally:reply.deleteLater()
        reply.finished.connect(finished)

_checker=None

def add_update_actions(menu,owner,automatic_owner=True):
    if sys.platform != 'win32':return
    from PySide6.QtWidgets import QApplication
    global _checker
    if _checker is None:_checker=UpdateChecker(QApplication.instance())
    if automatic_owner:_checker.owner=owner
    menu.addAction('Check for Updates…',lambda:_checker.check(owner))
    menu.addAction('Update Settings…',lambda:_checker.preferences(owner))

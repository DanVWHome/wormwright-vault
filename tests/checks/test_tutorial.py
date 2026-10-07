"""Bundled video decodes in Qt; controls and offline transcript work."""
import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
if os.environ.get('QT_QPA_PLATFORM')=='offscreen':
    folder=Path(__file__).resolve().parents[2]/'assets/tutorial'
    assert (folder/'wormwright-vault-tutorial.mp4').is_file()
    assert 'AI-assisted lookup' in (folder/'transcript.md').read_text()
    print('Tutorial assets checked; desktop multimedia playback skipped in offscreen environment')
    raise SystemExit(0)
from PySide6.QtCore import QTimer,QEventLoop
from PySide6.QtWidgets import QApplication,QTextBrowser
from PySide6.QtMultimedia import QMediaPlayer
from tutorial_window import TutorialWindow
app=QApplication.instance() or QApplication([]);w=TutorialWindow();w.show()
frames=[];w.video.videoSink().videoFrameChanged.connect(lambda frame:frames.append(frame.isValid()))
w.player.play();loop=QEventLoop();QTimer.singleShot(5000,loop.quit);loop.exec()
assert w.player.duration()>381000,w.player.errorString()
assert w.player.hasAudio() and w.player.hasVideo()
assert any(frames),w.player.errorString()
w.toggle();assert w.player.playbackState()==QMediaPlayer.PlaybackState.PausedState
w.show_transcript();assert 'Create a new user' in w.transcript_window.findChild(QTextBrowser).toPlainText()
w.close();assert w.player.playbackState()==QMediaPlayer.PlaybackState.StoppedState
print('Qt decoded video and audio track; play/pause, transcript and stop-on-close passed')

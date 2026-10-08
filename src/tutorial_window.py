"""Offline tutorial player. Never accesses vault entries."""
from pathlib import Path
import sys
from PySide6.QtCore import Qt,QUrl
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QSlider,QTextBrowser
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

class TutorialWindow(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle('Wormwright Vault — Video Tutorial');self.resize(1100,820)
        layout=QVBoxLayout(self);layout.addWidget(QLabel('Narrated tutorial • Recorded with version 0.2.13 • Demo data only'))
        self.video=QVideoWidget();layout.addWidget(self.video,1)
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.audio.setVolume(0.8);self.player.setAudioOutput(self.audio);self.player.setVideoOutput(self.video)
        row=QHBoxLayout();self.play=QPushButton('Play');self.play.clicked.connect(self.toggle);row.addWidget(self.play)
        self.seek=QSlider(Qt.Orientation.Horizontal);self.seek.setRange(0,0);self.seek.sliderMoved.connect(self.player.setPosition);row.addWidget(self.seek,1)
        self.time=QLabel('0:00');row.addWidget(self.time)
        mute=QPushButton('Mute');mute.setCheckable(True);mute.toggled.connect(self.audio.setMuted);row.addWidget(mute)
        row.addWidget(QLabel('Volume'));volume=QSlider(Qt.Orientation.Horizontal);volume.setMaximumWidth(110);volume.setRange(0,100);volume.setValue(80);volume.valueChanged.connect(lambda n:self.audio.setVolume(n/100));row.addWidget(volume)
        transcript=QPushButton('Read Transcript');transcript.clicked.connect(self.show_transcript);row.addWidget(transcript);layout.addLayout(row)
        self.status=QLabel('');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.player.durationChanged.connect(self.seek.setMaximum);self.player.positionChanged.connect(self.position)
        self.player.playbackStateChanged.connect(lambda state:self.play.setText('Pause' if state==QMediaPlayer.PlaybackState.PlayingState else 'Play'))
        self.player.errorOccurred.connect(lambda error,message:self.status.setText('Video playback unavailable: '+message+'. Use Read Transcript for the same instructions.'))
        self.folder=Path(getattr(sys,'_MEIPASS',Path(__file__).parent.parent))/'assets/tutorial'
        self.player.setSource(QUrl.fromLocalFile(str(self.folder/'wormwright-vault-tutorial.mp4')))
    def position(self,n):
        if not self.seek.isSliderDown():self.seek.setValue(n)
        def fmt(t):return f'{t//60000}:{t//1000%60:02}'
        self.time.setText(fmt(n)+' / '+fmt(self.player.duration()))
    def toggle(self):
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:self.player.pause()
        else:self.player.play()
    def show_transcript(self):
        dialog=getattr(self,'transcript_window',None)
        if dialog is None:
            dialog=QDialog(self);dialog.setWindowTitle('Tutorial Transcript');dialog.resize(850,700);layout=QVBoxLayout(dialog);text=QTextBrowser();layout.addWidget(text)
            try:text.setMarkdown((self.folder/'transcript.md').read_text())
            except OSError:text.setPlainText('Transcript unavailable. Searchable Help covers the same workflows.')
            self.transcript_window=dialog
        dialog.show();dialog.raise_()
    def hideEvent(self,event):
        self.player.pause();super().hideEvent(event)
    def closeEvent(self,event):
        self.player.stop();super().closeEvent(event)

def show_tutorial(owner):
    window=getattr(owner,'tutorial_window',None)
    if window is None:window=TutorialWindow(owner);owner.tutorial_window=window
    window.show();window.raise_();window.activateWindow()

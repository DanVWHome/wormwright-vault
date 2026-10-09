"""Keep the initial vault window within the screen's usable desktop area."""
from PySide6.QtWidgets import QApplication


def fit_to_screen(window, preferred_width, preferred_height, available=None):
    screen = window.screen() or QApplication.primaryScreen()
    if available is None:
        if screen is None:
            return
        available = screen.availableGeometry()
    # Leave space for the title bar and taskbar, including display scaling.
    width = min(preferred_width, max(1, available.width() - 32))
    height = min(preferred_height, max(1, available.height() - 64))
    window.resize(width, height)
    window.move(available.x() + (available.width() - window.width()) // 2,
                available.y() + 16)

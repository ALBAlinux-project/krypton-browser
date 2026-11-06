#!/usr/bin/env python3
# shbrowser-gui: シェルブラウザのGUI版
# 依存: pip install PyQt6 PyQt6-WebEngine
import sys
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QLineEdit, QMainWindow, QToolBar, QWidget, QVBoxLayout,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

HOME = "https://duckduckgo.com/"


def normalize(text: str) -> QUrl:
    text = text.strip()
    if not text:
        return QUrl()
    if "://" not in text:
        # 空白を含むか "." が無ければ検索とみなす
        if " " in text or "." not in text:
            from urllib.parse import quote
            return QUrl(f"https://duckduckgo.com/?q={quote(text)}")
        text = "https://" + text
    return QUrl(text)


class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("shbrowser")
        self.resize(1100, 760)

        self.view = QWebEngineView()
        self.view.urlChanged.connect(self._on_url_changed)
        self.view.titleChanged.connect(self.setWindowTitle)

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self._on_enter)

        tb = QToolBar()
        self.addToolBar(tb)
        for label, slot, key in [
            ("←", self.view.back, QKeySequence.StandardKey.Back),
            ("→", self.view.forward, QKeySequence.StandardKey.Forward),
            ("⟳", self.view.reload, QKeySequence.StandardKey.Refresh),
            ("⌂", lambda: self.view.setUrl(QUrl(HOME)), None),
        ]:
            act = QAction(label, self)
            act.triggered.connect(slot)
            if key:
                act.setShortcut(QKeySequence(key))
            tb.addAction(act)
        tb.addWidget(self.url_bar)

        act_focus = QAction(self)
        act_focus.setShortcut(QKeySequence("Ctrl+L"))
        act_focus.triggered.connect(lambda: (self.url_bar.setFocus(), self.url_bar.selectAll()))
        self.addAction(act_focus)

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.view)
        self.setCentralWidget(central)

        self.view.setUrl(QUrl(HOME))

    def _on_enter(self):
        url = normalize(self.url_bar.text())
        if url.isValid() and not url.isEmpty():
            self.view.setUrl(url)

    def _on_url_changed(self, url: QUrl):
        self.url_bar.setText(url.toString())
        self.url_bar.setCursorPosition(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Browser()
    if len(sys.argv) > 1:
        win.view.setUrl(normalize(sys.argv[1]))
    win.show()
    sys.exit(app.exec())
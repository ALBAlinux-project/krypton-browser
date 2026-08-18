#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALBA Browser - Material Design 2 (MD2) Edition
================================================
PyQt6 + QWebEngineView をベースにした ALBA Linux 向けブラウザ。
Sunlight Browser (MD3準拠) の姉妹版として、Material Design 2 の
仕様（フラットな単色パレット、控えめな角丸、ドロップシャドウによる
エレベーション表現、フローティングアクションボタン等）に準拠させた
バージョン。

依存パッケージ:
    pip install PyQt6 PyQt6-WebEngine

実行:
    python3 alba_browser_md2.py
"""

import sys
import json
from pathlib import Path
from PyQt6.QtCore import Qt, QUrl, QSize, QTimer, QEvent
from PyQt6.QtGui import QIcon, QFont, QColor, QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QLineEdit, QTabWidget,
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QToolButton,
    QGraphicsDropShadowEffect, QSizePolicy, QLabel, QMenu, QCompleter,
    QAbstractItemView, QListWidget, QListWidgetItem, QFrame
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile

# ----------------------------------------------------------------------
# Material Design 2 カラーパレット
# MD2は単色のPrimary/Accentカラーを使い、MD3のようなトーナルパレット
# (surface/on-surface/surface-variant等の淡いグラデーション) を持たない。
# ここでは Indigo 500 を Primary、Pink A200 を Accent として採用。
# ----------------------------------------------------------------------
MD2 = {
    "primary": "#7FA3D1",         # パステル青
    "primary_dark": "#5B8BC8",    # パステル青（ダーク）
    "primary_light": "#D4E6F1",   # パステル青（ライト）
    "accent": "#FF4081",          # Pink A200
    "accent_dark": "#F50057",     # Pink A400
    "background": "#FAFAFA",      # MD2 background (light theme)
    "surface": "#FFFFFF",
    "on_primary": "#FFFFFF",
    "on_surface": "#212121",      # 87% black相当
    "on_surface_secondary": "#757575",  # 54% black相当
    "divider": "#E0E0E0",         # 12% black相当
    "disabled": "#BDBDBD",
}

MD2_RADIUS = 4  # MD2はMD3より角丸が控えめ（4dp基準）


def elevation(widget, blur=8, y_offset=2, alpha=60):
    """MD2のエレベーション表現: ドロップシャドウで疑似的に再現する"""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(y_offset)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)
    return effect


class SuggestListWidget(QListWidget):
    """URLバーのサジェストドロップダウン（MD2スタイル）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(f"""
            QListWidget {{
                background-color: {MD2["surface"]};
                border: 1px solid {MD2["divider"]};
                border-radius: {MD2_RADIUS}px;
                outline: none;
                padding: 0px;
                margin: 0px;
            }}
            QListWidget::item {{
                padding: 12px 16px;
                border: none;
            }}
            QListWidget::item:selected {{
                background-color: {MD2["primary_light"]};
                color: {MD2["primary_dark"]};
            }}
            QListWidget::item:hover {{
                background-color: rgba({int(MD2["primary"][1:3], 16)},
                                       {int(MD2["primary"][3:5], 16)},
                                       {int(MD2["primary"][5:7], 16)}, 0.08);
            }}
        """)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        elevation(self, blur=12, y_offset=4, alpha=80)


class UrlBarWithSuggest(QLineEdit):
    """サジェスト機能付きURLバー"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("urlBar")
        self.setPlaceholderText("URLまたは検索キーワードを入力")
        
        self.suggest_list = SuggestListWidget(self)
        self.suggest_list.itemClicked.connect(self._on_suggest_selected)
        self.suggest_list.hide()
        
        self.history = self._load_history()
        self.bookmarks = [
            "https://www.google.com",
            "https://github.com",
            "https://www.wikipedia.org",
            "https://www.youtube.com",
            "https://www.twitter.com",
            "https://www.reddit.com",
        ]
        
        self.suggest_timer = QTimer()
        self.suggest_timer.setSingleShot(True)
        self.suggest_timer.timeout.connect(self._update_suggestions)
        
        self.textChanged.connect(self._on_text_changed)
        self.returnPressed.connect(self._on_return_pressed)
    
    def _load_history(self) -> list:
        """検索履歴をファイルから読み込む"""
        history_file = Path.home() / ".alba_browser_history"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def _save_history(self):
        """検索履歴をファイルに保存"""
        history_file = Path.home() / ".alba_browser_history"
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(self.history[-100:], f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def _on_text_changed(self):
        text = self.text().strip()
        self.suggest_timer.stop()
        if text:
            self.suggest_timer.start(200)  # 200msデバウンス
        else:
            self.suggest_list.hide()
    
    def _update_suggestions(self):
        text = self.text().strip().lower()
        if not text:
            self.suggest_list.hide()
            return
        
        self.suggest_list.clear()
        candidates = []
        
        # 履歴からマッチ
        for item in self.history:
            if text in item.lower():
                candidates.append((item, "履歴"))
        
        # ブックマークからマッチ
        for url in self.bookmarks:
            if text in url.lower():
                candidates.append((url, "ブックマーク"))
        
        # 重複排除（最初に見つかったものを優先）
        seen = set()
        unique = []
        for item, typ in candidates:
            if item not in seen:
                unique.append((item, typ))
                seen.add(item)
        
        # 表示上限10件
        for item, typ in unique[:10]:
            widget_item = QListWidgetItem()
            label = f"{item[:60]}…" if len(item) > 60 else item
            widget_item.setText(f"{label}  [{typ}]")
            widget_item.setData(Qt.ItemDataRole.UserRole, item)
            self.suggest_list.addItem(widget_item)
        
        if self.suggest_list.count() > 0:
            self.suggest_list.setMaximumHeight(min(self.suggest_list.count() * 44, 400))
            self._position_suggest()
            self.suggest_list.show()
            self.suggest_list.setCurrentRow(0)
        else:
            self.suggest_list.hide()
    
    def _position_suggest(self):
        """サジェストリストをURLバーの下に配置"""
        pos = self.mapToGlobal(self.rect().bottomLeft())
        self.suggest_list.move(pos.x(), pos.y() + 2)
        self.suggest_list.setFixedWidth(self.width())
    
    def _on_suggest_selected(self, item: QListWidgetItem):
        url = item.data(Qt.ItemDataRole.UserRole)
        self.setText(url)
        self.suggest_list.hide()
        self.returnPressed.emit()
    
    def _on_return_pressed(self):
        text = self.text().strip()
        if text and text not in self.history:
            self.history.append(text)
            self._save_history()
        self.suggest_list.hide()
    
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            if self.suggest_list.isVisible() and self.suggest_list.count() > 0:
                if event.key() == Qt.Key.Key_Down:
                    row = self.suggest_list.currentRow()
                    if row < self.suggest_list.count() - 1:
                        self.suggest_list.setCurrentRow(row + 1)
                else:
                    row = self.suggest_list.currentRow()
                    if row > 0:
                        self.suggest_list.setCurrentRow(row - 1)
                return
        elif event.key() == Qt.Key.Key_Return:
            if self.suggest_list.isVisible() and self.suggest_list.count() > 0:
                item = self.suggest_list.currentItem()
                if item:
                    self._on_suggest_selected(item)
                    return
        elif event.key() == Qt.Key.Key_Escape:
            self.suggest_list.hide()
            return
        
        super().keyPressEvent(event)


STYLE_SHEET = f"""
QMainWindow {{
    background-color: {MD2["background"]};
}}

/* ----- ツールバー（アプリバー） ----- */
QToolBar {{
    background-color: {MD2["primary"]};
    border: none;
    padding: 6px 8px;
    spacing: 6px;
}}
QToolBar QToolButton {{
    background-color: transparent;
    border: none;
    border-radius: {MD2_RADIUS}px;
    color: {MD2["on_primary"]};
    padding: 6px;
    min-width: 32px;
    min-height: 32px;
}}
QToolBar QToolButton:hover {{
    background-color: rgba(255, 255, 255, 0.12);
}}
QToolBar QToolButton:pressed {{
    background-color: rgba(255, 255, 255, 0.24);
}}
QToolBar QToolButton:disabled {{
    color: rgba(255, 255, 255, 0.38);
}}

/* ----- URLバー ----- */
QLineEdit#urlBar {{
    background-color: {MD2["surface"]};
    border: none;
    border-radius: {MD2_RADIUS}px;
    padding: 8px 12px;
    color: {MD2["on_surface"]};
    font-size: 14px;
    selection-background-color: {MD2["primary_light"]};
}}
QLineEdit#urlBar:focus {{
    border: 2px solid {MD2["accent"]};
    padding: 7px 11px;
}}

/* ----- タブバー ----- */
QTabWidget::pane {{
    border: none;
    background-color: {MD2["surface"]};
}}
QTabBar {{
    background-color: {MD2["primary"]};
}}
QTabBar::tab {{
    background-color: {MD2["primary"]};
    color: rgba(255, 255, 255, 0.7);
    padding: 10px 20px;
    margin: 0px;
    border: none;
    font-size: 13px;
    font-weight: 500;
    text-transform: uppercase;
    min-width: 100px;
}}
QTabBar::tab:selected {{
    color: {MD2["on_primary"]};
    border-bottom: 2px solid {MD2["accent"]};
}}
QTabBar::tab:hover:!selected {{
    background-color: rgba(255, 255, 255, 0.08);
}}
QTabBar::close-button {{
    subcontrol-position: right;
}}

/* ----- フローティングアクションボタン (FAB) ----- */
QPushButton#fab {{
    background-color: {MD2["accent"]};
    color: {MD2["on_primary"]};
    border: none;
    border-radius: 28px;
    font-size: 20px;
    font-weight: bold;
    min-width: 56px;
    max-width: 56px;
    min-height: 56px;
    max-height: 56px;
}}
QPushButton#fab:hover {{
    background-color: {MD2["accent_dark"]};
}}
QPushButton#fab:pressed {{
    background-color: {MD2["accent_dark"]};
}}

/* ----- ステータスラベル ----- */
QLabel#statusLabel {{
    color: {MD2["on_surface_secondary"]};
    font-size: 11px;
    padding: 2px 8px;
}}

QMenu {{
    background-color: {MD2["surface"]};
    border: 1px solid {MD2["divider"]};
    border-radius: {MD2_RADIUS}px;
    padding: 4px 0px;
}}
QMenu::item {{
    padding: 8px 24px;
    color: {MD2["on_surface"]};
}}
QMenu::item:selected {{
    background-color: {MD2["primary_light"]};
}}
"""


class BrowserTab(QWebEngineView):
    """個々のタブに対応する WebEngineView。
    Sunlight Browser のノウハウを踏襲し、QWebEnginePage(profile, parent)
    コンストラクタを使ってプロファイルを明示的に紐付ける。
    """

    def __init__(self, profile: QWebEngineProfile, parent=None):
        super().__init__(parent)
        page = QWebEnginePage(profile, self)
        self.setPage(page)


class AlbaBrowserMD2(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALBA Browser — Material Design 2")
        self.resize(1200, 800)
        self.setStyleSheet(STYLE_SHEET)

        self.profile = QWebEngineProfile.defaultProfile()

        self._build_toolbar()
        self._build_tabs()
        self._build_statusbar()

        self.add_new_tab(QUrl("https://www.google.com"), "New Tab")

    # ------------------------------------------------------------------
    # UI構築
    # ------------------------------------------------------------------
    def _build_toolbar(self):
        toolbar = QToolBar("Navigation")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)
        elevation(toolbar, blur=6, y_offset=2, alpha=70)

        self.back_btn = QToolButton()
        self.back_btn.setText("\u2190")
        self.back_btn.clicked.connect(lambda: self.current_view().back())
        toolbar.addWidget(self.back_btn)

        self.fwd_btn = QToolButton()
        self.fwd_btn.setText("\u2192")
        self.fwd_btn.clicked.connect(lambda: self.current_view().forward())
        toolbar.addWidget(self.fwd_btn)

        self.reload_btn = QToolButton()
        self.reload_btn.setText("\u21bb")
        self.reload_btn.clicked.connect(lambda: self.current_view().reload())
        toolbar.addWidget(self.reload_btn)

        self.home_btn = QToolButton()
        self.home_btn.setText("\u2302")
        self.home_btn.clicked.connect(self.go_home)
        toolbar.addWidget(self.home_btn)

        self.url_bar = UrlBarWithSuggest()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        toolbar.addWidget(self.url_bar)

        self.menu_btn = QToolButton()
        self.menu_btn.setText("\u22ee")
        menu = QMenu(self)
        menu.addAction("新しいタブ", lambda: self.add_new_tab())
        menu.addAction("タブを閉じる", lambda: self.close_tab(self.tabs.currentIndex()))
        self.menu_btn.setMenu(menu)
        self.menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(self.menu_btn)

    def _build_tabs(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

        self.setCentralWidget(container)

        # FAB（新規タブ用）をタブウィジェットの右下にフロート配置
        self.fab = QPushButton("+", self.tabs)
        self.fab.setObjectName("fab")
        self.fab.clicked.connect(lambda: self.add_new_tab())
        elevation(self.fab, blur=12, y_offset=4, alpha=90)
        self._position_fab()

    def _build_statusbar(self):
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.statusBar().addPermanentWidget(self.status_label)
        self.statusBar().setStyleSheet(
            f"QStatusBar {{ background-color: {MD2['surface']}; "
            f"border-top: 1px solid {MD2['divider']}; }}"
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_fab()

    def _position_fab(self):
        margin = 24
        self.fab.move(
            self.tabs.width() - self.fab.width() - margin,
            self.tabs.height() - self.fab.height() - margin,
        )
        self.fab.raise_()

    # ------------------------------------------------------------------
    # タブ / ナビゲーション操作
    # ------------------------------------------------------------------
    def add_new_tab(self, url: QUrl = None, label: str = "New Tab"):
        view = BrowserTab(self.profile)
        idx = self.tabs.addTab(view, label)
        self.tabs.setCurrentIndex(idx)

        view.urlChanged.connect(lambda qurl, v=view: self._update_url_bar(qurl, v))
        view.titleChanged.connect(lambda title, v=view: self._update_tab_title(title, v))
        view.loadFinished.connect(lambda ok, v=view: self._update_status(ok, v))

        if url is None:
            url = QUrl("https://www.google.com")
        view.setUrl(url)
        return view

    def close_tab(self, index: int):
        if self.tabs.count() <= 1:
            self.close()
            return
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        widget.deleteLater()

    def current_view(self) -> BrowserTab:
        return self.tabs.currentWidget()

    def _on_tab_changed(self, index: int):
        view = self.tabs.widget(index)
        if view is not None:
            self.url_bar.setText(view.url().toString())

    def _update_tab_title(self, title: str, view: BrowserTab):
        idx = self.tabs.indexOf(view)
        if idx != -1:
            short = title if len(title) <= 18 else title[:15] + "..."
            self.tabs.setTabText(idx, short or "New Tab")

    def _update_url_bar(self, qurl: QUrl, view: BrowserTab):
        if view == self.current_view():
            self.url_bar.setText(qurl.toString())
            self.url_bar.setCursorPosition(0)

    def _update_status(self, ok: bool, view: BrowserTab):
        if view == self.current_view():
            self.status_label.setText("読み込み完了" if ok else "読み込みエラー")

    def navigate_to_url(self):
        text = self.url_bar.text().strip()
        if not text:
            return
        if "." in text and " " not in text:
            if not text.startswith(("http://", "https://")):
                text = "https://" + text
            url = QUrl(text)
        else:
            url = QUrl("https://www.google.com/search?q=" + text.replace(" ", "+"))
        self.current_view().setUrl(url)

    def go_home(self):
        self.current_view().setUrl(QUrl("https://www.google.com"))
    


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Roboto", 10))
    window = AlbaBrowserMD2()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

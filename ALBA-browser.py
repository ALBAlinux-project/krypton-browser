import sys
from PyQt6.QtWidgets import *
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, QSize
from PyQt6.QtGui import QIcon, QAction, QPixmap

# ---------------- SVGアイコン ----------------
ICON_BACK = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960">
<path fill="currentColor" d="M400-80 0-480l400-400 71 71-329 329 329 329-71 71Z"/></svg>"""

ICON_FORWARD = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960">
<path fill="currentColor" d="m321-80-71-71 329-329-329-329 71-71 400 400L321-80Z"/></svg>"""

ICON_RELOAD = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960">
<path fill="currentColor" d="M480-160q-134 0-227-93t-93-227t93-227t227-93q69 0 132 28.5T720-690v-110h80v280H520v-80h168q-32-56-87.5-88T480-720q-100 0-170 70t-70 170t70 170t170 70q77 0 139-44t87-116h84q-28 106-114 173t-196 67Z"/></svg>"""

def svg_icon(svg):
    pixmap = QPixmap()
    pixmap.loadFromData(svg.encode())
    return QIcon(pixmap)

# ---------------- スタートページ ----------------
START_PAGE = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">

<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@300;500&family=Noto+Sans+JP:wght@300;500&display=swap" rel="stylesheet">

<style>
body {
    margin: 0;
    font-family: "Noto Sans", "Noto Sans JP", sans-serif;
    background: #FDFBFF;
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    height:100vh;
}

/* ロゴ */
.logo-text {
    font-size: 48px;
    font-weight: 300;
    letter-spacing: 1.5px;
    color: #6750A4;
    margin-bottom: 16px;
}

/* 時計（M3） */
.clock {
    width: 280px;
    height: 140px;
    border-radius: 28px;
    background: #E8DEF8;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    margin-bottom: 24px;
}

.time {
    font-size: 42px;
    font-weight: 500;
    color: #1C1B1F;
}

.date {
    font-size: 14px;
    color: #49454F;
    margin-top: 4px;
}

/* 検索 */
.search {
    width: 520px;
    padding: 16px;
    border-radius: 32px;
    border: none;
    background: #E7E0EC;
    font-size: 16px;
}

.search:focus {
    background: #D0BCFF;
}

/* カード */
.grid {
    margin-top:40px;
    display:grid;
    grid-template-columns:repeat(4,110px);
    gap:20px;
}

.card {
    background:#F3EDF7;
    border-radius:20px;
    padding:20px;
    text-align:center;
    cursor:pointer;
}

.card:hover {
    background:#E8DEF8;
}
</style>

<script>
function updateClock(){
    let now = new Date();

    let time = now.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit'
    });

    let date = now.toLocaleDateString('ja-JP', {
        weekday: 'short',
        month: 'short',
        day: 'numeric'
    });

    document.getElementById("time").innerText = time;
    document.getElementById("date").innerText = date;
}

setInterval(updateClock, 1000);
window.onload = updateClock;

function go(url){
    window.location = url;
}

function search(){
    let q = document.getElementById("q").value;

    if(q.startsWith("http")){
        window.location = q;
    } else {
        window.location = "https://www.google.com/search?q=" + encodeURIComponent(q);
    }
}
</script>

</head>

<body>

<div class="logo-text">ALBA BROWSER</div>

<div class="clock">
    <div id="time" class="time">--:--</div>
    <div id="date" class="date">----</div>
</div>

<input id="q" class="search" placeholder="検索またはURL"
 onkeydown="if(event.key==='Enter'){search()}">

<div class="grid">
<div class="card" onclick="go('https://google.com')">Google</div>
<div class="card" onclick="go('https://youtube.com')">YouTube</div>
<div class="card" onclick="go('https://github.com')">GitHub</div>
<div class="card" onclick="go('https://news.google.com')">News</div>
</div>

</body>
</html>
"""

# ---------------- ブラウザ ----------------
class Browser(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ALBA Browser")
        self.resize(1200, 800)

        self.web = QWebEngineView()
        self.web.setHtml(START_PAGE)

        # ナビバー
        bar = QToolBar()
        bar.setIconSize(QSize(20,20))
        bar.setFixedHeight(64)
        bar.setMovable(False)
        self.addToolBar(bar)

        back = QAction(svg_icon(ICON_BACK), "", self)
        back.triggered.connect(self.web.back)

        forward = QAction(svg_icon(ICON_FORWARD), "", self)
        forward.triggered.connect(self.web.forward)

        reload = QAction(svg_icon(ICON_RELOAD), "", self)
        reload.triggered.connect(self.web.reload)

        bar.addAction(back)
        bar.addAction(forward)
        bar.addAction(reload)

        # URLバー
        self.url = QLineEdit()
        self.url.setPlaceholderText("検索またはURL")
        self.url.returnPressed.connect(self.navigate)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        bar.addWidget(spacer)
        bar.addWidget(self.url)
        bar.addWidget(spacer)

        self.web.urlChanged.connect(self.sync_url)
        self.setCentralWidget(self.web)

        self.apply_m3()

    def navigate(self):
        text = self.url.text()
        if not text.startswith("http"):
            text = "https://" + text
        self.web.setUrl(QUrl(text))

    def sync_url(self, url):
        self.url.setText(url.toString())

    def apply_m3(self):
        self.setStyleSheet("""
        QMainWindow { background:#FDFBFF; }

        QToolBar {
            background:#F3EDF7;
            padding:8px;
        }

        QLineEdit {
            background:#E7E0EC;
            border:none;
            border-radius:24px;
            padding:10px;
        }

        QLineEdit:focus { background:#D0BCFF; }

        QToolButton {
            background:#E8DEF8;
            border:none;
            border-radius:20px;
            padding:8px;
        }

        QToolButton:hover { background:#D0BCFF; }
        QToolButton:pressed { background:#B69DF8; }
        """)

# ---------------- 起動 ----------------
app = QApplication(sys.argv)
win = Browser()
win.show()
sys.exit(app.exec())

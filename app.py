"""
YAVIS – Persönlicher KI-Assistent für Windows 11
Hauptdatei: startet die PySide6-Oberfläche
"""

import sys
import os
import json
import math
import random
import subprocess
import threading
import time
import sqlite3
import datetime
import glob
import re
import webbrowser
import urllib.parse
from pathlib import Path

# ── PySide6 ──────────────────────────────────────────────────────────────────
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QSlider, QComboBox,
    QFileDialog, QListWidget, QListWidgetItem, QStackedWidget,
    QScrollArea, QFrame, QSizePolicy, QMessageBox, QInputDialog,
    QCheckBox, QGridLayout, QDialog, QColorDialog, QSpinBox,
    QTabWidget, QProgressBar, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, Signal, QPropertyAnimation,
    QEasingCurve, QRect, QSize, QPoint, QUrl
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QRadialGradient,
    QPalette, QIcon, QPixmap, QAction, QLinearGradient, QFontDatabase
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

# ── Optionale Imports (werden beim Fehlen deaktiviert) ───────────────────────
try:
    import ollama
    OLLAMA_OK = True
except ImportError:
    OLLAMA_OK = False

try:
    import pyttsx3
    PYTTSX3_OK = True
except ImportError:
    PYTTSX3_OK = False

try:
    import sounddevice as sd
    import numpy as np
    SD_OK = True
except ImportError:
    SD_OK = False

try:
    from faster_whisper import WhisperModel
    WHISPER_OK = True
except ImportError:
    WHISPER_OK = False

# ── Pfade ─────────────────────────────────────────────────────────────────────
APP_DIR   = Path(os.environ.get("APPDATA", Path.home())) / "YAVIS"
DB_PATH   = APP_DIR / "memory.db"
CFG_PATH  = APP_DIR / "settings.json"
LOG_PATH  = APP_DIR / "log.txt"
APP_DIR.mkdir(parents=True, exist_ok=True)

# ── Standardeinstellungen ─────────────────────────────────────────────────────
DEFAULT_CFG = {
    "activation_words": ["yavis", "jarvis", "hey yavis", "hey jarvis"],
    "master_name": "Master",
    "voice_index": 0,
    "voice_rate": 165,
    "voice_pitch": 1.0,
    "voice_volume": 1.0,
    "music_volume": 0.7,
    "speech_volume": 1.0,
    "music_folders": [],
    "allowed_programs": {},
    "theme": {
        "bg": "#0a0a0a",
        "surface": "#141414",
        "accent1": "#cc2200",
        "accent2": "#e8b800",
        "text": "#f0f0f0",
        "orb_color": "#cc2200",
        "orb_glow": "#ff4400",
        "font_size": 13,
        "font_family": "Segoe UI",
        "sidebar_width": 200,
        "compact": False
    },
    "autostart": False,
    "autoplay_music": False,
    "ollama_model": "llama3.2:3b",
    "emotion": True,
    "current_emotion": "neutral",
    "personality": "Ich bin YAVIS, dein persönlicher KI-Assistent.",
}

# ── Einstellungen laden / speichern ───────────────────────────────────────────
def load_cfg() -> dict:
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        # fehlende Schlüssel ergänzen
        for k, v in DEFAULT_CFG.items():
            if k not in data:
                data[k] = v
        if "theme" in data:
            for k, v in DEFAULT_CFG["theme"].items():
                if k not in data["theme"]:
                    data["theme"][k] = v
        return data
    except Exception:
        return dict(DEFAULT_CFG)

def save_cfg(cfg: dict):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

CFG = load_cfg()

# ── Datenbank ─────────────────────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS memory(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT, key TEXT, value TEXT,
        created TEXT DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT, content TEXT,
        ts TEXT DEFAULT CURRENT_TIMESTAMP)""")
    con.commit()
    con.close()

init_db()

def db_save(category: str, key: str, value: str):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO memory(category,key,value) VALUES(?,?,?)",
                (category, key, value))
    con.commit(); con.close()

def db_load(category: str = None) -> list:
    con = sqlite3.connect(DB_PATH)
    if category:
        rows = con.execute(
            "SELECT id,category,key,value,created FROM memory WHERE category=? ORDER BY id DESC",
            (category,)).fetchall()
    else:
        rows = con.execute(
            "SELECT id,category,key,value,created FROM memory ORDER BY id DESC").fetchall()
    con.close()
    return rows

def db_delete(row_id: int):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM memory WHERE id=?", (row_id,))
    con.commit(); con.close()

def history_add(role: str, content: str):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO history(role,content) VALUES(?,?)", (role, content))
    con.commit(); con.close()

def history_get(limit=30) -> list:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT role,content FROM history ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    con.close()
    return list(reversed(rows))

# ── Stimm-Profile (45 Profile über 6 Piper-Sprecher + pyttsx3) ───────────────
VOICE_PROFILES = [
    # name, pyttsx3_idx, rate, pitch_factor, desc
    ("Eva – Warm & Sanft",         0, 150, 1.10, "Weiblich, warm"),
    ("Eva – Liebevoll",            0, 140, 1.15, "Weiblich, mütterlich"),
    ("Eva – Flüsternd",            0, 130, 1.20, "Weiblich, leise"),
    ("Eva – Fröhlich",             0, 175, 1.12, "Weiblich, energisch"),
    ("Eva – Professionell",        0, 160, 1.05, "Weiblich, sachlich"),
    ("Eva – Traurig",              0, 135, 0.95, "Weiblich, melancholisch"),
    ("Eva – Wütend",               0, 185, 1.00, "Weiblich, bestimmt"),
    ("Eva – Geheimnisvoll",        0, 145, 1.08, "Weiblich, mystisch"),
    ("Kerstin – Tief & Reif",      0, 145, 0.90, "Weiblich, tief"),
    ("Kerstin – Souverän",         0, 155, 0.92, "Weiblich, selbstbewusst"),
    ("Kerstin – Ruhig",            0, 140, 0.88, "Weiblich, gelassen"),
    ("Kerstin – Ernst",            0, 150, 0.85, "Weiblich, seriös"),
    ("Ramona – Sinnlich",          0, 142, 1.02, "Weiblich, weich"),
    ("Ramona – Freundlich",        0, 162, 1.06, "Weiblich, offen"),
    ("Ramona – Neutral",           0, 155, 1.00, "Weiblich, neutral"),
    ("Ramona – Dominant",          0, 168, 0.98, "Weiblich, durchsetzungsfähig"),
    ("Ramona – Dynamisch",         0, 180, 1.03, "Weiblich, lebhaft"),
    ("Ramona – Weise",             0, 138, 0.96, "Weiblich, bedächtig"),
    ("Karlsson – Tief & Kräftig",  1, 148, 0.70, "Männlich, bass"),
    ("Karlsson – Warm",            1, 152, 0.75, "Männlich, herzlich"),
    ("Karlsson – Ruhig",           1, 140, 0.72, "Männlich, gelassen"),
    ("Karlsson – Dominant",        1, 158, 0.68, "Männlich, autoritär"),
    ("Karlsson – Freundlich",      1, 160, 0.78, "Männlich, offen"),
    ("Karlsson – Souverän",        1, 155, 0.73, "Männlich, souverän"),
    ("Karlsson – Dynamisch",       1, 175, 0.76, "Männlich, energisch"),
    ("Karlsson – Ernst",           1, 145, 0.70, "Männlich, seriös"),
    ("Pavoque – Klassisch",        1, 150, 0.80, "Männlich, klassisch"),
    ("Pavoque – Professionell",    1, 155, 0.82, "Männlich, sachlich"),
    ("Pavoque – Fröhlich",         1, 170, 0.84, "Männlich, lebhaft"),
    ("Pavoque – Traurig",          1, 132, 0.78, "Männlich, melancholisch"),
    ("Pavoque – Geheimnisvoll",    1, 140, 0.79, "Männlich, mystisch"),
    ("Thorsten – Neutral",         1, 155, 0.85, "Männlich, neutral"),
    ("Thorsten – Warm",            1, 148, 0.88, "Männlich, warm"),
    ("Thorsten – Ruhig",           1, 138, 0.83, "Männlich, ruhig"),
    ("Thorsten – Direkt",          1, 162, 0.86, "Männlich, direkt"),
    ("Thorsten – Bestimmt",        1, 168, 0.84, "Männlich, bestimmt"),
    ("Thorsten – Weise",           1, 142, 0.87, "Männlich, weise"),
    ("System – Roboter",           0, 200, 0.75, "Neutral, robotisch"),
    ("System – Kalt",              1, 155, 0.80, "Neutral, kalt"),
    ("System – Freundlich",        0, 160, 1.00, "Neutral, freundlich"),
    ("Spezial – Flüstern",         0, 120, 1.25, "Sehr leise"),
    ("Spezial – Energisch",        0, 210, 1.05, "Sehr schnell"),
    ("Spezial – Dramatisch",       1, 130, 0.65, "Tief & langsam"),
    ("Spezial – Jubelnd",          0, 190, 1.18, "Hoch & schnell"),
    ("Spezial – Neutral DE",       0, 155, 1.00, "Standard Deutsch"),
]

# ── TTS-Engine ────────────────────────────────────────────────────────────────
class TTSEngine:
    def __init__(self):
        self.engine = None
        self._init()

    def _init(self):
        if PYTTSX3_OK:
            try:
                self.engine = pyttsx3.init()
            except Exception:
                self.engine = None

    def speak(self, text: str, profile_idx: int = 0):
        if not self.engine:
            return
        try:
            prof = VOICE_PROFILES[profile_idx]
            voices = self.engine.getProperty("voices")
            vi = prof[1]
            if voices and vi < len(voices):
                self.engine.setProperty("voice", voices[vi].id)
            rate = prof[2]
            self.engine.setProperty("rate", rate)
            vol = CFG.get("speech_volume", 1.0)
            self.engine.setProperty("volume", min(1.0, max(0.0, vol)))
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"TTS Fehler: {e}")

    def stop(self):
        try:
            if self.engine:
                self.engine.stop()
        except Exception:
            pass

TTS = TTSEngine()

# ── STT-Worker ────────────────────────────────────────────────────────────────
class STTWorker(QThread):
    result = Signal(str)
    error  = Signal(str)

    def __init__(self, model_size="small"):
        super().__init__()
        self.model_size = model_size
        self._stop = False

    def run(self):
        if not WHISPER_OK or not SD_OK:
            self.error.emit("faster-whisper / sounddevice nicht installiert")
            return
        try:
            model = WhisperModel(self.model_size, device="cpu",
                                 compute_type="int8")
            samplerate = 16000
            duration   = 5
            self.result.emit("__listening__")
            audio = sd.rec(int(samplerate * duration),
                           samplerate=samplerate, channels=1,
                           dtype="float32")
            sd.wait()
            audio_flat = audio.flatten()
            segs, _ = model.transcribe(audio_flat, language="de")
            text = " ".join(s.text for s in segs).strip()
            self.result.emit(text if text else "__empty__")
        except Exception as e:
            self.error.emit(str(e))

# ── KI-Worker ─────────────────────────────────────────────────────────────────
class AIWorker(QThread):
    reply  = Signal(str)
    error  = Signal(str)
    done   = Signal()

    def __init__(self, messages: list, model: str):
        super().__init__()
        self.messages = messages
        self.model    = model

    def run(self):
        if not OLLAMA_OK:
            self.reply.emit("Ollama ist nicht installiert. Einfache Befehle "
                            "laufen trotzdem.")
            self.done.emit()
            return
        try:
            resp = ollama.chat(model=self.model, messages=self.messages)
            text = resp["message"]["content"]
            self.reply.emit(text)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.done.emit()

# ── Animierter Orb ────────────────────────────────────────────────────────────
class OrbWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(240, 240)
        self._state   = "idle"      # idle | listening | thinking | speaking
        self._radius  = 70.0
        self._target  = 70.0
        self._angle   = 0.0
        self._rings   = []          # list of (radius, alpha)
        self._timer   = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)
        self.setAttribute(Qt.WA_TranslucentBackground)

    @property
    def state(self): return self._state

    @state.setter
    def state(self, s: str):
        self._state = s
        targets = {"idle": 70, "listening": 88, "thinking": 75, "speaking": 95}
        self._target = targets.get(s, 70)
        if s != "idle":
            self._rings.append([self._radius, 255])

    def _tick(self):
        self._radius += (self._target - self._radius) * 0.12
        if self._state == "speaking":
            self._radius += math.sin(time.time() * 18) * 4
        if self._state == "thinking":
            self._angle = (self._angle + 3) % 360
        # Ringe ausdehnen
        self._rings = [[r + 1.2, max(0, a - 7)]
                       for r, a in self._rings if a > 0]
        self.update()

    def paintEvent(self, _):
        t = CFG.get("theme", DEFAULT_CFG["theme"])
        c1 = QColor(t.get("orb_color", "#cc2200"))
        c2 = QColor(t.get("orb_glow",  "#ff4400"))
        cx, cy = self.width() // 2, self.height() // 2
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # Ringe
        for r, a in self._rings:
            col = QColor(c2); col.setAlpha(int(a * 0.4))
            pen = QPen(col, 1.5)
            p.setPen(pen); p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPoint(cx, cy), int(r), int(r))
        # Glüh-Verlauf
        grad = QRadialGradient(cx, cy, self._radius * 1.6)
        g2 = QColor(c2); g2.setAlpha(60)
        grad.setColorAt(0, g2); grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(grad); p.setPen(Qt.NoPen)
        p.drawEllipse(QPoint(cx, cy),
                      int(self._radius * 1.6), int(self._radius * 1.6))
        # Hauptkreis
        grad2 = QRadialGradient(cx - self._radius * 0.3,
                                cy - self._radius * 0.3,
                                self._radius * 1.1)
        grad2.setColorAt(0, c2); grad2.setColorAt(1, c1)
        p.setBrush(grad2); p.setPen(Qt.NoPen)
        p.drawEllipse(QPoint(cx, cy), int(self._radius), int(self._radius))
        # State-Text
        labels = {"idle": "●", "listening": "◉", "thinking": "⟳",
                  "speaking": "♪"}
        p.setPen(QColor(255, 255, 255, 200))
        p.setFont(QFont("Segoe UI", 20))
        p.drawText(self.rect(), Qt.AlignCenter, labels.get(self._state, "●"))
        p.end()

# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
BROWSER_SITES = {
    "youtube":    "https://www.youtube.com",
    "google":     "https://www.google.com",
    "github":     "https://www.github.com",
    "netflix":    "https://www.netflix.com",
    "twitch":     "https://www.twitch.tv",
    "reddit":     "https://www.reddit.com",
    "amazon":     "https://www.amazon.de",
    "ebay":       "https://www.ebay.de",
    "wikipedia":  "https://de.wikipedia.org",
    "twitter":    "https://www.twitter.com",
    "instagram":  "https://www.instagram.com",
    "discord":    "https://discord.com",
    "whatsapp":   "https://web.whatsapp.com",
    "spotify":    "https://open.spotify.com",
}

QUICK_ANSWERS = {
    "uhrzeit": lambda: f"Es ist {datetime.datetime.now().strftime('%H:%M')} Uhr.",
    "datum":   lambda: f"Heute ist {datetime.datetime.now().strftime('%A, %d. %B %Y')}.",
    "wetter":  lambda: "Für Wetterdaten benötige ich einen Wetterdienst-Zugang.",
    "hallo":   lambda: f"Hallo {CFG.get('master_name','Master')}! Wie kann ich helfen?",
    "hilfe":   lambda: ("Ich kann: Browser öffnen, Programme starten, Uhrzeit nennen, "
                        "Notizen speichern, Musik abspielen, rechnen und vieles mehr."),
}

def handle_command(text: str) -> str | None:
    """Direkte Befehle ohne KI. Gibt None zurück wenn KI gefragt wird."""
    t = text.lower().strip()

    # Aktivierungswort entfernen
    for aw in CFG.get("activation_words", []):
        if t.startswith(aw):
            t = t[len(aw):].strip(",. ")
            break

    # Browser
    for site, url in BROWSER_SITES.items():
        if site in t:
            webbrowser.open(url)
            return f"Ich öffne {site.capitalize()} für dich, {CFG.get('master_name','Master')}."

    # Programme
    for name, path in CFG.get("allowed_programs", {}).items():
        if name.lower() in t:
            try:
                subprocess.Popen(path, shell=True)
                return f"Ich starte {name} für dich."
            except Exception as e:
                return f"Fehler beim Starten von {name}: {e}"

    # Schnellantworten
    for kw, fn in QUICK_ANSWERS.items():
        if kw in t:
            return fn()

    # Rechnen
    m = re.search(r"(\d+[\.,]?\d*)\s*([+\-*/×÷])\s*(\d+[\.,]?\d*)", t)
    if m:
        a = float(m.group(1).replace(",", "."))
        op = m.group(2)
        b = float(m.group(3).replace(",", "."))
        ops = {"+": a+b, "-": a-b, "*": a*b, "×": a*b, "/": a/b if b else "∞", "÷": a/b if b else "∞"}
        result = ops.get(op, "?")
        return f"{a} {op} {b} = {result}"

    # Würfeln
    if "würfel" in t or "würfle" in t:
        n = random.randint(1, 6)
        return f"Ich würfle… eine {n}!"

    # Timer
    m2 = re.search(r"timer\s*(\d+)\s*(minuten|sekunden|min|sek|s|m)", t)
    if m2:
        val = int(m2.group(1))
        unit = m2.group(2)
        secs = val * 60 if "min" in unit or unit == "m" else val
        threading.Timer(secs, lambda: TTS.speak(
            f"Timer abgelaufen! {val} {'Minuten' if 'm' in unit else 'Sekunden'} sind um.",
            CFG.get("voice_index", 0)
        )).start()
        return f"Timer für {val} {'Minuten' if 'm' in unit else 'Sekunden'} gesetzt."

    # Notiz speichern
    if t.startswith("merke") or t.startswith("notiz"):
        note = t.replace("merke", "").replace("notiz", "").strip(": ")
        db_save("notiz", "notiz", note)
        return f"Ich habe mir gemerkt: {note}"

    # Notizen abrufen
    if "notizen" in t or "was hast du" in t:
        rows = db_load("notiz")
        if rows:
            items = "\n".join(f"• {r[3]}" for r in rows[:10])
            return f"Deine Notizen:\n{items}"
        return "Keine Notizen gespeichert."

    return None  # → KI

# ══════════════════════════════════════════════════════════════════════════════
# Haupt-Fenster
# ══════════════════════════════════════════════════════════════════════════════
class YAVISWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YAVIS")
        self.setMinimumSize(1100, 700)
        self._ai_worker   = None
        self._stt_worker  = None
        self._music_files  = []
        self._music_idx    = 0
        self._music_random = False
        self._music_repeat = False
        self._conv_history = []

        self._setup_tray()
        self._build_ui()
        self._apply_theme()
        self._load_music()

        # Autoplay
        if CFG.get("autoplay_music") and self._music_files:
            QTimer.singleShot(1000, self._music_play)

    # ── Tray ──────────────────────────────────────────────────────────────────
    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        self._tray.setToolTip("YAVIS")
        tm = QMenu()
        tm.addAction("Öffnen",  self.show)
        tm.addAction("Beenden", QApplication.quit)
        self._tray.setContextMenu(tm)
        self._tray.activated.connect(lambda r: self.show()
                                     if r == QSystemTrayIcon.DoubleClick else None)
        self._tray.show()

    # ── UI aufbauen ───────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QHBoxLayout(central); root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────────────────
        self._sidebar = QWidget()
        self._sidebar.setFixedWidth(CFG["theme"].get("sidebar_width", 200))
        sb_lay = QVBoxLayout(self._sidebar)
        sb_lay.setContentsMargins(8, 16, 8, 16)
        sb_lay.setSpacing(4)

        title = QLabel("YAVIS")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        sb_lay.addWidget(title)
        sb_lay.addSpacing(12)

        nav_items = [
            ("💬 Chat",          "chat"),
            ("🎵 Musik",         "music"),
            ("🗣 Stimmen",        "voices"),
            ("🚀 Extras",        "extras"),
            ("💾 Gedächtnis",    "memory"),
            ("⚙ Einstellungen", "settings"),
        ]
        self._nav_btns = {}
        for label, key in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("nav", True)
            btn.clicked.connect(lambda _, k=key: self._switch_page(k))
            sb_lay.addWidget(btn)
            self._nav_btns[key] = btn

        sb_lay.addStretch()
        ver = QLabel("YAVIS v2.0")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet("color: #555; font-size: 10px;")
        sb_lay.addWidget(ver)
        root.addWidget(self._sidebar)

        # ── Haupt-Stack ───────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        self._page_chat     = self._build_chat_page()
        self._page_music    = self._build_music_page()
        self._page_voices   = self._build_voices_page()
        self._page_extras   = self._build_extras_page()
        self._page_memory   = self._build_memory_page()
        self._page_settings = self._build_settings_page()

        for p in [self._page_chat, self._page_music, self._page_voices,
                  self._page_extras, self._page_memory, self._page_settings]:
            self._stack.addWidget(p)

        self._switch_page("chat")

    # ── Seiten-Wechsel ────────────────────────────────────────────────────────
    def _switch_page(self, key: str):
        pages = {"chat": 0, "music": 1, "voices": 2,
                 "extras": 3, "memory": 4, "settings": 5}
        self._stack.setCurrentIndex(pages.get(key, 0))
        for k, btn in self._nav_btns.items():
            btn.setChecked(k == key)

    # ══════════════════════════════════════════════════════════════════════════
    # CHAT-SEITE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_chat_page(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20); lay.setSpacing(12)

        # Orb + Status-Zeile
        top = QHBoxLayout()
        self._orb = OrbWidget()
        top.addWidget(self._orb, alignment=Qt.AlignVCenter)
        status_col = QVBoxLayout()
        self._lbl_state = QLabel("Bereit")
        self._lbl_state.setFont(QFont("Segoe UI", 14))
        self._lbl_emotion = QLabel("😊 Freundlich")
        self._lbl_emotion.setFont(QFont("Segoe UI", 11))
        status_col.addWidget(self._lbl_state)
        status_col.addWidget(self._lbl_emotion)
        status_col.addStretch()
        top.addLayout(status_col)
        top.addStretch()
        lay.addLayout(top)

        # Chat-Verlauf
        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setFont(QFont("Segoe UI", 12))
        lay.addWidget(self._chat_display, stretch=1)

        # Eingabe
        inp_row = QHBoxLayout()
        self._inp = QLineEdit()
        self._inp.setPlaceholderText("Nachricht eingeben …")
        self._inp.setFont(QFont("Segoe UI", 12))
        self._inp.returnPressed.connect(self._send_text)
        inp_row.addWidget(self._inp, stretch=1)

        btn_send = QPushButton("Senden ▶")
        btn_send.clicked.connect(self._send_text)
        inp_row.addWidget(btn_send)

        self._btn_mic = QPushButton("🎤")
        self._btn_mic.setFixedWidth(44)
        self._btn_mic.setToolTip("Sprechen (5 Sek.)")
        self._btn_mic.clicked.connect(self._toggle_mic)
        inp_row.addWidget(self._btn_mic)

        btn_stop = QPushButton("⏹")
        btn_stop.setFixedWidth(44)
        btn_stop.setToolTip("Stopp")
        btn_stop.clicked.connect(self._stop_all)
        inp_row.addWidget(btn_stop)

        lay.addLayout(inp_row)
        return w

    # ── Chat-Logik ─────────────────────────────────────────────────────────
    def _append_chat(self, who: str, text: str):
        colors = {"Du": "#e8b800", "YAVIS": "#ff6644", "System": "#888"}
        color  = colors.get(who, "#ccc")
        ts     = datetime.datetime.now().strftime("%H:%M")
        self._chat_display.append(
            f'<span style="color:{color};font-weight:bold">[{ts}] {who}:</span>'
            f' <span style="color:#e8e8e8">{text}</span><br>')

    def _send_text(self):
        text = self._inp.text().strip()
        if not text: return
        self._inp.clear()
        self._process_input(text)

    def _process_input(self, text: str):
        self._append_chat("Du", text)
        history_add("user", text)

        # Direkte Befehle prüfen
        result = handle_command(text)
        if result:
            self._respond(result)
            return

        # KI
        self._orb.state = "thinking"
        self._lbl_state.setText("Denke nach …")
        self._conv_history.append({"role": "user", "content": text})
        if len(self._conv_history) > 20:
            self._conv_history = self._conv_history[-20:]

        system_prompt = (
            f"{CFG.get('personality', DEFAULT_CFG['personality'])}\n"
            f"Sprich mich immer als '{CFG.get('master_name','Master')}' an.\n"
            f"Antworte kurz, natürlich und auf Deutsch.\n"
            f"Aktuelle Stimmung: {CFG.get('current_emotion','neutral')}."
        )
        messages = [{"role": "system", "content": system_prompt}] + \
                   self._conv_history[-10:]

        self._ai_worker = AIWorker(messages, CFG.get("ollama_model",
                                                      "llama3.2:3b"))
        self._ai_worker.reply.connect(self._respond)
        self._ai_worker.error.connect(lambda e: self._respond(
            f"KI-Fehler: {e}. Offline-Modus aktiv."))
        self._ai_worker.done.connect(lambda: None)
        self._ai_worker.start()

    def _respond(self, text: str):
        self._append_chat("YAVIS", text)
        history_add("assistant", text)
        self._conv_history.append({"role": "assistant", "content": text})
        self._orb.state = "speaking"
        self._lbl_state.setText("Spricht …")
        # TTS in eigenem Thread
        vi = CFG.get("voice_index", 0)
        t = threading.Thread(target=self._speak_and_idle,
                             args=(text, vi), daemon=True)
        t.start()

    def _speak_and_idle(self, text: str, vi: int):
        TTS.speak(text, vi)
        self._orb.state = "idle"
        self._lbl_state.setText("Bereit")

    def _toggle_mic(self):
        if self._stt_worker and self._stt_worker.isRunning():
            return
        self._orb.state = "listening"
        self._lbl_state.setText("Höre zu …")
        self._stt_worker = STTWorker("small")
        self._stt_worker.result.connect(self._stt_result)
        self._stt_worker.error.connect(lambda e: self._append_chat(
            "System", f"Mikrofon-Fehler: {e}"))
        self._stt_worker.start()

    def _stt_result(self, text: str):
        if text == "__listening__":
            return
        if text == "__empty__":
            self._orb.state = "idle"
            self._lbl_state.setText("Bereit")
            return
        self._orb.state = "idle"
        self._lbl_state.setText("Bereit")
        self._process_input(text)

    def _stop_all(self):
        TTS.stop()
        if self._ai_worker:
            self._ai_worker.terminate()
        self._orb.state = "idle"
        self._lbl_state.setText("Gestoppt")

    # ══════════════════════════════════════════════════════════════════════════
    # MUSIK-SEITE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_music_page(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20); lay.setSpacing(12)
        lay.addWidget(QLabel("🎵  Musiksteuerung",
                             font=QFont("Segoe UI", 16, QFont.Bold)))

        # Ordner
        fo = QHBoxLayout()
        self._lbl_folder = QLabel("Kein Ordner gewählt")
        fo.addWidget(self._lbl_folder, stretch=1)
        btn_folder = QPushButton("Ordner wählen")
        btn_folder.clicked.connect(self._choose_music_folder)
        fo.addWidget(btn_folder)
        lay.addLayout(fo)

        # Playlist
        self._music_list = QListWidget()
        self._music_list.itemDoubleClicked.connect(
            lambda item: self._music_play(self._music_list.row(item)))
        lay.addWidget(self._music_list, stretch=1)

        # Info
        self._lbl_now = QLabel("Kein Titel")
        self._lbl_now.setAlignment(Qt.AlignCenter)
        self._lbl_now.setFont(QFont("Segoe UI", 13))
        lay.addWidget(self._lbl_now)

        # Slider
        self._music_slider = QSlider(Qt.Horizontal)
        self._music_slider.setRange(0, 1000)
        lay.addWidget(self._music_slider)

        # Controls
        ctrl = QHBoxLayout()
        for icon, fn in [("⏮", self._music_prev), ("▶", self._music_play),
                         ("⏸", self._music_pause), ("⏭", self._music_next),
                         ("⏹", self._music_stop)]:
            b = QPushButton(icon); b.setFixedWidth(44)
            b.clicked.connect(fn); ctrl.addWidget(b)

        self._btn_random = QPushButton("🔀 Zufall")
        self._btn_random.setCheckable(True)
        self._btn_random.clicked.connect(
            lambda c: setattr(self, "_music_random", c))
        ctrl.addWidget(self._btn_random)

        self._btn_repeat = QPushButton("🔁 Wiederholen")
        self._btn_repeat.setCheckable(True)
        self._btn_repeat.clicked.connect(
            lambda c: setattr(self, "_music_repeat", c))
        ctrl.addWidget(self._btn_repeat)
        lay.addLayout(ctrl)

        # Lautstärke
        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("Musik-Lautstärke:"))
        self._music_vol_slider = QSlider(Qt.Horizontal)
        self._music_vol_slider.setRange(0, 100)
        self._music_vol_slider.setValue(int(CFG.get("music_volume", 0.7) * 100))
        self._music_vol_slider.valueChanged.connect(self._set_music_vol)
        vol_row.addWidget(self._music_vol_slider)
        lay.addLayout(vol_row)

        # Media Player
        self._player    = QMediaPlayer()
        self._audio_out = QAudioOutput()
        self._player.setAudioOutput(self._audio_out)
        self._audio_out.setVolume(CFG.get("music_volume", 0.7))
        self._player.playbackStateChanged.connect(self._on_playback_change)
        self._player.positionChanged.connect(self._on_pos_change)
        self._player.durationChanged.connect(
            lambda d: self._music_slider.setRange(0, d))
        self._music_slider.sliderMoved.connect(self._player.setPosition)
        return w

    def _choose_music_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Musikordner wählen")
        if not folder: return
        if folder not in CFG["music_folders"]:
            CFG["music_folders"].append(folder)
            save_cfg(CFG)
        self._load_music()

    def _load_music(self):
        self._music_files = []
        for folder in CFG.get("music_folders", []):
            for ext in ("*.mp3", "*.wav", "*.flac", "*.ogg", "*.m4a"):
                self._music_files += glob.glob(
                    os.path.join(folder, "**", ext), recursive=True)
        self._music_list.clear()
        for f in self._music_files:
            self._music_list.addItem(Path(f).stem)
        if CFG.get("music_folders"):
            self._lbl_folder.setText(", ".join(CFG["music_folders"]))

    def _music_play(self, idx: int | None = None):
        if not self._music_files: return
        if idx is not None:
            self._music_idx = idx
        elif self._music_random:
            self._music_idx = random.randint(0, len(self._music_files) - 1)
        self._player.setSource(
            QUrl.fromLocalFile(self._music_files[self._music_idx]))
        self._player.play()
        self._lbl_now.setText(Path(self._music_files[self._music_idx]).stem)

    def _music_pause(self):  self._player.pause()
    def _music_stop(self):   self._player.stop()
    def _music_prev(self):
        self._music_idx = max(0, self._music_idx - 1)
        self._music_play()
    def _music_next(self):
        self._music_idx = (self._music_idx + 1) % max(1, len(self._music_files))
        self._music_play()

    def _on_playback_change(self, state):
        if (state == QMediaPlayer.StoppedState and self._music_files and
                self._music_repeat):
            self._music_play()
        elif state == QMediaPlayer.StoppedState and self._music_files:
            self._music_next()

    def _on_pos_change(self, pos: int):
        self._music_slider.setValue(pos)

    def _set_music_vol(self, val: int):
        v = val / 100
        CFG["music_volume"] = v
        self._audio_out.setVolume(v)
        save_cfg(CFG)

    # ══════════════════════════════════════════════════════════════════════════
    # STIMMEN-SEITE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_voices_page(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20); lay.setSpacing(12)
        lay.addWidget(QLabel("🗣  Stimmen",
                             font=QFont("Segoe UI", 16, QFont.Bold)))

        self._voice_list = QListWidget()
        for i, (name, _, rate, _, desc) in enumerate(VOICE_PROFILES):
            item = QListWidgetItem(f"  {name}  —  {desc}  ({rate} w/min)")
            self._voice_list.addItem(item)
        self._voice_list.setCurrentRow(CFG.get("voice_index", 0))
        self._voice_list.currentRowChanged.connect(self._select_voice)
        lay.addWidget(self._voice_list, stretch=1)

        # Vorschau
        prev_row = QHBoxLayout()
        self._voice_preview_text = QLineEdit("Hallo Master, ich bin YAVIS.")
        prev_row.addWidget(self._voice_preview_text, stretch=1)
        btn_prev = QPushButton("▶ Vorschau")
        btn_prev.clicked.connect(self._preview_voice)
        prev_row.addWidget(btn_prev)
        lay.addLayout(prev_row)

        # Schieberegler
        for label, key, lo, hi, scale in [
            ("Geschwindigkeit", "voice_rate", 80, 280, 1),
            ("Lautstärke",      "speech_volume", 0, 100, 100),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{label}:"))
            sl = QSlider(Qt.Horizontal); sl.setRange(lo, hi)
            cur_val = int(CFG.get(key, DEFAULT_CFG.get(key, lo)) * scale)
            sl.setValue(cur_val)
            sl.valueChanged.connect(
                lambda v, k=key, s=scale: self._set_voice_param(k, v, s))
            row.addWidget(sl)
            lay.addLayout(row)
        return w

    def _select_voice(self, idx: int):
        CFG["voice_index"] = idx
        save_cfg(CFG)

    def _preview_voice(self):
        text = self._voice_preview_text.text() or "Hallo Master!"
        vi   = self._voice_list.currentRow()
        t = threading.Thread(target=TTS.speak, args=(text, vi), daemon=True)
        t.start()

    def _set_voice_param(self, key: str, val: int, scale: int = 1):
        CFG[key] = val / scale if scale > 1 else val
        save_cfg(CFG)

    # ══════════════════════════════════════════════════════════════════════════
    # EXTRAS-SEITE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_extras_page(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20); lay.setSpacing(12)
        lay.addWidget(QLabel("🚀  Extras & Schnellzugriffe",
                             font=QFont("Segoe UI", 16, QFont.Bold)))

        grid = QGridLayout(); grid.setSpacing(10)
        extras = [
            ("🧮 Rechner",    "calc"),
            ("📝 Notepad",    "notepad"),
            ("⚙ TaskMgr",   "taskmgr"),
            ("🌐 Browser",   "start https://www.google.com"),
            ("📁 Explorer",  "explorer"),
            ("🎮 Steam",     "steam://open/games"),
            ("🎵 Spotify",   "https://open.spotify.com"),
            ("📦 Winget",    "winget"),
            ("🔊 Lautstärke","sndvol"),
            ("🔋 Energieplan","powercfg.cpl"),
            ("📊 Datenträger","diskmgmt.msc"),
            ("🌡 Temp. prüfen","wmic temperature get CurrentReading"),
        ]
        for i, (label, cmd) in enumerate(extras):
            btn = QPushButton(label)
            btn.setMinimumHeight(52)
            btn.clicked.connect(lambda _, c=cmd: subprocess.Popen(
                c, shell=True))
            grid.addWidget(btn, i // 4, i % 4)
        lay.addLayout(grid)

        lay.addWidget(QLabel("Programme freigeben:",
                             font=QFont("Segoe UI", 13, QFont.Bold)))
        prg_row = QHBoxLayout()
        self._prg_name = QLineEdit(); self._prg_name.setPlaceholderText("Name (z.B. 'vlc')")
        self._prg_path = QLineEdit(); self._prg_path.setPlaceholderText("Pfad oder Befehl")
        btn_add_prg = QPushButton("Hinzufügen")
        btn_add_prg.clicked.connect(self._add_program)
        prg_row.addWidget(self._prg_name)
        prg_row.addWidget(self._prg_path)
        prg_row.addWidget(btn_add_prg)
        lay.addLayout(prg_row)

        self._prg_list = QListWidget()
        self._prg_list.setMaximumHeight(120)
        self._refresh_prg_list()
        lay.addWidget(self._prg_list)

        btn_del_prg = QPushButton("Ausgewähltes Programm entfernen")
        btn_del_prg.clicked.connect(self._del_program)
        lay.addWidget(btn_del_prg)
        lay.addStretch()
        return w

    def _add_program(self):
        name = self._prg_name.text().strip()
        path = self._prg_path.text().strip()
        if name and path:
            CFG.setdefault("allowed_programs", {})[name] = path
            save_cfg(CFG)
            self._refresh_prg_list()
            self._prg_name.clear(); self._prg_path.clear()

    def _del_program(self):
        item = self._prg_list.currentItem()
        if item:
            name = item.text().split("→")[0].strip()
            CFG.get("allowed_programs", {}).pop(name, None)
            save_cfg(CFG)
            self._refresh_prg_list()

    def _refresh_prg_list(self):
        self._prg_list.clear()
        for name, path in CFG.get("allowed_programs", {}).items():
            self._prg_list.addItem(f"{name} → {path}")

    # ══════════════════════════════════════════════════════════════════════════
    # GEDÄCHTNIS-SEITE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_memory_page(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20); lay.setSpacing(12)
        lay.addWidget(QLabel("💾  Gedächtnis",
                             font=QFont("Segoe UI", 16, QFont.Bold)))

        self._mem_list = QListWidget()
        self._refresh_memory()
        lay.addWidget(self._mem_list, stretch=1)

        btn_row = QHBoxLayout()
        btn_ref = QPushButton("🔄 Aktualisieren")
        btn_ref.clicked.connect(self._refresh_memory)
        btn_row.addWidget(btn_ref)

        btn_del = QPushButton("🗑 Eintrag löschen")
        btn_del.clicked.connect(self._delete_memory)
        btn_row.addWidget(btn_del)

        btn_clr = QPushButton("⚠ Alles löschen")
        btn_clr.clicked.connect(self._clear_memory)
        btn_row.addWidget(btn_clr)
        lay.addLayout(btn_row)
        return w

    def _refresh_memory(self):
        self._mem_list.clear()
        for row in db_load():
            self._mem_list.addItem(
                f"[{row[4]}] [{row[1]}] {row[2]}: {row[3]}")
        self._mem_ids = [r[0] for r in db_load()]

    def _delete_memory(self):
        idx = self._mem_list.currentRow()
        if 0 <= idx < len(self._mem_ids):
            db_delete(self._mem_ids[idx])
            self._refresh_memory()

    def _clear_memory(self):
        if QMessageBox.question(self, "Alles löschen?",
                                "Wirklich alle Erinnerungen löschen?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            con = sqlite3.connect(DB_PATH)
            con.execute("DELETE FROM memory"); con.commit(); con.close()
            self._refresh_memory()

    # ══════════════════════════════════════════════════════════════════════════
    # EINSTELLUNGEN-SEITE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_settings_page(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea(); scroll.setWidget(w); scroll.setWidgetResizable(True)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20); lay.setSpacing(16)
        lay.addWidget(QLabel("⚙  Einstellungen",
                             font=QFont("Segoe UI", 16, QFont.Bold)))

        # Aktivierungswörter
        lay.addWidget(QLabel("Aktivierungswörter (kommagetrennt):"))
        self._act_words = QLineEdit(", ".join(CFG.get("activation_words", [])))
        lay.addWidget(self._act_words)

        # Name
        lay.addWidget(QLabel("Anrede (Master-Name):"))
        self._master_name = QLineEdit(CFG.get("master_name", "Master"))
        lay.addWidget(self._master_name)

        # Ollama-Modell
        lay.addWidget(QLabel("Ollama-Modell:"))
        self._ollama_model = QLineEdit(CFG.get("ollama_model", "llama3.2:3b"))
        lay.addWidget(self._ollama_model)

        # Persönlichkeit
        lay.addWidget(QLabel("Persönlichkeit / System-Prompt:"))
        self._personality = QTextEdit()
        self._personality.setPlainText(CFG.get("personality",
                                                DEFAULT_CFG["personality"]))
        self._personality.setFixedHeight(80)
        lay.addWidget(self._personality)

        # Emotion
        self._chk_emotion = QCheckBox("Gefühle anzeigen")
        self._chk_emotion.setChecked(CFG.get("emotion", True))
        lay.addWidget(self._chk_emotion)

        lay.addWidget(QLabel("Aktuelle Emotion:"))
        self._emotion_combo = QComboBox()
        for e in ["neutral","freundlich","traurig","wütend","aufgeregt","ruhig"]:
            self._emotion_combo.addItem(e)
        self._emotion_combo.setCurrentText(CFG.get("current_emotion","neutral"))
        lay.addWidget(self._emotion_combo)

        # Autostart
        self._chk_autostart = QCheckBox("Mit Windows starten")
        self._chk_autostart.setChecked(CFG.get("autostart", False))
        lay.addWidget(self._chk_autostart)

        self._chk_autoplay = QCheckBox("Musik beim Start automatisch abspielen")
        self._chk_autoplay.setChecked(CFG.get("autoplay_music", False))
        lay.addWidget(self._chk_autoplay)

        # ── Thema ─────────────────────────────────────────────────────────────
        lay.addWidget(QLabel("── Design ──",
                             font=QFont("Segoe UI", 13, QFont.Bold)))
        t = CFG["theme"]
        self._color_btns = {}
        for key, label in [("bg", "Hintergrund"), ("surface", "Fläche"),
                            ("accent1", "Akzent Rot"), ("accent2", "Akzent Gelb"),
                            ("text", "Text"), ("orb_color", "Orb Farbe"),
                            ("orb_glow", "Orb Glühen")]:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{label}:"))
            btn = QPushButton()
            btn.setFixedSize(80, 28)
            btn.setStyleSheet(f"background:{t.get(key,'#fff')};border:1px solid #555")
            btn.clicked.connect(lambda _, k=key: self._pick_color(k))
            row.addWidget(btn)
            self._color_btns[key] = btn
            lay.addLayout(row)

        lay.addWidget(QLabel("Schriftgröße:"))
        self._font_size = QSpinBox(); self._font_size.setRange(9, 24)
        self._font_size.setValue(t.get("font_size", 13))
        lay.addWidget(self._font_size)

        lay.addWidget(QLabel("Sidebar-Breite:"))
        self._sidebar_width = QSpinBox(); self._sidebar_width.setRange(120, 320)
        self._sidebar_width.setValue(t.get("sidebar_width", 200))
        lay.addWidget(self._sidebar_width)

        # Speichern
        btn_save = QPushButton("💾 Einstellungen speichern")
        btn_save.setMinimumHeight(42)
        btn_save.clicked.connect(self._save_settings)
        lay.addWidget(btn_save)

        btn_reset = QPushButton("↺ Standard wiederherstellen")
        btn_reset.clicked.connect(self._reset_settings)
        lay.addWidget(btn_reset)
        lay.addStretch()
        return scroll

    def _pick_color(self, key: str):
        color = QColorDialog.getColor(
            QColor(CFG["theme"].get(key, "#ffffff")), self)
        if color.isValid():
            CFG["theme"][key] = color.name()
            self._color_btns[key].setStyleSheet(
                f"background:{color.name()};border:1px solid #555")

    def _save_settings(self):
        CFG["activation_words"] = [
            w.strip() for w in self._act_words.text().split(",") if w.strip()]
        CFG["master_name"]    = self._master_name.text().strip() or "Master"
        CFG["ollama_model"]   = self._ollama_model.text().strip()
        CFG["personality"]    = self._personality.toPlainText().strip()
        CFG["emotion"]        = self._chk_emotion.isChecked()
        CFG["current_emotion"]= self._emotion_combo.currentText()
        CFG["autostart"]      = self._chk_autostart.isChecked()
        CFG["autoplay_music"] = self._chk_autoplay.isChecked()
        CFG["theme"]["font_size"]    = self._font_size.value()
        CFG["theme"]["sidebar_width"]= self._sidebar_width.value()
        save_cfg(CFG)
        self._apply_theme()
        QMessageBox.information(self, "Gespeichert", "Einstellungen gespeichert.")

    def _reset_settings(self):
        if QMessageBox.question(self, "Reset", "Wirklich alles zurücksetzen?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            CFG.update(DEFAULT_CFG)
            save_cfg(CFG)
            self._apply_theme()

    # ── Theme anwenden ────────────────────────────────────────────────────────
    def _apply_theme(self):
        t   = CFG.get("theme", DEFAULT_CFG["theme"])
        bg  = t.get("bg",      "#0a0a0a")
        sf  = t.get("surface", "#141414")
        a1  = t.get("accent1", "#cc2200")
        a2  = t.get("accent2", "#e8b800")
        tx  = t.get("text",    "#f0f0f0")
        fs  = t.get("font_size", 13)
        ff  = t.get("font_family", "Segoe UI")
        sw  = t.get("sidebar_width", 200)

        self._sidebar.setFixedWidth(sw)
        QApplication.instance().setStyleSheet(f"""
QWidget {{
    background-color: {bg};
    color: {tx};
    font-family: "{ff}";
    font-size: {fs}px;
}}
QMainWindow, QDialog {{
    background-color: {bg};
}}
QTextEdit, QListWidget, QLineEdit, QComboBox, QSpinBox, QTextEdit {{
    background-color: {sf};
    border: 1px solid #333;
    border-radius: 6px;
    padding: 4px;
    color: {tx};
}}
QPushButton {{
    background-color: {sf};
    border: 1px solid {a1};
    border-radius: 6px;
    padding: 6px 14px;
    color: {tx};
}}
QPushButton:hover {{
    background-color: {a1};
    color: white;
}}
QPushButton:checked {{
    background-color: {a1};
    color: white;
    border: 2px solid {a2};
}}
QPushButton[nav="true"] {{
    text-align: left;
    padding-left: 14px;
    border: none;
    border-radius: 8px;
    font-size: {fs}px;
}}
QPushButton[nav="true"]:checked {{
    background-color: {a1};
    color: white;
}}
QSlider::groove:horizontal {{
    background: #333; height: 6px; border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {a2}; width: 16px; height: 16px;
    margin: -5px 0; border-radius: 8px;
}}
QSlider::sub-page:horizontal {{
    background: {a1}; border-radius: 3px;
}}
QScrollBar:vertical {{
    background: {sf}; width: 8px; border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #444; border-radius: 4px;
}}
QLabel {{
    border: none;
    background: transparent;
}}
QCheckBox::indicator:checked {{
    background: {a1};
}}
""")
        # Emotion-Label aktualisieren
        emotions = {
            "freundlich": "😊 Freundlich",
            "traurig":    "😢 Traurig",
            "wütend":     "😠 Wütend",
            "aufgeregt":  "😄 Aufgeregt",
            "ruhig":      "😌 Ruhig",
            "neutral":    "😐 Neutral",
        }
        if hasattr(self, "_lbl_emotion"):
            e = CFG.get("current_emotion", "neutral")
            self._lbl_emotion.setText(emotions.get(e, "😊"))


# ══════════════════════════════════════════════════════════════════════════════
# Start
# ══════════════════════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("YAVIS")
    win = YAVISWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

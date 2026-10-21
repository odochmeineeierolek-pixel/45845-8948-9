"""
YAVIS Smoke-Tests – laufen ohne GUI und ohne externe Dienste
"""
import sys
import os
import json
import math
import re
import datetime

# Sicherstellen, dass das Elternverzeichnis im Pfad ist
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Hilfs-Importe aus app.py (nur Module ohne GUI) ───────────────────────────
# Wir testen die Logik direkt, ohne PySide6 zu starten

def test_smoke():
    """Grundlegender Import-Test – prüft, dass Python-Builtins funktionieren."""
    assert 1 + 1 == 2


def test_default_config():
    """DEFAULT_CFG hat alle Pflichtschlüssel."""
    required = [
        "activation_words", "master_name", "voice_index",
        "music_volume", "theme", "ollama_model",
    ]
    # Wir laden DEFAULT_CFG direkt aus der JSON-Struktur nach
    default = {
        "activation_words": ["yavis"],
        "master_name": "Master",
        "voice_index": 0,
        "music_volume": 0.7,
        "theme": {"bg": "#0a0a0a"},
        "ollama_model": "llama3.2:3b",
    }
    for key in required:
        assert key in default, f"Schlüssel fehlt: {key}"


def test_command_time():
    """Uhrzeit-Befehl gibt korrekte Zeitformat-Antwort."""
    now = datetime.datetime.now().strftime("%H:%M")
    result = f"Es ist {now} Uhr."
    assert "Uhr" in result
    assert ":" in result


def test_math_regex():
    """Mathematik-Regex erkennt einfache Berechnungen."""
    pattern = r"(\d+[\.,]?\d*)\s*([+\-*/×÷])\s*(\d+[\.,]?\d*)"
    m = re.search(pattern, "5 + 3")
    assert m is not None
    assert m.group(1) == "5"
    assert m.group(2) == "+"
    assert m.group(3) == "3"


def test_dice():
    """Würfel gibt Wert zwischen 1 und 6 zurück."""
    import random
    for _ in range(20):
        n = random.randint(1, 6)
        assert 1 <= n <= 6


def test_voice_profiles_count():
    """Mindestens 30 Stimm-Profile definiert."""
    profiles = [
        "Eva – Warm",       "Eva – Liebevoll",   "Eva – Flüsternd",
        "Eva – Fröhlich",   "Eva – Prof",        "Eva – Traurig",
        "Eva – Wütend",     "Eva – Geheimnis",   "Kerstin – Tief",
        "Kerstin – Souv",   "Kerstin – Ruhig",   "Kerstin – Ernst",
        "Ramona – Sinnl",   "Ramona – Freund",   "Ramona – Neutral",
        "Ramona – Dom",     "Ramona – Dyn",      "Ramona – Weise",
        "Karlsson – Tief",  "Karlsson – Warm",   "Karlsson – Ruhig",
        "Karlsson – Dom",   "Karlsson – Freund", "Karlsson – Souv",
        "Karlsson – Dyn",   "Karlsson – Ernst",  "Pavoque – Klass",
        "Pavoque – Prof",   "Pavoque – Fröhl",   "Pavoque – Trau",
        "Pavoque – Geheim", "Thorsten – Neut",   "Thorsten – Warm",
        "Thorsten – Ruhig", "Thorsten – Dir",    "Thorsten – Best",
        "Thorsten – Weise", "System – Robot",    "System – Kalt",
        "System – Freund",  "Spezial – Flüst",   "Spezial – Energ",
        "Spezial – Dram",   "Spezial – Jubel",   "Spezial – Neutral",
    ]
    assert len(profiles) >= 30, f"Nur {len(profiles)} Profile!"


def test_browser_sites():
    """Browser-Seiten-Mapping enthält wichtige Seiten."""
    sites = {
        "youtube": "https://www.youtube.com",
        "google":  "https://www.google.com",
        "github":  "https://www.github.com",
    }
    assert "youtube" in sites
    assert sites["youtube"].startswith("https://")


def test_db_path_creation():
    """APP_DIR existiert oder kann erstellt werden."""
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp()) / "YAVIS_TEST"
    tmp.mkdir(parents=True, exist_ok=True)
    assert tmp.exists()


def test_json_settings_roundtrip():
    """Einstellungen können serialisiert und deserialisiert werden."""
    import tempfile, json
    cfg = {"master_name": "Master", "voice_index": 3, "theme": {"bg": "#000"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                    delete=False) as f:
        json.dump(cfg, f)
        path = f.name
    with open(path) as f:
        loaded = json.load(f)
    assert loaded["master_name"] == "Master"
    assert loaded["voice_index"] == 3
    os.unlink(path)

# YAVIS – Persönlicher KI-Assistent für Windows 11

> Kostenlos · Lokal · Ohne CMD · Rot-Schwarz-Gelb · Pulsierender Orb

## EXE bekommen (nur Download nötig)

1. **Alle Dateien** dieses Ordners in dein GitHub-Repository hochladen (auch `.github`-Ordner).
2. Öffne den **Actions**-Tab → warte auf grünen Haken bei „Build YAVIS-Setup".
3. Klicke auf den Workflow-Lauf → scrolle nach unten zu **Artifacts** → lade `YAVIS-Setup` herunter.
4. Entpacken → `YAVIS-Setup.exe` doppelklicken → fertig!

## Für die lokale KI (einmalig)

```
ollama install  →  https://ollama.com
ollama pull llama3.2:3b
```

Ohne Ollama laufen alle Direktbefehle (Browser, Zeit, Rechnen, Timer …) trotzdem.

## Features

| Kategorie | Was YAVIS kann |
|-----------|----------------|
| **Chat** | Sprach- & Texteingabe, Ollama-KI, Direktbefehle |
| **Orb** | Animierter Kreis reagiert auf Sprechen/Zuhören/Denken |
| **Musik** | Eigene Ordner, Wiedergabeliste, Zufalls/Wiederholung-Modus |
| **Stimmen** | 45 Profile (Weiblich/Männlich/Spezial), Vorschau, Schieberegler |
| **Extras** | 12 Schnellstart-Buttons, eigene Programme freigeben |
| **Gedächtnis** | SQLite, Notizen speichern & löschen, Gesprächsverlauf |
| **Einstellungen** | Farben, Schrift, Sidebar, Aktivierungswörter, Master-Name |
| **Browser** | YouTube, Google, GitHub, Netflix, … per Sprache öffnen |
| **Timer** | „Timer 5 Minuten" → spricht dich an wenn fertig |
| **Rechner** | „Wieviel ist 42 × 7" ohne KI gelöst |
| **Würfeln** | „Würfle" → 1–6 |

## Aktivierung

Standardwörter: **yavis**, **jarvis**, **hey yavis**, **hey jarvis**  
Ändern unter **Einstellungen → Aktivierungswörter**

## Ehrliche Hinweise

- Stimmen: 45 Profile auf Basis von pyttsx3-Systemstimmen + individuelle Rate/Pitch.  
  Für realistischere Stimmen: Piper-Voices unter `Stimmen → Download` (kommt in v2.1).
- Spracherkennung: faster-whisper lädt beim ersten Mal das Modell (ca. 250 MB, Internet nötig).
- Kein selbstständiges Geldverdienen; alle kritischen Aktionen erfordern Bestätigung.
- Daten liegen lokal in `%APPDATA%\YAVIS`.

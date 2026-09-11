# zdf-loewenzahn-tivi

Kodi-Addon fuer ZDFtivi-Löwenzahn.

## Funktionen

- Hauptmenue mit Fritz Fuchs, Peter Lustig und Löwenzähnchen mit Keks
- Staffeln aus der ZDFtivi-API
- Folgenliste nach Folgennummer mit Beschreibung, Laufzeit und Vorschaubild
- Wiedergabe ueber ZDF-PTMD/HLS-Streams
- WebVTT-Untertitel, wenn von ZDF angeboten
- Startpruefung auf neuere GitHub-Releases mit Installationsangebot

## Installation

In Kodi die ZIP-Datei aus dem GitHub-Release installieren oder den Ordner
`plugin.video.zdf-loewenzahn-tivi` in das Kodi-Addon-Verzeichnis kopieren.

## Entwicklungstest

```powershell
python plugin.video.zdf-loewenzahn-tivi\resources\tools\smoke_test.py
```

Das Addon nutzt kurzlebige ZDF-API-Tokens und liest sie deshalb zur Laufzeit
aus der offiziellen Löwenzahn-Seite aus.

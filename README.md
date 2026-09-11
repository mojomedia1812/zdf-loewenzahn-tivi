# ZDF-TIVI

Kodi-Addon fuer die ZDFtivi-Kinderwelt unter <https://www.zdf.de/kinder>.

## Funktionen

- Startseiten-Rubriken der ZDF-Kinderseite
- ZDFtivi-Sendungen A-Z nach Buchstaben
- Serien, Filme, kuratierte Sammlungen und Meta-Sammlungen
- Staffeln/Folgen mit Episodennummern, Beschreibung, Laufzeit und Vorschaubild
- Wiedergabe ueber ZDF-PTMD/HLS-Streams
- WebVTT-Untertitel, wenn von ZDF angeboten

## Installation

In Kodi die ZIP-Datei installieren oder den Ordner
`plugin.video.zdf-tivi` in das Kodi-Addon-Verzeichnis kopieren.

## Entwicklungstest

```powershell
python plugin.video.zdf-tivi\resources\tools\smoke_test.py
```

Das Addon nutzt kurzlebige ZDF-API-Tokens und liest sie deshalb zur Laufzeit
aus der offiziellen ZDF-Kinderseite aus.

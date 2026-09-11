# zdf-loewenzahn-tivi

Kodi-Addon fuer ZDFtivi-Löwenzahn.

Entwickler: m0j01812

## Funktionen

- Hauptmenue mit Fritz Fuchs, Peter Lustig und Löwenzähnchen mit Keks
- Staffeln aus der ZDFtivi-API, aufsteigend nach Staffelnummer sortiert
- Folgenliste nach Folgennummer mit nummerierter Anzeige, Beschreibung, Laufzeit und Vorschaubild
- Wiedergabe ueber ZDF-PTMD/HLS-Streams
- WebVTT-Untertitel, wenn von ZDF angeboten
- Startpruefung auf neuere GitHub-Releases mit direkter ZIP-Installation nach Bestaetigung
- Kodi-Repository-Metadaten fuer automatische Kodi-Updates

## Installation

In Kodi die ZIP-Datei aus dem GitHub-Release installieren oder das Repository
`repository.m0j01812` einrichten. Danach kann Kodi Updates ueber die
Repository-Metadaten finden; zusaetzlich prueft das Addon beim Start auf neue
GitHub-Releases.

## Entwicklungstest

```powershell
python plugin.video.zdf-loewenzahn-tivi\resources\tools\smoke_test.py
```

Das Addon nutzt kurzlebige ZDF-API-Tokens und liest sie deshalb zur Laufzeit
aus der offiziellen Löwenzahn-Seite aus.

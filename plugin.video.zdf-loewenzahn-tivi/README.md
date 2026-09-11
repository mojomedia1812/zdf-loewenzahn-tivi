# zdf-loewenzahn-tivi

Kodi-Addon fuer ZDFtivi-Löwenzahn.

Entwickler: m0j01812

## Struktur

- Hauptmenue: Fritz Fuchs, Peter Lustig, Löwenzähnchen mit Keks
- Untermenue: ZDF-Staffeln je Reihe, aufsteigend nach Staffelnummer sortiert
- Folgenansicht: nach Folgennummer sortierte und nummeriert angezeigte ZDF-VOD-Folgen mit HLS-Streamauflösung
- Startprüfung: meldet neuere GitHub-Releases und öffnet nach Bestätigung die ZIP-Installation

Die ZDF-Seite liefert kurzlebige API-Tokens. Das Addon liest den Token deshalb zur Laufzeit aus der Löwenzahn-Startseite und fragt danach die offiziellen ZDF-GraphQL- und PTMD-Endpunkte ab.

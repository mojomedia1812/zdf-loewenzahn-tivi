# zdf-loewenzahn-tivi

Kodi-Addon fuer ZDFtivi-Löwenzahn.

## Struktur

- Hauptmenue: Fritz Fuchs, Peter Lustig, Löwenzähnchen mit Keks
- Untermenue: ZDF-Staffeln je Reihe
- Folgenansicht: abspielbare ZDF-VOD-Folgen mit HLS-Streamauflösung

Die ZDF-Seite liefert kurzlebige API-Tokens. Das Addon liest den Token deshalb zur Laufzeit aus der Löwenzahn-Startseite und fragt danach die offiziellen ZDF-GraphQL- und PTMD-Endpunkte ab.

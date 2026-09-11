# ZDF-TIVI

Kodi-Addon fuer ZDFtivi unter <https://www.zdf.de/kinder>.

## Struktur

- Startseite / Rubriken: die ZDFtivi-Cluster der Kinderstartseite
- Sendungen A-Z: alphabetischer ZDFtivi-Katalog
- Sammlungen: Serien, Meta-Sammlungen und kuratierte ZDFtivi-Seiten
- Staffeln/Folgen: VOD-Folgen mit Episodennummern, Beschreibung, Laufzeit und Vorschaubild
- Filme: Movie-Collections werden direkt als abspielbare Filme angezeigt

Das Addon liest kurzlebige ZDF-API-Tokens zur Laufzeit aus der offiziellen
ZDF-Kinderseite und fragt danach die ZDF-GraphQL- und PTMD-Endpunkte ab.

## Entwicklungstest

```powershell
python plugin.video.zdf-tivi\resources\tools\smoke_test.py
```

Mit `--no-stream` wird die abschliessende PTMD/HLS-Streamaufloesung uebersprungen.

# WM24Import

Meldet sich am **Hersteller-Admin** von [wochenmarkt24.de](https://www.wochenmarkt24.de/SupplierAdmin/login) an,
ruft **Bestellte Artikel → Auslieferungstag** auf und speichert die Tabelle als **CSV-Datei im Download-Ordner**.

## Inhalt

- `wm24import.py` – Login + CSV-Download
- `requirements.txt` – externe Abhängigkeiten
- `.env.example` – Vorlage für die Zugangsdaten (`.env` wird nicht committed, siehe `.gitignore`)

## Voraussetzungen

- Python 3.8 oder höher
- [`requests`](https://pypi.org/project/requests/) (einzige externe Abhängigkeit)

```bash
pip install -r requirements.txt
```

## Zugangsdaten

Die Zugangsdaten dürfen nicht im Code stehen. Entweder als Umgebungsvariablen:

```bash
export WM24_USER="dein-benutzername@wm24.org"
export WM24_PASSWORD="dein-passwort"
```

oder über eine Datei `.env` in diesem Ordner (aus `.env.example` kopieren):

```
WM24_USER=dein-benutzername@wm24.org
WM24_PASSWORD=dein-passwort
```

## Verwendung

```bash
python3 wm24import.py                        # Auslieferungstag = morgen, Ziel: ~/Downloads
python3 wm24import.py --date 24.12.2026      # bestimmter Auslieferungstag (DD.MM.YYYY)
python3 wm24import.py --outdir /pfad/zum/ordner
```

Die CSV-Datei heißt z. B. `Bestellte_Artikel_Auslieferungstag_24-12-2026.csv`
(UTF-8 mit BOM, Trennzeichen Komma – lässt sich direkt in Excel öffnen).

## Hinweise

- Die Webseite lädt die Tabelle serverseitig per DataTables. Das Skript ruft denselben
  Daten-Endpunkt (`/SupplierAdmin/getSoldArticlesDeliveryDate`) auf, den auch die
  **CSV**-Schaltfläche der Webseite verwendet, holt alle Zeilen des Auslieferungstags
  (Standard: morgen, wie auf der Seite voreingestellt) und schreibt sie als CSV.
- Der Login erfordert den Header `X-Requested-With: XMLHttpRequest`, sonst antwortet
  die Seite mit 400 („Invalides Formular-Token“).
- Spalten: Shop, Bestellnummer, Bestellzeit, Produkt Name, Produkt Nummer, Produkt
  Information, Anzahl Bestellungen, Einzel-Preis, Summe, Kaufeinheit, Pickzeit, Foto,
  Tournummer, Tourname, Tourstop.

## Projektstruktur

```
├── wm24import.py
├── requirements.txt
├── .env.example
└── README.md
```

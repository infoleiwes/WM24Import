# WM24Import

Meldet sich am **Hersteller-Admin** von [wochenmarkt24.de](https://www.wochenmarkt24.de/SupplierAdmin/login) an,
ruft **Bestellte Artikel → Auslieferungstag** auf und speichert die Tabelle als **CSV-Datei im Download-Ordner**.

## Inhalt

- `wm24import.py` – Login am Hersteller-Admin + CSV-Download (Bestellte Artikel)
- `wm24_dolibarr_abgleich.py` – Abgleich WM24-Produktliste gegen Dolibarr-Export mit Preisvergleich
- `requirements.txt` – externe Abhängigkeiten
- `.env.example` – Vorlage für die Zugangsdaten (`.env` wird nicht committed, siehe `.gitignore`)

## Voraussetzungen

- Python 3.8 oder höher
- [`requests`](https://pypi.org/project/requests/) und [`openpyxl`](https://pypi.org/project/openpyxl/) (externe Abhängigkeiten)

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

## WM24 ↔ Dolibarr Abgleich (`wm24_dolibarr_abgleich.py`)

Erzeugt aus der WM24-Produktliste (Hersteller Admin → Produkt-Liste, CSV) und einem
Dolibarr-Produktexport (CSV, Kodierung ISO-8859-1) eine neue Tabelle, in der jedes
WM24-Produkt dem passenden Dolibarr-Produkt zugeordnet wird – inkl. Preisvergleich.

```bash
python3 wm24_dolibarr_abgleich.py "WM24_Hersteller Admin  Produkt-Liste.csv" "Dolibarr_export_produit_2.csv"
# optionales 3. Argument: Ausgabe-Präfix (Default: WM24_Dolibarr_Preisvergleich)
```

Ausgabe: `WM24_Dolibarr_Preisvergleich.xlsx` (Excel) und `.csv` (Semikolon, UTF-8 mit BOM).

Spalten: WM24 Produkt-Nr., WM24 Produkt Name, Inhalt, WM24 Preis (EUR), Dolibarr Ref.Nr.,
Dolibarr Bezeichnung, Dolibarr PriceLevelUnitPriceTTC (EUR), Differenz (EUR), Differenz (%),
Match.

Zuordnung über Produktname (Umlaute normalisiert), Gebindegröße aus „Inhalt“
(250 g → 250G, 500 g → 500G, 1000 g/1 kg → 1KG) und „gemahlen“ vs. „ganze Bohne“,
z. B. `WM11034` 1 kg → `KAETG-1KG`, La Paz Honduras gemahlen → `KHONBIOM-…`,
ganze Bohne → `KHONBIOG-…`. Preisvergleich: WM24 „Preis“ gegen Dolibarr
„PriceLevelUnitPriceTTC“.

## Projektstruktur

```
├── wm24import.py
├── wm24_dolibarr_abgleich.py
├── requirements.txt
├── .env.example
└── README.md
```

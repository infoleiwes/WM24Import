#!/usr/bin/env python3
"""WM24Import - laedt die Liste "Bestellte Artikel / Auslieferungstag" von
wochenmarkt24.de (Hersteller Admin) als CSV in den Download-Ordner.

Zugangsdaten werden aus den Umgebungsvariablen WM24_USER / WM24_PASSWORD
oder aus einer .env-Datei neben diesem Skript gelesen.
"""

import argparse
import csv
import datetime as dt
import os
import sys
from pathlib import Path

import requests

BASE_URL = "https://www.wochenmarkt24.de"
LOGIN_URL = f"{BASE_URL}/SupplierAdmin/login"
LOGIN_CHECK_URL = f"{BASE_URL}/SupplierAdmin/loginCheck"
SOLD_PAGE_URL = f"{BASE_URL}/SupplierAdmin/soldArticlesDeliveryDate"
AJAX_URL = f"{BASE_URL}/SupplierAdmin/getSoldArticlesDeliveryDate"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

COLUMNS = [
    "shopName",
    "orderOrdernumber",
    "ordertime",
    "name",
    "ordernumber",
    "hs_order_basket_attributes_product_information",
    "quantity",
    "price",
    "sumPrice",
    "purchaseunit",
    "created_at",
    "images",
    "hs_order_attributes_tour_number",
    "hs_order_attributes_tour_name",
    "hs_order_attributes_tour_stop",
]

HEADERS = [
    "Shop",
    "Bestellnummer",
    "Bestellzeit",
    "Produkt Name",
    "Produkt Nummer",
    "Produkt Information",
    "Anzahl Bestellungen",
    "Einzel-Preis",
    "Summe",
    "Kaufeinheit",
    "Pickzeit",
    "Foto",
    "Tournummer",
    "Tourname",
    "Tourstop",
]


def load_env_file(path):
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_credentials():
    user = os.environ.get("WM24_USER")
    password = os.environ.get("WM24_PASSWORD")
    if not user or not password:
        print(
            "Fehler: WM24_USER und WM24_PASSWORD fehlen. "
            "Bitte als Umgebungsvariablen setzen oder in einer .env-Datei "
            "neben dem Skript hinterlegen (siehe .env.example).",
            file=sys.stderr,
        )
        sys.exit(2)
    return user, password


def login(session, user, password):
    session.get(LOGIN_URL, timeout=30)
    response = session.post(
        LOGIN_CHECK_URL,
        data={"username": user, "password": password},
        headers={
            "Referer": LOGIN_URL,
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=30,
    )
    if response.status_code != 200 or "login-form" in response.text:
        print("Fehler: Anmeldung fehlgeschlagen (Login nicht erfolgreich).", file=sys.stderr)
        sys.exit(3)
    page = session.get(SOLD_PAGE_URL, timeout=30)
    if page.status_code != 200 or "sold_product_list" not in page.text:
        print("Fehler: Seite 'Bestellte Artikel / Auslieferungstag' nicht erreichbar.", file=sys.stderr)
        sys.exit(4)


def fetch_rows(session, delivery_date):
    rows = []
    start = 0
    page_size = 10000
    while True:
        params = {
            "draw": "1",
            "start": str(start),
            "length": str(page_size),
            "search[value]": "",
            "search[regex]": "false",
            "order[0][column]": "2",
            "order[0][dir]": "desc",
        }
        for i, col in enumerate(COLUMNS):
            params[f"columns[{i}][data]"] = col
            params[f"columns[{i}][name]"] = ""
            params[f"columns[{i}][searchable]"] = "true" if i in (2, 3) else "false"
            params[f"columns[{i}][orderable]"] = "true"
            params[f"columns[{i}][search][value]"] = delivery_date if i == 0 else ""
            params[f"columns[{i}][search][regex]"] = "false"
        response = session.get(
            AJAX_URL,
            params=params,
            headers={
                "Referer": SOLD_PAGE_URL,
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", [])
        rows.extend(data)
        total = int(payload.get("recordsFiltered") or 0)
        if not data or len(rows) >= total:
            break
        start += page_size
    return rows


def format_purchaseunit(value):
    if not value:
        return ""
    parts = str(value).split(" ")
    try:
        return f"{float(parts[0]):g} " + " ".join(parts[1:])
    except (ValueError, IndexError):
        return str(value)


def write_csv(rows, download_dir, delivery_date):
    download_dir.mkdir(parents=True, exist_ok=True)
    stamp = delivery_date.replace(".", "-")
    path = download_dir / f"Bestellte_Artikel_Auslieferungstag_{stamp}.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADERS)
        for row in rows:
            writer.writerow(
                [
                    row.get("shopName", ""),
                    row.get("orderOrdernumber", ""),
                    row.get("ordertime", ""),
                    row.get("name", ""),
                    row.get("ordernumber", ""),
                    row.get("hs_order_basket_attributes_product_information", ""),
                    row.get("quantity", ""),
                    row.get("price", ""),
                    row.get("sumPrice", ""),
                    format_purchaseunit(row.get("purchaseunit")),
                    row.get("created_at", ""),
                    row.get("images", ""),
                    row.get("hs_order_attributes_tour_number", ""),
                    row.get("hs_order_attributes_tour_name", ""),
                    row.get("hs_order_attributes_tour_stop", ""),
                ]
            )
    return path


def main():
    parser = argparse.ArgumentParser(description="WM24Import: CSV-Export 'Bestellte Artikel / Auslieferungstag'")
    parser.add_argument(
        "--date",
        default=None,
        help="Auslieferungstag im Format DD.MM.YYYY (Standard: morgen)",
    )
    parser.add_argument(
        "--outdir",
        default=str(Path.home() / "Downloads"),
        help="Zielordner fuer die CSV-Datei (Standard: ~/Downloads)",
    )
    args = parser.parse_args()

    if args.date:
        delivery_date = args.date
        dt.datetime.strptime(delivery_date, "%d.%m.%Y")
    else:
        delivery_date = (dt.date.today() + dt.timedelta(days=1)).strftime("%d.%m.%Y")

    load_env_file(Path(__file__).resolve().parent / ".env")
    user, password = get_credentials()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    login(session, user, password)
    rows = fetch_rows(session, delivery_date)
    path = write_csv(rows, Path(args.outdir), delivery_date)
    print(f"{len(rows)} Zeilen fuer Auslieferungstag {delivery_date} gespeichert nach: {path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Abgleich WM24-Produktliste gegen Dolibarr-Produktexport.

Erzeugt eine Tabelle, in der jedes WM24-Produkt (Produkt-Nr. z. B. WM11034)
dem passenden Dolibarr-Produkt (Ref.Nr. z. B. KAETG-1KG) zugeordnet wird,
inkl. Preisvergleich WM24 "Preis" vs. Dolibarr "PriceLevelUnitPriceTTC".

Aufruf:
    python3 wm24_dolibarr_abgleich.py <wm24_csv> <dolibarr_csv> <ausgabe_prefix>
"""

import csv
import re
import sys
import unicodedata
from difflib import SequenceMatcher

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

SIZE_RE = re.compile(r"^(\d+)\s*(KG|G)$")
WM_RE = re.compile(r"\((WM\d+(?:\.\d+)?)\)")
DOLI_REF_RE = re.compile(r"^[A-Z]+-\d+(?:KG|G)$")
DROP_TOKENS = {"bio", "gemahlen", "kaffee"}


def norm_tokens(text):
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return {t for t in s.split() if t and t not in DROP_TOKENS}


def parse_grams(inhalt):
    m = re.match(r"\s*([\d.,]+)\s*(kg|g)\b", inhalt.strip().lower())
    if not m:
        return None
    value = float(m.group(1).replace(",", "."))
    return value * 1000 if m.group(2) == "kg" else value


def size_code(grams):
    if grams is None:
        return None
    if grams >= 1000 and grams % 1000 == 0:
        return f"{int(grams // 1000)}KG"
    return f"{int(grams)}G"


def parse_price(text):
    t = text.replace("€", "").replace(" ", "").strip()
    if not t:
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def load_dolibarr(path):
    candidates = []
    with open(path, encoding="latin-1", newline="") as fh:
        for row in csv.DictReader(fh):
            ref = row["Ref.Nr."].strip()
            if not DOLI_REF_RE.match(ref):
                continue
            suffix = ref.rsplit("-", 1)[1]
            if not SIZE_RE.match(suffix):
                continue
            bezeichnung = row["Bezeichnung"]
            ground = "gemahlen" in bezeichnung.lower()
            base_name = re.sub(r"\s*\d+\s*(KG|G)\s*$", "", bezeichnung, flags=re.I)
            base_name = re.sub(r"\((gemahlen|bio)\)", "", base_name, flags=re.I)
            candidates.append(
                {
                    "ref": ref,
                    "size": suffix.upper(),
                    "ground": ground,
                    "bezeichnung": bezeichnung,
                    "ttc": float(row["PriceLevelUnitPriceTTC"] or 0),
                    "tokens": norm_tokens(base_name),
                }
            )
    return candidates


def match(wm_row, candidates):
    name = wm_row["Produkt Name"]
    m = WM_RE.search(name)
    wm_nr = m.group(1) if m else ""
    grams = parse_grams(wm_row.get("Inhalt", ""))
    size = size_code(grams)
    ground = "gemahlen" in name.lower()

    clean = WM_RE.sub("", name)
    clean = re.sub(r"\d+(?:[.,]\d+)?\s*(?:kg|g)\b", " ", clean, flags=re.I)
    clean = re.sub(r"\b(ganze bohne|gemahlen)\b", " ", clean, flags=re.I)
    clean = clean.split(" - ")[0]
    wm_tokens = norm_tokens(clean)

    best = None
    best_score = (0, 0.0)
    for cand in candidates:
        if cand["size"] != size or cand["ground"] != ground:
            continue
        inter = len(cand["tokens"] & wm_tokens)
        if inter == 0:
            continue
        ratio = SequenceMatcher(
            None, " ".join(sorted(cand["tokens"])), " ".join(sorted(wm_tokens))
        ).ratio()
        if (inter, ratio) > best_score:
            best_score = (inter, ratio)
            best = cand
    return wm_nr, grams, size, ground, wm_tokens, best, best_score


def main():
    wm_path, doli_path, out_prefix = sys.argv[1], sys.argv[2], sys.argv[3]
    candidates = load_dolibarr(doli_path)

    results = []
    with open(wm_path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            wm_nr, grams, size, ground, wm_tokens, best, score = match(row, candidates)
            wm_price = parse_price(row.get("Preis", ""))
            entry = {
                "wm_nr": wm_nr,
                "name": row["Produkt Name"],
                "inhalt": row.get("Inhalt", ""),
                "wm_price": wm_price,
                "ref": best["ref"] if best else "",
                "bezeichnung": best["bezeichnung"] if best else "",
                "ttc": best["ttc"] if best else None,
                "matched": best is not None,
                "score": score,
            }
            if best and wm_price is not None:
                entry["diff"] = round(wm_price - best["ttc"], 2)
                entry["diff_pct"] = (
                    round((wm_price - best["ttc"]) / best["ttc"] * 100, 1)
                    if best["ttc"]
                    else None
                )
            else:
                entry["diff"] = None
                entry["diff_pct"] = None
            results.append(entry)

    results.sort(key=lambda e: e["wm_nr"])

    header = [
        "WM24 Produkt-Nr.",
        "WM24 Produkt Name",
        "Inhalt",
        "WM24 Preis (EUR)",
        "Dolibarr Ref.Nr.",
        "Dolibarr Bezeichnung",
        "Dolibarr PriceLevelUnitPriceTTC (EUR)",
        "Differenz WM24 - Dolibarr (EUR)",
        "Differenz (%)",
        "Match",
    ]

    def row_values(e):
        return [
            e["wm_nr"],
            e["name"],
            e["inhalt"],
            e["wm_price"] if e["wm_price"] is not None else "",
            e["ref"],
            e["bezeichnung"],
            e["ttc"] if e["ttc"] is not None else "",
            e["diff"] if e["diff"] is not None else "",
            e["diff_pct"] if e["diff_pct"] is not None else "",
            "ja" if e["matched"] else "NEIN - kein Dolibarr-Produkt gefunden",
        ]

    csv_path = out_prefix + ".csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(header)
        for e in results:
            writer.writerow(row_values(e))

    xlsx_path = out_prefix + ".xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Preisvergleich"
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for e in results:
        ws.append(row_values(e))
    widths = [16, 70, 10, 16, 18, 40, 22, 20, 12, 30]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    wb.save(xlsx_path)

    matched = sum(1 for e in results if e["matched"])
    print(f"{len(results)} WM24-Produkte verarbeitet, {matched} zugeordnet, {len(results) - matched} ohne Match")
    for e in results:
        if not e["matched"]:
            print("  ohne Match:", e["wm_nr"], e["name"][:70])
    print("CSV:", csv_path)
    print("XLSX:", xlsx_path)


if __name__ == "__main__":
    main()

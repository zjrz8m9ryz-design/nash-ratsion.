#!/usr/bin/env python3
"""
Weekly price-feed check.

Important: this does not invent prices or scrape store pages blindly.
It can consume a CSV feed once a stable, permitted source is configured.
Until then it records the check time and leaves prices explicitly marked as not connected.
"""
import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "prices.json"
FEED_URL = os.environ.get("PRICE_FEED_URL", "").strip()

data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
checked = datetime.now(timezone.utc).isoformat(timespec="seconds")
data["last_checked"] = checked

if FEED_URL:
    request = Request(FEED_URL, headers={"User-Agent": "NashRatsion/1.0 price-feed-check"})
    with urlopen(request, timeout=25) as response:
        csv_text = response.read().decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    required = {"product", "store", "price", "checked_at"}
    if rows and not required.issubset(rows[0].keys()):
        raise SystemExit("CSV feed must contain columns: product, store, price, checked_at")
    parsed = []
    for row in rows:
        try:
            price = float(str(row["price"]).replace(",", ".").replace(" ", ""))
        except (ValueError, TypeError):
            continue
        if price < 0:
            continue
        parsed.append({
            "product": row["product"].strip(),
            "store": row["store"].strip(),
            "price": round(price, 2),
            "checked_at": row["checked_at"].strip()
        })
    data["items"] = parsed
    data["source_status"] = "live" if parsed else "feed_empty"
    data["note"] = "Цены получены из настроенного CSV-источника. Проверяйте дату и магазин: цена может зависеть от адреса и карты лояльности."
else:
    data["source_status"] = "not_connected"
    data["note"] = (
        "Еженедельная задача запущена, но источник цен ещё не подключён. "
        "Текущие ориентировочные цены нельзя считать автоматически обновлёнными. "
        "Подключите разрешённый CSV/API-источник в секрет PRICE_FEED_URL."
    )

DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Price feed status: {data['source_status']}; items: {len(data['items'])}; checked: {checked}")

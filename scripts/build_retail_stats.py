"""Compute full descriptive statistics for the UCI "Online Retail" dataset.

Pure standard library (zipfile + xml iterparse), no pandas/openpyxl needed.

Usage:
    python scripts/build_retail_stats.py "/path/to/Online Retail.xlsx"

Output: src/data/retail_stats.json (consumed by the /stats page).
Source: https://archive.ics.uci.edu/dataset/352/online+retail
"""
from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "src", "data", "retail_stats.json")
EPOCH = datetime(1899, 12, 30)
NON_PRODUCT = {"POST", "D", "M", "C2", "DOT", "BANK CHARGES", "S", "AMAZONFEE",
               "B", "CRUK", "PADS", "m"}
COLS = ["invoice", "stock", "desc", "qty", "date", "price", "cust", "country"]


def load_shared(z: zipfile.ZipFile) -> list[str]:
    out = []
    for _, el in ET.iterparse(z.open("xl/sharedStrings.xml")):
        if el.tag == NS + "si":
            out.append("".join(t.text or "" for t in el.iter(NS + "t")))
            el.clear()
    return out


def iter_rows(path: str):
    with zipfile.ZipFile(path) as z:
        shared = load_shared(z)
        row: dict[str, object] = {}
        for ev, el in ET.iterparse(z.open("xl/worksheets/sheet1.xml"), events=("end",)):
            if el.tag == NS + "c":
                ref = el.get("r", "")
                col = re.match(r"[A-Z]+", ref).group(0)
                t = el.get("t")
                v = el.find(NS + "v")
                val = None
                if t == "inlineStr":
                    val = "".join(x.text or "" for x in el.iter(NS + "t"))
                elif v is not None and v.text is not None:
                    val = shared[int(v.text)] if t == "s" else v.text
                row[col] = val
                el.clear()
            elif el.tag == NS + "row":
                r = int(el.get("r"))
                if r > 1:
                    yield [row.get(c) for c in "ABCDEFGH"]
                row = {}
                el.clear()


def quantiles(sorted_vals: list[float]) -> dict:
    n = len(sorted_vals)
    if not n:
        return {}
    q = lambda p: sorted_vals[min(n - 1, int(p * (n - 1)))]
    mean = sum(sorted_vals) / n
    var = sum((x - mean) ** 2 for x in sorted_vals) / n
    return {"min": sorted_vals[0], "p25": q(.25), "median": q(.5), "p75": q(.75),
            "p95": q(.95), "p99": q(.99), "max": sorted_vals[-1],
            "mean": round(mean, 3), "std": round(var ** .5, 3)}


def hist(values, edges):
    labels, counts = [], [0] * (len(edges))
    for i, e in enumerate(edges):
        labels.append(f"{e}" if i == len(edges) - 1 else (f"{e}" if edges[i + 1] == e + 1 else f"{e}-{edges[i + 1] - 1}"))
    labels[-1] = f"{edges[-1]}+"
    for v in values:
        idx = 0
        for i, e in enumerate(edges):
            if v >= e:
                idx = i
        counts[idx] += 1
    return {"labels": labels, "counts": counts}


def main(path: str) -> None:
    n = 0
    miss = Counter()
    inv_rows = Counter()
    inv_items: dict[str, set] = defaultdict(set)
    inv_meta: dict[str, tuple] = {}
    inv_cancel = {}
    cust_inv: dict[str, set] = defaultdict(set)
    prod_desc: dict[str, Counter] = defaultdict(Counter)
    prod_qty = Counter()
    prod_rev = Counter()
    prod_inv: dict[str, set] = defaultdict(set)
    country_rev = Counter()
    country_inv: dict[str, set] = defaultdict(set)
    month_rev = Counter()
    month_inv: dict[str, set] = defaultdict(set)
    hour_inv: dict[int, set] = defaultdict(set)
    wd_inv: dict[int, set] = defaultdict(set)
    seen_rows = Counter()
    neg_qty = zero_price = neg_price = cancel_rows = non_product_rows = 0
    qty_pos, price_pos = [], []
    dmin = dmax = None
    clean_rows = 0
    clean_inv: dict[str, set] = defaultdict(set)

    for inv, stock, desc, qty, dt, price, cust, country in iter_rows(path):
        n += 1
        for name, v in zip(COLS, (inv, stock, desc, qty, dt, price, cust, country)):
            if v in (None, ""):
                miss[name] += 1
        inv = str(inv); stock = str(stock) if stock is not None else ""
        qty = int(float(qty)); price = float(price)
        d = EPOCH + timedelta(days=float(dt))
        d = d.replace(microsecond=0)
        dmin = d if dmin is None or d < dmin else dmin
        dmax = d if dmax is None or d > dmax else dmax
        cancel = inv.startswith("C")
        cancel_rows += cancel
        neg_qty += qty < 0
        zero_price += price == 0
        neg_price += price < 0
        seen_rows[(inv, stock, desc, qty, dt, price, cust)] += 1
        inv_rows[inv] += 1
        inv_items[inv].add(stock)
        cu = None if cust is None else str(int(float(cust)))
        inv_meta[inv] = (cu, country, d)
        inv_cancel[inv] = cancel
        if cu:
            cust_inv[cu].add(inv)
        if desc:
            prod_desc[stock][desc.strip()] += 1
        is_np = stock in NON_PRODUCT or not re.match(r"^\d{5}", stock)
        non_product_rows += is_np
        if not cancel and qty > 0 and price > 0:
            rev = qty * price
            qty_pos.append(qty); price_pos.append(price)
            country_rev[country] += rev
            country_inv[country].add(inv)
            mk = d.strftime("%Y-%m")
            month_rev[mk] += rev
            month_inv[mk].add(inv)
            hour_inv[d.hour].add(inv)
            wd_inv[d.weekday()].add(inv)
            if not is_np:
                prod_qty[stock] += qty
                prod_rev[stock] += rev
                prod_inv[stock].add(inv)
                clean_rows += 1
                clean_inv[inv].add(stock)

    dup_rows = sum(c - 1 for c in seen_rows.values() if c > 1)
    pname = {s: c.most_common(1)[0][0] for s, c in prod_desc.items()}
    all_products = {s for items in inv_items.values() for s in items}
    sizes = sorted(len(v) for v in clean_inv.values())
    n_clean = len(clean_inv)
    total_rev = sum(month_rev.values())
    cust_ids = {m[0] for m in inv_meta.values() if m[0]}

    top = lambda c, k=15: c.most_common(k)
    top_by_inv = sorted(prod_inv.items(), key=lambda kv: -len(kv[1]))[:20]
    pair_counts = Counter()  # top-level support of single items (for Apriori min_sup guidance)
    sup_curve = []
    item_sup = sorted((len(v) for v in prod_inv.values()), reverse=True)
    for pct in (0.1, 0.2, 0.5, 1, 2, 3, 5):
        thr = n_clean * pct / 100
        sup_curve.append({"min_sup_pct": pct, "min_count": round(thr, 1),
                          "frequent_items": sum(1 for s in item_sup if s >= thr)})

    out = {
        "source": "UCI Machine Learning Repository - Online Retail (id 352)",
        "url": "https://archive.ics.uci.edu/dataset/352/online+retail",
        "overview": {
            "rows": n, "columns": 8,
            "invoices": len(inv_items),
            "customers": len(cust_ids),
            "products_stockcodes": len(all_products),
            "countries": len({m[1] for m in inv_meta.values()}),
            "date_from": dmin.isoformat(sep=" "), "date_to": dmax.isoformat(sep=" "),
            "days_span": (dmax - dmin).days + 1,
            "total_revenue_valid_sales": round(total_rev, 2),
            "avg_order_value": round(total_rev / max(1, len(set().union(*month_inv.values()))), 2),
        },
        "columns": [
            {"name": "InvoiceNo", "type": "nominal", "desc": "Mã hóa đơn (6 chữ số). Bắt đầu bằng 'C' = hủy đơn"},
            {"name": "StockCode", "type": "nominal", "desc": "Mã sản phẩm (5 chữ số)"},
            {"name": "Description", "type": "text", "desc": "Tên sản phẩm"},
            {"name": "Quantity", "type": "integer", "desc": "Số lượng mỗi dòng"},
            {"name": "InvoiceDate", "type": "datetime", "desc": "Thời điểm lập hóa đơn"},
            {"name": "UnitPrice", "type": "numeric", "desc": "Đơn giá (GBP)"},
            {"name": "CustomerID", "type": "nominal", "desc": "Mã khách hàng (5 chữ số)"},
            {"name": "Country", "type": "nominal", "desc": "Quốc gia của khách"},
        ],
        "missing": {k: {"count": miss.get(k, 0), "pct": round(100 * miss.get(k, 0) / n, 2)} for k in COLS},
        "quality": {
            "cancellation_rows": cancel_rows,
            "cancellation_invoices": sum(inv_cancel.values()),
            "negative_quantity_rows": neg_qty,
            "zero_price_rows": zero_price,
            "negative_price_rows": neg_price,
            "duplicate_rows": dup_rows,
            "non_product_rows": non_product_rows,
            "non_product_codes": sorted(s for s in all_products if s in NON_PRODUCT or not re.match(r"^\d{5}", s))[:40],
            "valid_sale_rows": len(qty_pos),
        },
        "quantity": quantiles(sorted(qty_pos)),
        "unit_price": quantiles(sorted(price_pos)),
        "invoice_lines": {"quantiles": quantiles(sorted(inv_rows.values()))},
        "basket": {
            "note": "Giỏ hàng sạch cho Apriori: bỏ hóa đơn hủy, qty<=0, giá<=0, mã không phải sản phẩm; mỗi hóa đơn = 1 tập item (không trùng).",
            "clean_transactions": n_clean,
            "clean_rows": clean_rows,
            "distinct_items": len(prod_inv),
            "size": quantiles([float(x) for x in sizes]),
            "size_hist": hist(sizes, [1, 2, 3, 4, 5, 6, 8, 11, 16, 21, 31, 51, 101]),
            "single_item_baskets_pct": round(100 * sum(1 for s in sizes if s == 1) / max(1, n_clean), 2),
            "multi_item_baskets": sum(1 for s in sizes if s >= 2),
            "density_pct": round(100 * clean_rows / max(1, n_clean * len(prod_inv)), 4),
            "support_curve": sup_curve,
        },
        "customers": {
            "orders_per_customer": quantiles(sorted(float(len(v)) for v in cust_inv.values())),
            "repeat_customers": sum(1 for v in cust_inv.values() if len(v) > 1),
            "rows_without_customer_pct": round(100 * miss.get("cust", 0) / n, 2),
        },
        "top_products_by_baskets": [
            {"code": s, "name": pname.get(s, ""), "baskets": len(v),
             "support_pct": round(100 * len(v) / n_clean, 2)} for s, v in top_by_inv],
        "top_products_by_quantity": [
            {"code": s, "name": pname.get(s, ""), "qty": q} for s, q in top(prod_qty)],
        "top_products_by_revenue": [
            {"code": s, "name": pname.get(s, ""), "revenue": round(r, 2)} for s, r in top(prod_rev)],
        "countries": [
            {"country": c, "revenue": round(r, 2), "invoices": len(country_inv[c]),
             "revenue_pct": round(100 * r / total_rev, 2)} for c, r in top(country_rev, 40)],
        "monthly": [
            {"month": m, "revenue": round(month_rev[m], 2), "invoices": len(month_inv[m])}
            for m in sorted(month_rev)],
        "hourly_invoices": [{"hour": h, "invoices": len(hour_inv[h])} for h in sorted(hour_inv)],
        "weekday_invoices": [
            {"day": ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"][d], "invoices": len(wd_inv[d])}
            for d in range(7)],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", OUT, f"({os.path.getsize(OUT)//1024} KB)")
    print(json.dumps(out["overview"], indent=1))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])

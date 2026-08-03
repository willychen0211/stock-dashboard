"""
抓取 0050.TW（元大台灣50）日K資料，計算支撐/壓力與均線，輸出成 JSON。
資料來源：Yahoo Finance chart API（公開、無需金鑰）。
用法：python fetch_data.py <SYMBOL> <RANGE> <OUT_JSON>
例如：python fetch_data.py 0050.TW 6mo data/0050.json
"""
import sys
import json
import urllib.request

def fetch_chart(symbol, rng="6mo", interval="1d"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={rng}&interval={interval}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = json.loads(resp.read().decode())
    result = raw["chart"]["result"][0]
    meta = result["meta"]
    ts = result["timestamp"]
    quote = result["indicators"]["quote"][0]
    candles = []
    for i, t in enumerate(ts):
        o, h, l, c, v = quote["open"][i], quote["high"][i], quote["low"][i], quote["close"][i], quote["volume"][i]
        if None in (o, h, l, c):
            continue
        candles.append({"t": t, "o": round(o, 2), "h": round(h, 2), "l": round(l, 2), "c": round(c, 2), "v": v})
    return meta, candles

def sma(values, window):
    out = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
        else:
            out.append(round(sum(values[i + 1 - window:i + 1]) / window, 2))
    return out

def find_pivots(candles, left=3, right=3):
    """區域高低點：左右 N 根K棒內都沒有更高/更低，視為波段高/低點"""
    highs, lows = [], []
    n = len(candles)
    for i in range(left, n - right):
        h = candles[i]["h"]
        l = candles[i]["l"]
        window_h = [candles[j]["h"] for j in range(i - left, i + right + 1) if j != i]
        window_l = [candles[j]["l"] for j in range(i - left, i + right + 1) if j != i]
        if all(h >= wh for wh in window_h) and h > max(window_h):
            highs.append({"t": candles[i]["t"], "price": h})
        if all(l <= wl for wl in window_l) and l < min(window_l):
            lows.append({"t": candles[i]["t"], "price": l})
    return highs, lows

def cluster_levels(points, tolerance_pct=0.015):
    """把接近的波段高/低點合併成一個「關鍵水平」，回傳依出現次數排序的清單"""
    prices = sorted(p["price"] for p in points)
    clusters = []
    for p in prices:
        placed = False
        for cl in clusters:
            if abs(p - cl["avg"]) / cl["avg"] <= tolerance_pct:
                cl["members"].append(p)
                cl["avg"] = sum(cl["members"]) / len(cl["members"])
                placed = True
                break
        if not placed:
            clusters.append({"avg": p, "members": [p]})
    clusters.sort(key=lambda c: len(c["members"]), reverse=True)
    return [{"price": round(c["avg"], 2), "touches": len(c["members"])} for c in clusters]

def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "0050.TW"
    rng = sys.argv[2] if len(sys.argv) > 2 else "6mo"
    out_path = sys.argv[3] if len(sys.argv) > 3 else "data/0050.json"

    meta, candles = fetch_chart(symbol, rng)
    closes = [c["c"] for c in candles]
    ma5 = sma(closes, 5)
    ma20 = sma(closes, 20)
    ma60 = sma(closes, 60)
    for i, c in enumerate(candles):
        c["ma5"] = ma5[i]
        c["ma20"] = ma20[i]
        c["ma60"] = ma60[i]

    # 用最近 60 根交易日找波段高低點，抓最近走勢的支撐壓力（避免半年前的舊高低點失去意義）
    recent = candles[-60:] if len(candles) > 60 else candles
    highs, lows = find_pivots(recent, left=3, right=3)
    resistance = cluster_levels(highs)[:4]
    support = cluster_levels(lows)[:4]

    out = {
        "symbol": symbol,
        "name": meta.get("longName") or meta.get("shortName") or symbol,
        "currency": meta.get("currency"),
        "regularMarketTime": meta.get("regularMarketTime"),
        "regularMarketPrice": meta.get("regularMarketPrice"),
        "regularMarketDayHigh": meta.get("regularMarketDayHigh"),
        "regularMarketDayLow": meta.get("regularMarketDayLow"),
        "regularMarketVolume": meta.get("regularMarketVolume"),
        "fiftyTwoWeekHigh": meta.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": meta.get("fiftyTwoWeekLow"),
        "candles": candles,
        "support": support,
        "resistance": resistance,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"OK: {len(candles)} candles -> {out_path}")
    print(f"Support: {support}")
    print(f"Resistance: {resistance}")

if __name__ == "__main__":
    main()

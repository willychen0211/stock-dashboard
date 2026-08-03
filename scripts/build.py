"""
把 data/<symbol>.json 的價格資料 + 新聞/市場摘要文字，套進 template.html，產出 site/index.html
用法：python build.py <DATA_JSON> <TEMPLATE> <OUT_HTML> <UPDATE_LABEL> <NEWS_HTML_FILE> <GLOBAL_HTML_FILE>
"""
import sys
import json
import html


def fmt(v, decimals=2):
    if v is None:
        return "—"
    return f"{v:.{decimals}f}"


def level_list_html(levels, unit="元"):
    if not levels:
        return '<li><span class="lt">近期資料不足，尚無明顯區域</span></li>'
    items = []
    for lv in levels:
        items.append(
            f'<li><span class="lp num">{lv["price"]:.2f} {unit}</span>'
            f'<span class="lt">近期出現 {lv["touches"]} 次</span></li>'
        )
    return "\n".join(items)


def main():
    data_path, template_path, out_path, update_label, news_path, global_path = sys.argv[1:7]

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    with open(template_path, encoding="utf-8") as f:
        tpl = f.read()
    with open(news_path, encoding="utf-8") as f:
        news_html = f.read()
    with open(global_path, encoding="utf-8") as f:
        global_html = f.read()

    candles = data["candles"]
    last = candles[-1]
    prev = candles[-2] if len(candles) > 1 else last
    price = data.get("regularMarketPrice", last["c"])
    change = price - prev["c"]
    change_pct = (change / prev["c"] * 100) if prev["c"] else 0
    change_class = "chg-up" if change >= 0 else "chg-down"
    sign = "+" if change >= 0 else ""

    import datetime
    ts = data.get("regularMarketTime")
    if ts:
        dt = datetime.datetime.utcfromtimestamp(ts) + datetime.timedelta(hours=8)
        last_update = dt.strftime("%Y/%m/%d %H:%M")
    else:
        last_update = "—"

    replacements = {
        "{{SYMBOL_NAME}}": html.escape(data.get("name", data["symbol"])),
        "{{SYMBOL}}": html.escape(data["symbol"]),
        "{{UPDATE_LABEL}}": html.escape(update_label),
        "{{LAST_UPDATE}}": last_update,
        "{{CURRENT_PRICE}}": fmt(price),
        "{{CHANGE_CLASS}}": change_class,
        "{{DAY_CHANGE}}": f"{sign}{fmt(change)}",
        "{{DAY_CHANGE_PCT}}": f"{sign}{fmt(change_pct)}%",
        "{{DAY_HIGH}}": fmt(data.get("regularMarketDayHigh")),
        "{{DAY_LOW}}": fmt(data.get("regularMarketDayLow")),
        "{{WEEK52_HIGH}}": fmt(data.get("fiftyTwoWeekHigh")),
        "{{WEEK52_LOW}}": fmt(data.get("fiftyTwoWeekLow")),
        "{{SUPPORT_LIST_HTML}}": level_list_html(data.get("support", [])),
        "{{RESISTANCE_LIST_HTML}}": level_list_html(data.get("resistance", [])),
        "{{NEWS_SECTION_HTML}}": news_html,
        "{{GLOBAL_MARKET_SECTION_HTML}}": global_html,
        "{{CHART_DATA_JSON}}": json.dumps(data, ensure_ascii=False),
    }

    out = tpl
    for k, v in replacements.items():
        out = out.replace(k, v)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Built -> {out_path}")


if __name__ == "__main__":
    main()

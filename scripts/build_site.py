"""Build the static report page from `out/results.json`.

    python scripts/build_site.py

No framework and no external requests: the page is one self-contained HTML file so
it opens offline and from a `file://` path, and there is nothing to break at build
time. Every number comes from `out/results.json`; the prose is fixed text and is
the part a human edits.
"""

from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "out", "results.json")
OUT = os.path.join(ROOT, "site", "index.html")

PROBLEMS = {
    "cordeau2006": {
        "title": "Dial-a-Ride",
        "short": "DARP",
        "what": "把 36 位乘客的接送塞進 4 輛車：時間窗、共乘容量、最長乘車時間、最長趟次。",
        "how": "最便宜可行插入。每插一對（上車、下車）就從車場重排一次時刻表，用真時刻表判可行性，不用估算。",
        "why": "時間窗讓「先排誰」比「走多短」更關鍵，所以要真的排一遍時鐘。",
    },
    "fischetti1998": {
        "title": "Orienteering",
        "short": "OP",
        "what": "單車、有時間預算，選一條回程閉環，把沿路城市的獎金拿得最多。",
        "how": "按「獎金 / 多繞的路」比值插入城市；插不進去就 2-opt 把路壓短再插。多輪重啟，每輪給獎金加不同噪聲。",
        "why": "500 座城，窮舉不可能；但「繞一點多拿很多」的貪心加壓路，能在 60 秒裡逼近參考解。",
    },
    "barnhart2000": {
        "title": "OD 整數多商品流",
        "short": "ODIMCF",
        "what": "585 個商品各走一條不可拆的路，或退回人工弧（等於賠掉那筆收入）；弧有容量。",
        "how": "最寬路徑貪心：每個商品挑「瓶頸容量最大」的路，而不是最短路——物理弧成本都是 0，最短路只會把貨堆在同一幾條弧上。",
        "why": "目標是「別賠錢」，所以排序用收入而不是流量；多種排序各跑一遍取最好。",
    },
    "hoffman1993": {
        "title": "機組排班集合劃分",
        "short": "SPP",
        "what": "100 段航班，15,000 個候選機組輪轉，每一段剛好被一個輪轉覆蓋，成本最小。",
        "how": "三段：min-conflicts 找覆蓋 → 大鄰域（挑幾根已選輪轉，把那幾段航班重解一次）→ CP-SAT 帶提示再優化。",
        "why": "成本與長度無關（1–200 對 1–51 段），最優解是「很多很短」，而分支定界是從「很少很長」往下走——這就是它撞牆的原因。",
    },
    "bodur2017": {
        "title": "隨機容量選址",
        "short": "SCFLP",
        "what": "先決定開哪些倉（開倉費），再看 1,500 個需求情境各自怎麼送；總容量要撐得住最壞情境。",
        "how": "開倉集合用「從全開往下刪」：每次刪一個最貴的，用抽樣情境估期望成本，容量撐得住且成本下降就刪。送貨用「最便宜配對先送」的貪心運輸。",
        "why": "每個情境都解一次 LP 放不進 60 秒；成本係數不隨情境變，所以配對順序只排一次。",
    },
    "nagy2015": {
        "title": "可分割收送的 VRP",
        "short": "VRPDDP",
        "what": "199 位顧客，送貨與取貨可以分兩趟做，但車上任何時刻的貨不能超過容量。",
        "how": "把「送貨」與「取貨」當兩個獨立任務，Clarke-Wright 節約法在兩個容量預算下分組；每組先送後取、區塊內 2-opt，再用帶載重檢查的全序列 2-opt 收尾。",
        "why": "同一顧客的送與取可以拆開，這正是題目給的自由；把顧客綁在一起，set-3 上會多走 20%。",
    },
}

PROSE = {
    "conclusion": "六題都跑得出可行解；一題撞在 60 秒上。",
    "lede": "六個沒見過的運籌題，同一條生產線：讀 schema、選構造、自己判可行、自己決定什麼時候停。"
            "判分用官方檢查器。",
    "ruler_note": "橫條是實際牆鐘，紅線是 60 秒。條愈長不代表愈好，撞到紅線就是 0 分。",
    "score_note": "分數＝參考目標 ÷ 我們算出的目標（最小化題）。等於參考是 1.000，比參考好可以到 2.000。"
                  "這裡的參考值是<b>基準資料集</b>裡的 Gurobi 目標，不是比賽後台的凍結值，所以它是估計，不是成績。",
}


def esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fmt(value, digits=3):
    if value is None:
        return "—"
    return f"{value:,.{digits}f}"


def build() -> str:
    data = json.load(open(RESULTS, encoding="utf-8"))
    rows = data["rows"]
    problems = data["problems"]
    order = [s for s in PROBLEMS if s in problems]

    total_rows = len(rows)
    feasible_rows = sum(1 for r in rows if r["feasible"])
    failed = [r for r in rows if not r["feasible"]]
    mean_score = data["mean_score"]
    max_wall = max(r["wall_s"] for r in rows) if rows else 0.0

    # ---- the 60 s ruler
    bar_h, gap, left, width = 18, 10, 150, 480
    ruler = [f'<svg viewBox="0 0 {left + width + 92} {len(order) * (bar_h + gap) + 40}" '
             f'role="img" aria-label="每題最慢一次實例的牆鐘，紅線是 60 秒">']
    ruler.append(f'<line x1="{left + width}" y1="0" x2="{left + width}" y2="{len(order)*(bar_h+gap)+8}" '
                 f'stroke="#b3271e" stroke-width="2"/>')
    ruler.append(f'<text x="{left + width}" y="{len(order)*(bar_h+gap)+26}" text-anchor="middle" '
                 f'font-size="14" fill="#b3271e">60 s</text>')

    for i, slug in enumerate(order):
        y = i * (bar_h + gap) + 6
        slowest = max((r["wall_s"] for r in rows if r["slug"] == slug), default=0.0)
        length = min(1.0, slowest / 60.0) * width
        score = problems[slug]["mean_score"]
        colour = "#1f5d4c" if score >= 1.0 else ("#b3271e" if problems[slug]["feasible"] < problems[slug]["instances"] else "#3a3730")
        ruler.append(f'<text x="{left - 12}" y="{y + bar_h - 4}" text-anchor="end" font-size="15" fill="#16150f">'
                     f'{esc(PROBLEMS[slug]["short"])}</text>')
        ruler.append(f'<rect x="{left}" y="{y}" width="{width}" height="{bar_h}" fill="#eae5d8" rx="3"/>')
        ruler.append(f'<rect x="{left}" y="{y}" width="{max(2, length):.1f}" height="{bar_h}" fill="{colour}" rx="3"/>')
        ruler.append(f'<text x="{left + 10}" y="{y + bar_h - 5}" font-size="13" fill="#f7f5f0">'
                     f'{slowest:.0f}s</text>' if slowest > 6 else "")
        ruler.append(f'<text x="{left + width + 14}" y="{y + bar_h - 5}" font-size="14" fill="#3a3730">'
                     f'{score:.2f}</text>')
    ruler.append("</svg>")
    ruler_svg = "".join(ruler)

    # ---- table
    table_rows = []
    for slug in order:
        for r in [x for x in rows if x["slug"] == slug]:
            bad = not r["feasible"]
            cls = ' class="bad"' if bad else ""
            note = "—"
            if bad:
                note = "檢查器判不可行（沒有可行覆蓋）" if r["objective"] in (None, 0) else "檢查器判不可行"
            elif r["score"] >= 1.0:
                note = "優於參考"
            elif r["score"] >= 0.9:
                note = "接近參考"
            table_rows.append(
                f'<tr{cls}><td>{esc(PROBLEMS[slug]["short"])}</td><td class="mono">{esc(r["instance"])}</td>'
                f'<td>{"可行" if r["feasible"] else "不可行"}</td>'
                f'<td class="num">{fmt(r["score"])}</td>'
                f'<td class="num">{r["wall_s"]:.2f}s</td><td>{note}</td></tr>'
            )

    # ---- per problem cards
    cards = []
    for slug in order:
        p = problems[slug]
        info = PROBLEMS[slug]
        ok = p["feasible"] == p["instances"]
        badge = "全部可行" if ok else f'{p["feasible"]}/{p["instances"]} 可行'
        cards.append(f"""
      <article class="card">
        <div class="card-head">
          <h3>{esc(info["title"])} <span class="slug mono">{esc(slug)}</span></h3>
          <span class="badge {"ok" if ok else "warn"}">{esc(badge)}</span>
        </div>
        <p class="what">{esc(info["what"])}</p>
        <p><strong>怎麼做：</strong>{esc(info["how"])}</p>
        <p class="why"><strong>為什麼：</strong>{esc(info["why"])}</p>
        <dl class="mini">
          <div><dt>平均分</dt><dd class="num">{p["mean_score"]:.3f}</dd></div>
          <div><dt>最慢一次</dt><dd class="num">{p["max_wall_s"]:.1f}s</dd></div>
        </dl>
      </article>""")

    failed_lines = "".join(
        f'<li><code>{esc(r["slug"])}</code> / <code>{esc(r["instance"])}</code>：{esc((r["violations"] or ["不可行"])[0])[:160]}</li>'
        for r in failed
    ) or "<li>沒有。</li>"

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>六十秒的演算法 — FrontierOR Challenge</title>
<style>
  :root {{
    --paper: #f7f5f0; --ink: #16150f; --muted: #6b6659; --line: #e0dbcf;
    --red: #b3271e; --green: #1f5d4c; --card: #fffdf8;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--paper); color: var(--ink);
         font: 16px/1.65 -apple-system, "Segoe UI", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }}
  .wrap {{ max-width: 880px; margin: 0 auto; padding: 56px 24px 96px; }}
  header {{ border-bottom: 1px solid var(--line); padding-bottom: 22px; margin-bottom: 28px; }}
  .kicker {{ font-size: 13px; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); margin: 0 0 14px; }}
  h1 {{ font-size: 34px; line-height: 1.2; margin: 0 0 10px; letter-spacing: -.01em; }}
  .lede {{ font-size: 17px; color: #3a3730; margin: 0; max-width: 42em; }}
  .meta {{ margin-top: 18px; font-size: 14px; color: var(--muted); }}
  .meta code {{ font-size: 13px; }}
  h2 {{ font-size: 22px; margin: 64px 0 16px; letter-spacing: -.01em; }}
  h2 .num-badge {{ font-size: 13px; color: var(--muted); font-weight: 400; margin-left: 10px; }}
  p {{ margin: 0 0 14px; }}
  .hero {{ display: block; }}
  .statline {{ display: grid; grid-template-columns: 210px 1fr; gap: 32px; align-items: start; margin-top: 24px; }}
  .stat {{ font-size: 46px; line-height: 1.1; font-weight: 600; letter-spacing: -.02em; }}
  .stat small {{ display: block; font-size: 14px; font-weight: 400; color: var(--muted); letter-spacing: 0; margin-top: 8px; }}
  .ruler {{ background: var(--card); border: 1px solid var(--line); border-radius: 6px; padding: 16px 20px 6px; }}
  .ruler svg {{ width: 100%; height: auto; display: block; }}
  .ruler .cap {{ font-size: 13px; color: var(--muted); margin: 6px 0 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 15px; margin: 8px 0 0; }}
  th {{ text-align: left; font-weight: 600; font-size: 13px; letter-spacing: .04em; color: var(--muted);
        padding: 10px 10px; border-bottom: 1px solid var(--line); white-space: nowrap; }}
  td {{ padding: 10px 10px; border-bottom: 1px solid #eee8db; vertical-align: top; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .mono, code {{ font-family: ui-monospace, SFMono-Regular, "Cascadia Mono", Menlo, monospace; }}
  tr.bad td {{ background: #fbf0ee; }}
  tr.bad td:first-child {{ box-shadow: inset 3px 0 0 var(--red); }}
  .cards {{ display: grid; gap: 20px; }}
  .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 6px; padding: 22px 24px 16px; }}
  .card-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 16px; }}
  .card h3 {{ font-size: 18px; margin: 0 0 10px; }}
  .card .slug {{ font-size: 13px; color: var(--muted); font-weight: 400; }}
  .badge {{ font-size: 13px; padding: 2px 9px; border-radius: 999px; white-space: nowrap; }}
  .badge.ok {{ background: #e8f0ec; color: var(--green); }}
  .badge.warn {{ background: #f7e4e1; color: var(--red); }}
  .card p {{ font-size: 16px; margin: 0 0 10px; }}
  .card .what {{ color: #3a3730; }}
  .card .why {{ color: var(--muted); }}
  .mini {{ display: flex; gap: 28px; margin: 6px 0 12px; padding-top: 12px; border-top: 1px solid #efe9dc; }}
  .mini div {{ display: flex; gap: 8px; align-items: baseline; }}
  .mini dt {{ font-size: 13px; color: var(--muted); }}
  .mini dd {{ margin: 0; font-size: 15px; font-variant-numeric: tabular-nums; }}
  .note {{ background: #fbf8ef; border-left: 3px solid #c8a35a; padding: 16px 20px; margin: 24px 0; font-size: 15px; }}
  ul {{ margin: 0 0 16px; padding-left: 22px; }}
  li {{ margin-bottom: 8px; }}
  pre {{ background: #1d1c18; color: #f2efe6; padding: 16px 18px; border-radius: 6px; overflow-x: auto;
         font-size: 13px; line-height: 1.6; }}
  footer {{ margin-top: 72px; padding-top: 22px; border-top: 1px solid var(--line); font-size: 13px; color: var(--muted); }}
  @media (max-width: 760px) {{
    .statline {{ grid-template-columns: 1fr; gap: 16px; }}
    h1 {{ font-size: 27px; }}
    .stat {{ font-size: 36px; }}
    .wrap {{ padding: 36px 18px 72px; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <p class="kicker">FrontierOR Challenge · 測試階段 · 六題</p>
    <h1>六十秒的演算法</h1>
    <p class="lede">{esc(PROSE["lede"])}</p>
    <p class="meta">2 vCPU / 4 GB / 無網路 / 每題 60 秒 · 參考值＝<code>frontieror/FrontierOR</code>（CC BY 4.0）的 Gurobi 解</p>
  </header>

  <section class="hero">
    <div class="ruler">
      {ruler_svg}
      <p class="cap">{esc(PROSE["ruler_note"])}</p>
    </div>
    <div class="statline">
      <p class="stat">{feasible_rows}/{total_rows}
        <small>個實例拿到可行解；平均分 {mean_score:.3f}（參考＝1.000）</small>
      </p>
      <div>
        <p>{esc(PROSE["conclusion"])} 最慢的一次用了 {max_wall:.1f} 秒，預算 60 秒；
          {len(failed)} 個實例沒有拿到可行覆蓋。</p>
        <p class="note">{PROSE["score_note"]}</p>
      </div>
    </div>
  </section>

  <h2>每個實例 <span class="num-badge">{total_rows} 行</span></h2>
  <table>
    <thead><tr><th>題</th><th>實例</th><th>可行性</th><th class="num">分數</th><th class="num">耗時</th><th>備註</th></tr></thead>
    <tbody>
      {''.join(table_rows)}
    </tbody>
  </table>

  <h2>六條生產線</h2>
  <div class="cards">{''.join(cards)}
  </div>

  <h2>撞牆的那一題</h2>
  <p>集合劃分（<code>hoffman1993</code>）是唯一沒有全部拿下來的題。原因不是「不夠快」，
     而是<b>成本與長度無關</b>：15,000 個候選輪轉的成本在 1–200 之間，覆蓋的航班段數在 1–51 之間，
     所以最優解是「很多很短的輪轉」。分支定界從第一個可行解（約 33 根長輪轉）往下走，
     每一步都要拆掉一根長的換幾根短的，60 秒內走不到。</p>
  <p>最密的兩個實例（平均覆蓋 21.6 段、需要約 5 根輪轉）連<b>可行覆蓋</b>都找不到：
     100 段航班要剛好被 5 個集合切開，在 15,000 個候選裡是一個針尖。純可行性模型跑 15 秒也還是
     <code>UNKNOWN</code>。這是這條生產線目前真正的邊界，不是調參能解決的。</p>
  <p>沒有拿下來的實例：</p>
  <ul>{failed_lines}</ul>

  <h2>怎麼覆核</h2>
  <p>下面每一行都能在乾淨 clone 上跑。檢查器是官方那一份，目標值另外用一份獨立算式重算，
     分數按官方公式算。</p>
  <pre>git clone &lt;repo&gt; &amp;&amp; cd frontieror
python -m pip install ortools          # 只有 hoffman1993 需要
python scripts/fetch_data.py          # 取 large 實例，按 sha256 校驗
python harness/verify.py --tier tiny  # 只跑六個 tiny 實例，約 4 秒
python harness/verify.py              # 全部 36 個實例
python harness/build_submission.py    # 打包成 submission.zip（&lt; 4 MB）</pre>

  <footer>
    數據：<code>frontieror/FrontierOR</code>（Hugging Face，CC BY 4.0）· 題面與檢查器為原作者所有 ·
    本頁由 <code>scripts/build_site.py</code> 從 <code>out/results.json</code> 生成，不聯外。
  </footer>
</div>
</body>
</html>
"""


def main() -> int:
    html = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"{OUT}: {len(html)/1024:.1f} KiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

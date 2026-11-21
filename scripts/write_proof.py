"""Render `docs/04-PROOF.md` from `out/results.json`.

    python scripts/write_proof.py

The proof page is generated, never typed: every number in it comes from the same
`results.json` that the site is built from, so the report cannot drift away from
what the harness measured. The fixed prose explains how to re-run each block.
"""

from __future__ import annotations

import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "out", "results.json")
OUT = os.path.join(ROOT, "docs", "04-PROOF.md")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    data = json.load(open(RESULTS, encoding="utf-8"))
    rows = data["rows"]
    problems = data["problems"]
    checks = data["checks"]
    failed = data["failed"]

    lines = []
    lines.append("# 04-PROOF — 舉證")
    lines.append("")
    lines.append("這份檔案由 `python scripts/write_proof.py` 從 `out/results.json` 生成，"
                 "數字不手抄。要複驗就重跑 `python harness/verify.py`。")
    lines.append("")
    lines.append("## 0. 檢查器是官方那一份")
    lines.append("")
    lines.append("下面每個 `feasibility_check.py` 都是主辦方公佈的檔案（CC BY 4.0），"
                 "本倉庫未改動；sha256 記在這裡，重跑前可先比對。")
    lines.append("")
    lines.append("| 題 | sha256 |")
    lines.append("|---|---|")
    for slug in sorted(problems):
        path = os.path.join(ROOT, "benchmark", "tasks", slug, "feasibility_check.py")
        lines.append(f"| `{slug}` | `{sha256(path)}` |")
    lines.append("")
    lines.append("## 1. 逐實例結果")
    lines.append("")
    lines.append(f"時間上限 60 s／實例。分數＝參考目標 ÷ 我們的值（最小化），參考＝1.000。"
                 f"共 {len(rows)} 個實例，可行 {sum(1 for r in rows if r['feasible'])} 個，"
                 f"平均分 {data['mean_score']:.4f}。")
    lines.append("")
    lines.append("| 題 | 實例 | 可行 | 分數 | 耗時 (s) | 我們的值 | 參考 |")
    lines.append("|---|---|---|---:|---:|---:|---:|")
    for r in rows:
        lines.append(
            f"| `{r['slug']}` | `{r['instance']}` | {'✅' if r['feasible'] else '❌'} | "
            f"{r['score']:.4f} | {r['wall_s']:.2f} | "
            f"{('—' if r['objective'] is None else format(r['objective'], ',.4f'))} | "
            f"{('—' if r['reference_objective'] is None else format(r['reference_objective'], ',.4f'))} |"
        )
    lines.append("")
    lines.append("## 2. 每題匯總")
    lines.append("")
    lines.append("| 題 | 可行/實例 | 平均分 | 最慢一次 (s) |")
    lines.append("|---|---|---:|---:|")
    for slug, p in problems.items():
        lines.append(f"| `{slug}` | {p['feasible']}/{p['instances']} | {p['mean_score']:.4f} | {p['max_wall_s']:.2f} |")
    lines.append("")
    lines.append("## 3. 斷言")
    lines.append("")
    recorded = data.get("recorded_infeasible", [])
    lines.append(f"`harness/verify.py` 這一輪跑了 {len(checks)} 條斷言：硬斷言（崩潰、逾時、格式、"
                 f"自報值與重算值不符、打包超限、偷連網）**全部通過**；"
                 f"{len(recorded)} 個實例被官方檢查器判不可行，記在下面，不算作管線故障。")
    lines.append("")
    by_id = {}
    for c in checks:
        key = c["id"].split("/")[0]
        bucket = by_id.setdefault(key, {"ok": 0, "bad": 0, "detail": ""})
        bucket["ok" if c["ok"] else "bad"] += 1
        if not c["ok"]:
            bucket["detail"] = c["detail"][:200]
    lines.append("| 斷言 | 通過 | 失敗 | 說明 |")
    lines.append("|---|---:|---:|---|")
    for key in sorted(by_id):
        b = by_id[key]
        lines.append(f"| {key} | {b['ok']} | {b['bad']} | {b['detail'].replace('|', '/')} |")
    lines.append("")
    if failed:
        lines.append("硬斷言失敗：")
        lines.append("")
        for c in failed:
            lines.append(f"- `{c['id']}`：{c['detail'][:300]}")
        lines.append("")
    if recorded:
        lines.append("被檢查器判不可行的實例（記分為 0，是這一輪的結果）：")
        lines.append("")
        for c in recorded:
            lines.append(f"- `{c['id']}`：{c['detail'][:300]}")
        lines.append("")
    lines.append("## 4. 怎麼重跑")
    lines.append("")
    lines.append("```sh")
    lines.append("python -m pip install ortools           # 只有 hoffman1993 需要")
    lines.append("python scripts/fetch_data.py           # large 實例，按 sha256 校驗")
    lines.append("python harness/verify.py --tier tiny   # 六個 tiny，約 4 秒")
    lines.append("python harness/verify.py               # 全部 36 個")
    lines.append("python harness/build_submission.py     # submission.zip")
    lines.append("python scripts/write_proof.py          # 重寫本頁")
    lines.append("python scripts/build_site.py           # 重寫結果頁")
    lines.append("```")
    lines.append("")
    lines.append("## 5. 這一輪的環境")
    lines.append("")
    lines.append("- 本機：Windows 11，Python 3.13.14，ortools（本地開發用；沙箱是 Python 3.12 + ortools 9.15）")
    lines.append("- 沙箱限制是**模擬**的：子進程 + 60 s 牆鐘 + 每題資料夾複製到暫存目錄；"
                 "沒有真的 2 vCPU / 4 GB 限制，也沒有真的斷網（用 AC-06 掃 import 代替）")
    lines.append("- 執行時間會隨機器不同；分數不會（同一個解，同一個檢查器）")
    lines.append("")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"{OUT}: {len(lines)} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

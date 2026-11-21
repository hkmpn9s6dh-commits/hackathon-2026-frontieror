# 六十秒的演算法 — FrontierOR Challenge（賽道 AK）

六個運籌題、每題 60 秒、2 核、4 GB、沒有網路。這個倉庫是那條生產線：每題一支
`solve.py`（可以直接投 Main 賽道），加一條用**官方檢查器**驗可行性、獨立重算目標值、
按官方公式算分的管線。

- 比賽：<https://frontieror-challenge.com/>（FrontierOR / MIT；測試階段開到
  2026-12-27 23:59 EST，Stage 1 2027-01-04 起）
- 賽規與驗收：`SPEC.md`
- 舉證：`docs/04-PROOF.md`｜界面規格：`docs/07-UI.md`
- 結果頁：`site/index.html`（由 `scripts/build_site.py` 從 `out/results.json` 生成）

## 一眼看完

| 題 | 算法 | 可行/實例 | 平均分（參考＝1.000） |
|---|---|---|---|
| `cordeau2006` DARP | 最便宜可行插入 + 真時刻表 | 6/6 | 0.964 |
| `fischetti1998` OP（**最大化**） | 獎金/繞路插入 + 2-opt + 多輪重啟 | 6/6 | 0.865 |
| `barnhart2000` ODIMCF | 最寬路徑貪心 + 多種排序 | 6/6 | 0.940 |
| `hoffman1993` SPP | min-conflicts → 大鄰域 → CP-SAT | 4/6 | 0.421 |
| `bodur2017` SCFLP | 開倉集合刪除 + 貪心運輸 | 6/6 | 0.915 |
| `nagy2015` VRPDDP | 送/取拆成任務 + 節約法 + 2-opt | 6/6 | 0.942 |

全部 36 個實例：**34 可行、2 個記 0**，六題平均 **0.841**（每題等權再平均）。
表裡的數字每次 `python harness/verify.py` 會重寫 `out/results.json`，那份是準的。

**方向要緊**：六題裡只有定向越野是最大化，分數是「我們 ÷ 參考」；其餘五題是最小化，
分數是「參考 ÷ 我們」。搞反會把 0.80 寫成 1.25 —— 本輪真的寫反過一次，被盲審抓出來，
修法是把方向寫進 `harness/directions.py`，`scripts/merge_results.py` 一律重算分數。

## 跑

需要 Python 3.9+。只有 `hoffman1993` 用到 `ortools`；其餘五題是純標準庫。

```sh
python -m pip install ortools          # 只有 hoffman1993 需要
python scripts/fetch_data.py           # 取 large 實例（40 MB），按 sha256 校驗
python harness/verify.py --tier tiny   # 六個 tiny 實例，約 4 秒
python harness/verify.py               # 全部 36 個實例，約 25 分鐘（每題用滿 60 秒）
python harness/build_submission.py     # 打包 submission.zip（< 4 MB）
python scripts/build_site.py           # 重新生成結果頁
```

只跑某一題：

```sh
python harness/verify.py --slugs fischetti1998 --time-limit 60
```

單跑一次，像沙箱那樣（複製資料夾到暫存目錄、限時、量牆鐘）：

```sh
python harness/run_one.py --slug barnhart2000 \
  --instance data/large/barnhart2000/large_instance_1.json --time-limit 60
```

## 目錄

```
benchmark/tasks/<slug>/     checker、schema、題面、tiny 實例、參考目標值（進 Git，約 700 KB）
data/large/<slug>/          large 實例（不進 Git，由 scripts/fetch_data.py 按 sha256 取回）
solvers/<slug>/solve.py     提交物：每題一支，資料夾自足
common/orlib.py             共用：CLI、預算、寫解檔（打包時複製進每題資料夾）
harness/run_one.py          像沙箱那樣跑一次
harness/verify.py           全量驗證 + 計分 + 斷言（AC-01…AC-10）
harness/objective.py        獨立重算目標值（不採信 solver 自報的數）
harness/build_submission.py 打包，並回報大小
scripts/fetch_data.py       取 large 實例
scripts/build_site.py       生成結果頁
```

## 三件要說清楚的事

1. **分數是估計，不是成績。** 官方用「後台凍結的參考值」算分；我們手上只有基準資料集裡的
   Gurobi 目標值。所以 `score = 參考 ÷ 我們的值` 只在「參考值相同」時才等於官方分數。
   報告裡所有 >1 的數字都只說明那條參考解不是最優，不是我們贏了。
2. **可行性是官方判的。** `benchmark/tasks/<slug>/feasibility_check.py` 是主辦方公佈的
   「the code our evaluation runs on every solution」，原檔未改（sha256 在 `docs/04-PROOF.md`）。
3. **目標值是我們自己重算的。** `harness/objective.py` 用另一份算式從解的决定重算一遍，
   和 solver 自報的值對不上就判失敗（AC-04）。

## 授權

`benchmark/` 下的題面、schema、檢查器、實例與參考解來自
[`frontieror/FrontierOR`](https://huggingface.co/datasets/frontieror/FrontierOR)，
授權 **CC BY 4.0**；`solvers/` 與 `harness/` 是本倉庫的作品。

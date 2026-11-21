# SPEC — 賽道 AK《六十秒的演算法》 FrontierOR Challenge

寫在動手之前。上面每一條賽規都引自官方頁面（2026-11-20 抓取，原文在
`docs/sources/`），驗收條件寫成可執行的斷言，實現在 `harness/verify.py`。

## 一、這場比賽要什麼（原文）

**兩條賽道，分開排名**（`/docs` Overview）：

> Two tracks, scored separately … **Main**: You submit **Algorithm code, one folder
> per problem** … Runs on **Our sandbox: 2 vCPU, 4 GB, no network** … Dependencies
> **Open-source only** … Scored on **The Main track's private instances** … The
> leaderboard **Its own; the champion and the prizes come from this track**.

**這是一場「給 agent 的」比賽**（同頁）：

> Your team's agentic workflow designs an algorithm for each one, you submit them,
> and a leaderboard per track ranks the teams. **You may improve the workflow but
> not edit its algorithms by hand.**

**沙箱怎麼跑**（`/docs/main/submission-format`）：

```sh
python solve.py --problem barnhart2000 \
                --instance /work/in/instance.json \
                --output /work/out/solution.json \
                --time-limit 60
```

> The working directory is `/work/algorithm`, which holds your problem folder and is
> read-only. … **Finish before the limit.** An algorithm still running at its time
> limit is stopped and the instance scores 0, **even if it has already written a
> solution**. … It is at most **16 MB**.

**評分**（`/docs/main/scoring`）：

> A feasible solution scores the ratio of its objective to the instance's reference
> objective, a frozen checker-accepted value. **Matching the reference scores 1**, a
> worse solution less, and **a better one more, up to 2**. … Instance scores are
> averaged within each problem, then across problems, **so every problem weighs the
> same** however many instances it has.

**判據是公開的**（`/docs/problems`）：

> The problems of the testing stage and Stage 1 publish their checker: **the code our
> evaluation runs on every solution.** … `result.json` has `feasible`, `violations`,
> `reported_objective_value` and `computed_objective_value`; **the score uses the
> computed one.**

**時程**：測試階段開到 2026-12-27 23:59 EST（註冊與組隊同時截止，北京 12-28 13:59）；
Stage 1 2027-01-04～01-31 四輪每輪 15 題；Stage 2 2027-02-08～14。
獎金 $21,000（$10k / $5k / 3–6 名各 $1.5k）＋ Best New Problem、Best Write-Up。

## 二、測試階段六題與我們手上的東西

| slug | 題 | 規模 | 參考目標（Gurobi） |
|---|---|---|---|
| cordeau2006 | Dial-a-Ride | 36 用戶 / 4 車 / 6 座 | 313.18（tiny）、243.75–508.66（large） |
| fischetti1998 | Orienteering | 25 / 500 城 | 287（tiny）、9,528–25,982（large） |
| barnhart2000 | OD 整數多商品流 | 50 節點 / 130 弧 / 585 商品 | 64（tiny）、4,368–5,180（large） |
| hoffman1993 | 機組排班集合劃分 | 100 列 / 15,000 欄 | 16（tiny）、180–657（large） |
| bodur2017 | 隨機容量選址 | 50 設施 / 50 顧客 / 1,500 情境 | 74,706（tiny）、48,284–63,728（large） |
| nagy2015 | 可分割收送的 VRP | 199 顧客 / C=200 | 948（tiny）、3,423–13,986（large） |

數據來源 `frontieror/FrontierOR`（Hugging Face，**CC BY 4.0**），含題面、schema、
官方 `feasibility_check.py` 與 Gurobi 參考解。本倉庫提交其中 6 題（約 700 KB：
checker、schema、題面、tiny 實例、參考目標值）；large 實例 40 MB 由
`scripts/fetch_data.py` 按 sha256 取回，不進 Git。

## 三、要交什麼

`submission.zip`（≤4 MB）：每個 slug 一個資料夾，內含 `solve.py`，資料夾自足
（共用的 `orlib.py` 由 `harness/build_submission.py` 複製進去）。

## 四、驗收條件（可執行）

| 編號 | 條件 | 怎麼判 |
|---|---|---|
| AC-01 | 每個 solver 在 60 s 內正常退出（exit 0） | `harness/run_one.py` 子進程 + 牆鐘 |
| AC-02 | 牆鐘 < 時限（不是「幾乎」到點） | 同上，`wall_s < 60` |
| AC-03 | 官方 `feasibility_check.py` 判 `feasible=true` | 跑原檔，讀 `violations` |
| AC-04 | 自報 `objective_value` = 獨立重算值 | `harness/objective.py` 另寫一份算式 |
| AC-05 | 六題都有 `solve.py` | 打包後的 staged 目錄 |
| AC-06 | solver 不碰網路（沙箱沒有網路） | 正則掃 `import requests/urllib/socket/httpx` |
| AC-07 | 提交包 ≤ 4 MB | `build_submission.archive_size()` |
| AC-08 | 結果可由倉庫內檔案重現 | `benchmark/instances.json` 有每個實例的 sha256 與參考值 |
| AC-09 | 分數按官方公式算，且方向正確 | `harness/directions.py`（最小化＝參考÷我們；最大化＝我們÷參考），對照 `/docs/main/scoring` 原文 |
| AC-10 | 全新 clone 只照 README 能跑出同一結論 | 閘 C，見 `docs/04-PROOF.md` |

## 五、明確不做

- 不改官方 checker、不改實例檔（sha256 進 manifest，AC-08 驗）。
- 不引用 Gurobi 解當自己的輸出（Self-hosted 才交答案；Main 交代碼）。
- 不聲稱「最優」。參考值本身是 Gurobi 在平台上跑出來的值，我們只報「相對參考的比值」。
- 不在報告裡把「比參考好」寫成「比最優好」——比值 >1 只說明參考那一版不是最優。

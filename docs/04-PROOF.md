# 04-PROOF — 舉證

這份檔案由 `python scripts/write_proof.py` 從 `out/results.json` 生成，數字不手抄。要複驗就重跑 `python harness/verify.py`。

## 0. 檢查器是官方那一份

下面每個 `feasibility_check.py` 都是主辦方公佈的檔案（CC BY 4.0），本倉庫未改動；sha256 記在這裡，重跑前可先比對。

| 題 | sha256 |
|---|---|
| `barnhart2000` | `43de7c6d2520e9dd1257b7b1b79e4bf47dfee6a1fae22546adfbd933b113b1a7` |
| `bodur2017` | `77a6e2333ac8c732cd7243cb3241e55dbcbed38ee1b16f33cb26fdaea5732a39` |
| `cordeau2006` | `2b177d20faa563eec61abe23a069a8fd5b0b5af72459fca17e1ee5390f338d94` |
| `fischetti1998` | `9a90c7c4f20adc78a9dc62acfaabac6760527928f6e846aac6d6bd1b6bdb3318` |
| `hoffman1993` | `321bff76bf51fcf30ff66d2847ac376a568dda5861d2a8a4e63605c6063039dd` |
| `nagy2015` | `ad3121d2feaba6359a204847897fd2a02e1044e1f07ea168cc6cd491f1088671` |

## 1. 逐實例結果

時間上限 60 s／實例。分數＝參考目標 ÷ 我們的值（最小化），參考＝1.000。共 36 個實例，可行 34 個，平均分 0.8912。

| 題 | 實例 | 可行 | 分數 | 耗時 (s) | 我們的值 | 參考 |
|---|---|---|---:|---:|---:|---:|
| `barnhart2000` | `large_instance_1` | ✅ | 0.9167 | 7.34 | 5,401.0000 | 4,951.0000 |
| `barnhart2000` | `large_instance_2` | ✅ | 0.9108 | 8.50 | 4,796.0000 | 4,368.0000 |
| `barnhart2000` | `large_instance_3` | ✅ | 0.9277 | 9.81 | 5,143.0000 | 4,771.0000 |
| `barnhart2000` | `large_instance_4` | ✅ | 0.9589 | 7.63 | 5,402.0000 | 5,180.0000 |
| `barnhart2000` | `large_instance_5` | ✅ | 0.9245 | 7.14 | 5,150.0000 | 4,761.0000 |
| `barnhart2000` | `tiny_instance` | ✅ | 1.0000 | 0.65 | 64.0000 | 64.0000 |
| `bodur2017` | `large_instance_1` | ✅ | 0.8921 | 11.53 | 71,434.0162 | 63,727.5266 |
| `bodur2017` | `large_instance_2` | ✅ | 0.8818 | 6.05 | 61,838.5811 | 54,529.7619 |
| `bodur2017` | `large_instance_3` | ✅ | 0.9037 | 3.19 | 53,429.5254 | 48,283.7085 |
| `bodur2017` | `large_instance_4` | ✅ | 0.9857 | 15.04 | 49,196.9609 | 48,495.8834 |
| `bodur2017` | `large_instance_5` | ✅ | 0.9791 | 15.84 | 51,655.7597 | 50,576.0209 |
| `bodur2017` | `tiny_instance` | ✅ | 0.8495 | 1.17 | 87,943.1278 | 74,706.0899 |
| `cordeau2006` | `large_instance_1` | ✅ | 0.9599 | 23.01 | 517.9179 | 497.1260 |
| `cordeau2006` | `large_instance_2` | ✅ | 0.9617 | 42.85 | 342.6981 | 329.5572 |
| `cordeau2006` | `large_instance_3` | ✅ | 0.9539 | 26.56 | 255.5429 | 243.7504 |
| `cordeau2006` | `large_instance_4` | ✅ | 0.9636 | 42.69 | 527.8584 | 508.6630 |
| `cordeau2006` | `large_instance_5` | ✅ | 0.9534 | 1.78 | 137.4938 | 131.0897 |
| `cordeau2006` | `tiny_instance` | ✅ | 0.9933 | 5.06 | 315.3020 | 313.1849 |
| `fischetti1998` | `large_instance_1` | ✅ | 1.2487 | 51.73 | 13,925.0000 | 17,388.0000 |
| `fischetti1998` | `large_instance_2` | ✅ | 1.2839 | 14.94 | 7,421.0000 | 9,528.0000 |
| `fischetti1998` | `large_instance_3` | ✅ | 1.2206 | 55.22 | 16,524.0000 | 20,169.0000 |
| `fischetti1998` | `large_instance_4` | ✅ | 1.1638 | 55.21 | 20,079.0000 | 23,368.0000 |
| `fischetti1998` | `large_instance_5` | ✅ | 1.0767 | 55.21 | 24,131.0000 | 25,982.0000 |
| `fischetti1998` | `tiny_instance` | ✅ | 1.0000 | 0.17 | 287.0000 | 287.0000 |
| `hoffman1993` | `large_instance_1` | ✅ | 0.3103 | 54.95 | 2,117.0000 | 657.0000 |
| `hoffman1993` | `large_instance_2` | ✅ | 1.0000 | 1.45 | 229.0000 | 229.0000 |
| `hoffman1993` | `large_instance_3` | ✅ | 0.2127 | 54.31 | 973.0000 | 207.0000 |
| `hoffman1993` | `large_instance_4` | ❌ | 0.0000 | 54.80 | 0.0000 | 331.0000 |
| `hoffman1993` | `large_instance_5` | ❌ | 0.0000 | 55.07 | 0.0000 | 180.0000 |
| `hoffman1993` | `tiny_instance` | ✅ | 1.0000 | 0.98 | 16.0000 | 16.0000 |
| `nagy2015` | `large_instance_1` | ✅ | 1.0201 | 1.13 | 13,711.0000 | 13,986.0000 |
| `nagy2015` | `large_instance_2` | ✅ | 0.9215 | 3.66 | 3,963.0000 | 3,652.0000 |
| `nagy2015` | `large_instance_3` | ✅ | 1.0120 | 0.73 | 13,202.0000 | 13,361.0000 |
| `nagy2015` | `large_instance_4` | ✅ | 0.8637 | 2.67 | 3,963.0000 | 3,423.0000 |
| `nagy2015` | `large_instance_5` | ✅ | 1.0037 | 0.60 | 13,711.0000 | 13,762.0000 |
| `nagy2015` | `tiny_instance` | ✅ | 0.8301 | 0.26 | 1,142.0000 | 948.0000 |

## 2. 每題匯總

| 題 | 可行/實例 | 平均分 | 最慢一次 (s) |
|---|---|---:|---:|
| `barnhart2000` | 6/6 | 0.9398 | 9.81 |
| `bodur2017` | 6/6 | 0.9153 | 15.84 |
| `cordeau2006` | 6/6 | 0.9643 | 42.85 |
| `fischetti1998` | 6/6 | 1.1656 | 55.22 |
| `hoffman1993` | 4/6 | 0.4205 | 55.07 |
| `nagy2015` | 6/6 | 0.9418 | 3.66 |

## 3. 斷言

`harness/verify.py` 這一輪跑了 166 條斷言：硬斷言（崩潰、逾時、格式、自報值與重算值不符、打包超限、偷連網）**全部通過**；2 個實例被官方檢查器判不可行，記在下面，不算作管線故障。

| 斷言 | 通過 | 失敗 | 說明 |
|---|---:|---:|---|
| AC-01 | 36 | 0 |  |
| AC-02 | 36 | 0 |  |
| AC-03 | 34 | 2 | checker rejected: empty required decision witness field(s): selected_rotations |
| AC-04 | 34 | 0 |  |
| AC-05 | 6 | 0 |  |
| AC-06 | 6 | 0 |  |
| AC-07 | 6 | 0 |  |
| AC-08 | 6 | 0 |  |

被檢查器判不可行的實例（記分為 0，是這一輪的結果）：

- `AC-03/hoffman1993/large_instance_4`：checker rejected: empty required decision witness field(s): selected_rotations
- `AC-03/hoffman1993/large_instance_5`：checker rejected: empty required decision witness field(s): selected_rotations

## 4. 怎麼重跑

```sh
python -m pip install ortools           # 只有 hoffman1993 需要
python scripts/fetch_data.py           # large 實例，按 sha256 校驗
python harness/verify.py --tier tiny   # 六個 tiny，約 4 秒
python harness/verify.py               # 全部 36 個
python harness/build_submission.py     # submission.zip
python scripts/write_proof.py          # 重寫本頁
python scripts/build_site.py           # 重寫結果頁
```

## 5. 這一輪的環境

- 本機：Windows 11，Python 3.13.14，ortools（本地開發用；沙箱是 Python 3.12 + ortools 9.15）
- 沙箱限制是**模擬**的：子進程 + 60 s 牆鐘 + 每題資料夾複製到暫存目錄；沒有真的 2 vCPU / 4 GB 限制，也沒有真的斷網（用 AC-06 掃 import 代替）
- 執行時間會隨機器不同；分數不會（同一個解，同一個檢查器）

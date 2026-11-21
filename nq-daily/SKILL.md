---
name: nq-daily
description: Run the NowQuant daily data pipeline end to end — pull new Databento hourly bars with nfetch, load them into NQLake, export the mmap file, and run nqhpc to refresh out/. Use whenever the user asks to pull, fetch, or update Databento or market data and run the pipeline, e.g. "拉一下昨天的数据", "跑一遍管线", "更新数据", "daily run", "refresh the lake", "把今天的 bar 补上", even when they name only one stage (nfetch, nqlake upload, mmap, nqhpc run) of the daily update. Also use to check which days are missing from the lake.
---

# NQ 每日管线

一次运行把湖里缺的 UTC 整天补齐，然后重算 `out/`。

| 步 | 程序 | 目录 | 产物 |
|---|---|---|---|
| 1 定窗口 | `scripts/daily.py plan` | 本 Skill | 改好的 `daily_ohlcv1h.toml` |
| 2 下载 | `build/nfetch download` | `~/Containers/apps/nfetch` | `datasets/XNAS.ITCH/ohlcv-1h/[QQQ/]YYYY-MM-DD.dbn.zst` |
| 3 转换 | `build/nfetch convert` | 同上 | 同名 `.parquet` |
| 4 入湖 | `nqlake upload` | `~/Containers/apps/lakehouse` | 表 `market.us_equity_ohlcv` |
| 5 导出 | `nqlake mmap` | `~/Containers/apps/nqhpc` | `~/.nqlake/mmap.arrow` |
| 6 计算 | `build/nqhpc run` | 同上 | `out/1h.parquet`、`out/xs.parquet`、`out/instruments.parquet` |

`nqlake` 指 `~/Containers/apps/lakehouse/target/universal/stage/bin/nqlake`，运行前 `export JAVA_HOME=/opt/homebrew/opt/openjdk@21`。

## 不重复下载的规则

- 下载是付费请求，而且 nfetch 每次运行都会重下配置窗口里的全部文件。窗口必须只含缺的天。
- 窗口由 `daily.py plan` 算，不手填：`start` = 湖和本地日文件里最晚的一天 + 1，`end` = 今天的 UTC 日期（不含）。
- `plan` 只改配置顶层的 `start` 和 `end`。symbols、dataset、schema、split 归用户改。
- `plan` 输出 `nothing to download` 时跳过第 2 步，从第 3 步接着做。本地可能还有没入湖的文件。
- 用户点名要重下某天（例如修数据）时才手改窗口，并先把要重下的天和 dry-run 费用告诉用户。
- Databento 只给完整的 UTC 日。nfetch 会把 `end` 收回到 Databento 已有的最后一天，所以当天和未发布的昨天下不到。这种情况如实报告，不重试。

## 步骤

### 0 环境

```bash
docker ps --filter name=nqlake-seaweedfs-1 --format '{{.Status}}'
```

- 没有 `healthy`：在 `lakehouse` 里 `docker compose up -d --wait`。
- 缺 `nqlake` 可执行文件：在 `lakehouse` 里 `sbt stage`。
- 缺 `nfetch/build/nfetch`：`cmake -S . -B build && cmake --build build -j`。

### 1 定窗口

```bash
python3 ~/.claude/skills/nq-daily/scripts/daily.py plan
```

`plan --check` 只打印窗口，不写配置。

### 2 下载

```bash
cd ~/Containers/apps/nfetch
build/nfetch download --dry-run daily_ohlcv1h.toml
build/nfetch download -y --max-cost 0.10 daily_ohlcv1h.toml
```

- 一天约 $0.003。dry-run 总价超过 $0.10 时停下问用户，窗口多半算错了。
- 周末和假日的文件报 `no data`，属正常。周六 UTC 有一根周五盘后的 00:00 bar。
- 退出码 1：读 `datasets/manifest.json` 里的原因，报告后停下。

### 3 转换，4 入湖

```bash
python3 ~/.claude/skills/nq-daily/scripts/daily.py pending
```

`pending` 列出湖里还没有的本地日文件。这份清单同时是转换和入湖的清单，所以上次下载了但没入湖的文件也会补上。清单为空就跳到第 5 步。

```bash
build/nfetch convert <清单里的每个 .dbn.zst>
nqlake upload -y --table us_equity_ohlcv <对应的每个 .parquet>
```

- 逐个文件转换。对目录转换会重写历年的 Parquet。
- 所有 Parquet 放进一次 `upload`。记下输出里的 `rows=` 和 `table_rows=`。
- 入湖后再跑一次 `pending`，应为空。

### 5 导出，6 计算

```bash
cd ~/Containers/apps/nqhpc
nqlake mmap -y --sql-file plugins/adapters/nqlake_ohlcv/mmap.sql
cmake --build build -j
build/nqhpc run --adapter build/plugins/adapters/nqlake_ohlcv.so \
                --plugin build/plugins/features/ta_ohlcv.so \
                --sampler 1h=time:1h --cross xs=ta_ohlcv:1h
```

- 这是默认运行：全历史，无 `warmup_until`。用户给了别的采样器或参数就照用户的。
- 湖里没有新行且用户没改代码时，第 5、6 步的结果和上次相同。告诉用户，问是否仍要重跑。
- `run` 覆盖 `out/`。不提交任何文件。

### 7 核对

```bash
duckdb -c "SELECT count(*) n, count(DISTINCT symbol) syms, to_timestamp(max(ts)/1e9) hi FROM 'out/1h.parquet'"
```

- `hi` 应是最新入湖那天最后一根 bar 的结束时刻。
- `out/1h.parquet` 的行数 = mmap 行数 − 适配器报告跳过的 bar 数。

## 报告

第一句说补了哪几天、`out/` 更新到什么时刻。然后一张表：每步一行，列出花费、新增行数、表总行数、mmap 行数、运行耗时和退出码。再列适配器跳过的 bar 数，以及没下到的天和原因。

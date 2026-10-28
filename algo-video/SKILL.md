---
name: algo-video
description: Make or revise one episode of the user's Chinese algorithm-explainer video series (算法竞赛基础系列) from their improvised voice recordings — Three.js animation synced to the voice, Tone.js sound, ffmpeg export, using the shared engine at /Volumes/T7/video/engine. Use whenever the user asks to make a new episode, re-cut, re-time, fix animations or subtitles, or render a draft/final for a video under /Volumes/T7/video.
---

# 算法讲解视频：工作流

引擎：`/Volumes/T7/video/engine/`（共享）。每期一个文件夹，例如 `/Volumes/T7/video/Oct 27 Prefix Sum/`（第 1 期，可作为写场景的范例）。
一键命令：`/Volumes/T7/video/engine/bin/ep <命令> <这一期的文件夹>`，`ep help` 看全部。

## 用户的固定要求
- 录屏里的画面只是他念稿时看的提词，**绝不进成片**；只用音频。
- 1080p60 横屏、深色科技风、字幕烧录进画面并另出 SRT、段与段之间有章节卡。
- 剪掉口误之前先列出来给他确认；成片前他自己改 `script/字幕.txt`。
- 依赖版本只用发布满两周的（npm 选旧一点的版本；pip 用 `uv pip install --exclude-newer <两周前日期>`）。

## 新一期的流程
1. `ep new "<文件夹>"`，改 `episode.json`（标题、英文标题、期数、小结要点、本期热词）。用户把录屏 .mov 放进去，按文件名排序就是段落顺序。
2. `ep asr <文件夹>`：Whisper 出文字，Paraformer（FunASR）逐字对齐时间，Silero VAD 判断人声起止。输出 `script/transcript.json`（每句带 `chars` 逐字时间）、`script/识别报告.md`、自动生成的 `script/edl.json`。
3. **读识别报告**，把要用户确认的列给他：两个模型听得不一样的词、可能的幻听或漏识别、口误重复（附时间）。修正写进 `script/fixes.json`（`{"fix": [[正则, 替换]], "drop": [句子编号]}`）后重跑 `ep asr <文件夹> --force`。可以跨期复用的错字写进 `engine/glossary.json`。
4. 在 `edl.json` 里写章节卡（`"card": {"no": "01", "title": "…"}`）和要剪的片段（`cuts: [[起, 止]]`，原录音秒数），然后跑 `ep voice <文件夹>`，生成人声、`timeline.json` 和 `字幕.txt`。
5. 写场景：`scenes/index.js` 列出各段，每段一个 `segNN.js`（参考第 1 期和 `engine/template/scenes/seg01.js`）。
6. `ep preview <文件夹>` 开预览（端口 5177）；`ep snap <文件夹> out.png 时间...` 出联系表自查；`ep check <文件夹>` 自动查排版重叠和音轨时长，必须做到 0 处。
7. `ep draft <文件夹>`（540p30，约 2 分钟）给用户看；他改完字幕后 `ep final <文件夹>`（约 10 分钟）。

## 写场景的规则
- `update(t)` 必须是 t 的**纯函数**：每帧把状态整体写一遍，不累积上一帧的状态。否则拖动预览和逐帧渲染会对不上。
- 时间点从文稿取，不写死秒数：`say(段号, '关键词', 第几次)`，或 `word('s03.008', 'L-1')`、`at('s03.008', 0.5)`。有 `chars` 时用的是逐字实测时间。
- 3D 物体用 `Cells`（一排数组格子）、`SpanBar`（区间长条）、`Grid`（二维网格）、`makeLink`（粗线）。文字、公式、代码放 HTML 叠加层：`el()`、`tex()`（KaTeX）、`code()`（Shiki，每行 class `ln`，用 `hotLine` 高亮），用 `fade` / `pose` / `stick` 控制。
- 底部约 960px 往下是字幕区，公式最低放到 y≈860。
- 音效写在场景返回值的 `sfx: [{t, kind, step?}]` 里，kind 可选 whoosh、rise、impact、chime、pop、tick、stack、note。

## 踩过的坑（别再踩）
- **Whisper 会在段尾编出重复句子，时间戳也量化、偏早。** asr.py 用 Paraformer 和 VAD 交叉验证，段尾幻听会自动删除；报告里仍然要看。剪辑点绝不能只凭 Whisper 的时间。
- Paraformer 会把英文和代码术语听成音译（栏姆达、四加加），数字写成汉字，所以文字用 Whisper，Paraformer 只负责时间和口误检测。SenseVoice 也试过，术语更差。
- 渲染时 Vite 不能监视 `work/`，写文件会触发页面重载（`scripts/lib.mjs` 已关闭 hmr 和 watch）。shell 管道里的步骤要用 `pipefail`，否则失败会被吞掉。
- `brew install` 可能升级共享库、弄坏 Homebrew 的 node；装完检查 `node -v`，坏了就 `brew upgrade node`。
- Claude App 自带的预览启动器在 T7（exFAT 移动硬盘）上会卡住：用 `ep preview` 在后台起服务，再用 launch.json 里只写 url 的配置连上去。exFAT 不能建软链接，venv 放在 `~/.venvs/`。
- 叠加层 CSS：`#overlay > *` 设了 nowrap，代码卡的 `pre` 要用 `#overlay .code` 才能覆盖回来。
- Homebrew 的 ffmpeg 没有 drawtext、libass；字幕在网页里画。
- 降噪默认 RNNoise（`episode.json` 的 `"denoise"`）；DeepFilterNet 在 `~/.venvs/dfn`，可选 `"dfn"`。

## 环境
- Python：`~/.venvs/algo-video`（3.12：funasr、silero-vad、numpy、opencc）、`~/.venvs/dfn`（3.11：deepfilternet）。
- 模型：`/Volumes/T7/video/models/`（Whisper large-v3-turbo、RNNoise）；FunASR 模型在 `~/.cache/modelscope`。
- Node 依赖在 `/Volumes/T7/video/node_modules`（各期共用）。Chrome 在 `/Applications/Google Chrome.app`。

---
name: video-studio
description: Make or revise a video from the user's improvised voice recordings, on any topic — speech recognition into a proofread script, Three.js animation synced to the voice, Tone.js sound, ffmpeg export, using the shared engine at /Volumes/T7/video/engine. Use whenever the user asks to start a new video or episode, proofread a transcript, cut, re-time, fix animations or subtitles, adjust sound, or render a draft/final for anything under /Volumes/T7/video.
---

# 视频制作：工作流

引擎：`/Volumes/T7/video/engine/`（共享）。每个视频一个文件夹（下文叫「一期」），例如 `/Volumes/T7/video/Oct 27 Prefix Sum/`（一期算法讲解，可作为写场景的范例）。
一键命令：`/Volumes/T7/video/engine/bin/ep <命令> <这一期的文件夹>`，`ep help` 看全部。

## 不随题材变的约定
- 用户对着提词即兴口述并录屏；录屏画面只是提词，**绝不进成片**，只用音频。画面全部由场景生成。
- 引擎目前固定输出 1080p60 横屏、深色风格；字幕烧录进画面，另出 SRT。
- **识别完先由 Claude 做第一轮校对**：能确定的直接改，拿不准的用 ？ 标给用户；然后停下来让用户校对，用户说校对好了才往下做剪辑、人声和场景。
- 剪掉口误之前先列出来给用户确认；成片前用户还可以再改一遍 `script/字幕.txt`。
- 依赖版本只用发布满两周的（npm 选旧一点的版本；pip 用 `uv pip install --exclude-newer <两周前日期>`）。

## 每期自己定的（episode.json）
- `title` 必填；`titleEn`、`series`、`episode`（期数）、`summary`（片尾要点）、`outroText`（片尾最后一句，默认「感谢观看」）都可以不写，不写片头片尾就不显示那一项。
- `glossaries`：选题材术语表，比如 `["算法"]`；`通用` 每期都自动带上。新题材没有合适的表，就建 `engine/glossaries/<题材>.json`（`hotwords` + `fix`）。`hotwords` 写这一期独有的词。
- 声音：`denoise`（rnnoise / dfn / none）、`denoise_db`（默认 16）、`loudness`（成片目标 LUFS，默认 -14）、`bgm_level`（默认 1.6）、`sfx_level`（默认 0.9）。用户通常在「视频项目」面板里调。
- 章节卡在 `script/edl.json` 每段的 `card` 里，可有可无；先问用户这一期要不要分章节。
- `edl.json` 的 `hold`（新一期默认 2 秒）：每段说完后画面停留的时间，让观众看清这一段最后的画面再转场；场景里收尾的元素要显示到 `seg.t1`。

## 新一期的流程
1. `ep new "<文件夹>"`，和用户确认标题、题材（选哪个术语表）、要不要系列名和期数，写进 `episode.json`。用户把录屏放进这一期的 `source/`（mov / mp4 / m4a / wav / mp3），按文件名排序就是段落顺序。源文件只读，不改不删。
2. `ep asr <文件夹>`：Whisper 出文字，Paraformer（FunASR）逐字对齐时间，Silero VAD 判断人声起止。输出 `script/校对.txt`（可疑处以 `#   ⚠` 标在对应句子上面）、`script/transcript.json`（每句带 `chars` 逐字时间）、自动生成的 `script/edl.json`。
3. **Claude 初校**：从头到尾读一遍 `script/校对.txt`，结合上下文和这一期题材的知识判断。⚠ 处每一条都要处理，其余句子也要看。
   - 能确定的错字、术语、漏字、标点：直接改，写明理由。
   - 拿不准的（听不清的词、可能是口误、两种说法都通）：写成一个具体的问题，比如「是『原理』还是『定义』？」。不要猜着改。
   - 用户说的话照原样保留：口头禅、自我修正不删，只改识别错的字。
   - 写成 `script/初校.json`（`[{"id", "text"?, "why"?, "ask"?}]`；只写 id 表示看过、没问题），然后 `ep review <文件夹>`。句子上方会出现 ✎（改过的）和 ？（要用户确认的）标记，⚠ 视为已处理。
4. **停下来让用户校对**：告诉用户改了几句、有几处 ？，请用户在「视频项目」面板的文稿页处理。面板会先列出 ？ 句，每句可以 ▶ 播放、直接改、或点 ✓ 表示没问题。不要替用户回答 ？，也不要先写场景。用户说校对好了，跑 `ep proof <文件夹>` 写回识别稿（改过的句子重新对齐逐字时间，原文留在 `asr` 字段），看一眼改动列表：同类错字以后还会出现的，加进对应的 `engine/glossaries/*.json`。要重新识别（`ep asr --force`）时，原识别文字没变的句子会自动沿用用户的校对，带不过去的会列出来，旧文件在 `校对.旧.txt`。
5. 在 `edl.json` 里写章节卡（如果要）和要剪的片段（`cuts: [[起, 止]]`，原录音秒数），先列给用户确认，然后跑 `ep voice <文件夹>`（会先自动写回校对），生成人声、`timeline.json` 和 `字幕.txt`（默认就是校对后的文字）。
6. 写场景（在校对之后写，`say()` 找的词是校对后的文字）：`scenes/index.js` 列出各段，每段一个 `segNN.js`（参考 `engine/template/scenes/seg01.js` 和已有的各期）。先想清楚每段要让观众看懂什么，再选画面。
7. `ep preview <文件夹>` 开预览（端口 5177）；`ep snap <文件夹> out.png 时间...` 出联系表自查；`ep check <文件夹>` 自动查排版重叠和音轨时长，必须做到 0 处。
8. `ep listen <文件夹>` 出 20 秒试听；`ep draft <文件夹>`（540p30，约 2 分钟）给用户看；用户改完字幕后 `ep final <文件夹>`（9 分钟的片子约 3 分钟）。出片后扫一遍有没有单帧或短暂的画面跳变（相邻帧差异大、随后又跳回去）。

## 写场景的规则
- `update(t)` 必须是 t 的**纯函数**：每帧把状态整体写一遍，不累积上一帧的状态。否则拖动预览和逐帧渲染会对不上。
- 时间点从文稿取，不写死秒数：`say(段号, '关键词', 第几次)`，或 `word('s03.008', '词')`、`at('s03.008', 0.5)`。有 `chars` 时用的是逐字实测时间。
- 现成的积木在 `engine/web/core/`：3D 的 `Cells`（一排格子）、`SpanBar`（横跨几格的长条）、`Grid`（二维网格）、`makeLink`（粗线）、`textTexture`（文字贴图）；HTML 叠加层的 `el()`、`tex()`（KaTeX 公式）、`code()`（Shiki 代码，目前只装了 C++，每行 class `ln`，用 `hotLine` 高亮）；动画用 `fade` / `pose` / `stick` 和 `anim.js` 的缓动。题材需要新的积木（图表、地图、时间线……）时，通用的写进 `engine/web/core/`，只这一期用的留在这一期的 `scenes/`。
- 底部约 960px 往下是字幕区，内容最低放到 y≈860。
- 音效写在场景返回值的 `sfx: [{t, kind, step?}]` 里，kind 可选 whoosh、rise、impact、chime、pop、tick、stack、note。

## 踩过的坑（别再踩）
- **Whisper 会在段尾编出重复句子，时间戳也量化、偏早。** asr.py 用 Paraformer 和 VAD 交叉验证，段尾幻听会自动删除；校对稿里仍然要看。剪辑点绝不能只凭 Whisper 的时间。
- Paraformer 会把英文和专业术语听成音译（栏姆达、四加加），数字写成汉字，所以文字用 Whisper，Paraformer 只负责时间和口误检测。SenseVoice 也试过，术语更差。
- 渲染时 Vite 不能监视 `work/`，写文件会触发页面重载（`scripts/lib.mjs` 已关闭 hmr 和 watch）。shell 管道里的步骤要用 `pipefail`，否则失败会被吞掉。
- `brew install` 可能升级共享库、弄坏 Homebrew 的 node；装完检查 `node -v`，坏了就 `brew upgrade node`。
- Claude App 自带的预览启动器在 T7（exFAT 移动硬盘）上会卡住：用 `ep preview` 在后台起服务，再用 launch.json 里只写 url 的配置连上去。exFAT 不能建软链接，venv 放在 `~/.venvs/`。
- **逐帧截图的速度和正确性**（`scripts/lib.mjs`、`render.mjs`）：时间几乎全花在 `Page.captureScreenshot` 上，画一帧只要 1.5ms。
  - 关垂直同步和帧率上限（`--disable-gpu-vsync --disable-frame-rate-limit`）后单页约 60 fps。
  - 每个 worker 一个独立的 Chrome，6 个约 220 fps；几个页面共用一个 Chrome 时截图在浏览器进程里排队，总速度卡在约 100 fps，开页还慢、偶尔卡死。
  - 新版无头 Chrome 有真窗口，关掉一个页面时别的页面会短暂套用 Retina 的 2 倍像素比，那几帧被放大到左上角（第 1 期出过）。现在固定 `--force-device-scale-factor=1`、页面等全部画完再关、每帧检查 `devicePixelRatio`。
  - 关浏览器和 node 退出都可能卡住：最多等 2 秒就杀掉进程，脚本最后 `process.exit`。
  - 用 Chrome 实时录制（MediaRecorder、标签页录制）最快也只是实时，还会掉帧；screencast 推来的帧和 seek 对不上号，只有 JPEG。所以不用录制，用逐帧截图。
- 叠加层 CSS：`#overlay > *` 设了 nowrap，代码卡的 `pre` 要用 `#overlay .code` 才能覆盖回来。
- Homebrew 的 ffmpeg 没有 drawtext、libass；字幕在网页里画。
- 降噪设置一变，`ep listen / check / draft / final` 会按 `work/voice.json` 自动重新生成人声；按新引擎重新生成人声后片长可能变（剪辑点改按人声检测），动画跟着句子编号走，重跑 `ep check` 就行。

## 视频项目面板（Claude Code mod）
- `video-projects` mod：每一期的进度、下一步、声音旋钮（写 episode.json）、在面板里改校对稿和字幕（逐句播放原声）、上下文和用量。已装成正式插件 `video-projects@local-mods`（本地插件源，直接读 `~/.claude/mods/video-projects/`），命令 `/videos`。改这个文件夹里的代码后要 `/reload-plugins` 才生效；用户要开关就在桌面 App 的 + → Plugins 里，或 `claude plugin disable|enable video-projects@local-mods`。改完先跑 `claude plugin validate` 和 `claude plugin test`。
- 用户点面板上的按钮会以用户的口吻发来一句话（比如「……的 校对.txt 我校对好了，继续」），照常接着做。

## 环境
- Python：`~/.venvs/algo-video`（3.12：funasr、silero-vad、numpy、opencc；名字是历史原因，所有视频共用）、`~/.venvs/dfn`（3.11：deepfilternet）。
- 模型：`/Volumes/T7/video/models/`（Whisper large-v3-turbo、RNNoise）；FunASR 模型在 `~/.cache/modelscope`。
- Node 依赖在 `/Volumes/T7/video/node_modules`（各期共用）。Chrome 在 `/Applications/Google Chrome.app`。

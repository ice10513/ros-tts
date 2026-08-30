# AGENTS.md

面向本仓库的 Agent 说明。修改代码前先读 `speaker.py` 与 `tts-models/` 的实际路径，不要假设已存在 ROS 节点或 VITS 模型。

## 项目是什么

独立离线 TTS 脚本：用 `sherpa-onnx` 加载本地 ONNX 模型，用 `sounddevice` 播放。仓库名含 `ros`，但当前没有 `package.xml`、launch 或 ROS 节点。

入口：`speaker.py`。模型根目录：`tts-models/`（相对脚本文件，不要改成 cwd 相对路径）。

## 目录约定

- `speaker.py`：CLI 与引擎实现，保持单文件，除非明确要求拆包。
- `tts-models/matcha-icefall-zh-en/`：Matcha 声学模型、`tokens.txt`、`lexicon.txt`、`espeak-ng-data/`。
- `tts-models/vocos-16khz-univ.onnx`：Matcha 必需的 vocoder。
- `tts-models/vits-piper-zh_CN-huayan-medium/`：可选 VITS；目录不存在则跳过，不要当硬错误。
- `requirements.txt` / `deploy.sh`：依赖清单与安装入口。不要把依赖写死在文档里却不更新这两个文件。

不要提交或改动 `espeak-ng-data/` 下的语音数据，除非任务就是更新模型。

## 运行与依赖

- Python >= 3.8。推荐 `.venv`，由 `./deploy.sh` 创建。
- pip：`sherpa-onnx`、`sounddevice`、`numpy`。
- 系统：`libportaudio2`（播放）、`wget`（Matcha 缺 vocoder 时下载）。
- 当前引擎 `provider="cpu"`、`num_threads=4`。不要默认改成 CUDA，除非用户要求并同步安装说明。

## 改代码时

- 保持 VITS / Matcha 两条引擎路径独立；一方失败不应阻止另一方加载。
- 模型路径一律 `os.path.join(MODEL_DIR, ...)`。Matcha vocoder 在 `tts-models/` 根下，不在子目录里。
- `synthesize()` 目前直接 `sd.play` + `sd.wait`，忽略 `output_file`。若加导出 wav，保留现有播放行为，或提供明确开关。
- 语速默认 `SPEED = 1.0`。Matcha 配置不要丢掉 `lexicon` 与 `data_dir`。
- 新增依赖必须写入 `requirements.txt`，并在 `README.md` 提一句。

## 不要做的事

- 不要把大模型（`.onnx`、lexicon、espeak 数据）重新生成或替换，除非用户明确要求。
- 不要引入在线 TTS API；本项目约束是离线合成。
- 不要在未确认的情况下把脚本改成 ROS2 节点；若要接入 ROS，新增节点文件，保留 CLI。
- 不要添加与 TTS 无关的重构、格式化全文件或新文档。

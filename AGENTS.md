# AGENTS.md

面向本仓库的 Agent 说明。改代码前先看 `ros_tts/`、`speaker.py` 和 `tts-models/` 的实际路径。

## 项目是什么

ROS 2 Humble 的离线 TTS 包（`ament_python`，包名 `ros_tts`）。节点持久运行，订阅 `std_msgs/String`，把文字排队合成并播放。CLI `speaker.py` 仍可单独试听。

默认节点名 `tts_speaker`，默认 topic `/tts/text`，两者都可配置，不要写死。

## 目录约定

- `ros_tts/tts_engine.py`：VITS / Matcha 引擎与模型路径解析。
- `ros_tts/speaker_node.py`：ROS 2 节点；播放在后台线程，不要在回调里 `sd.wait()`。
- `launch/tts.launch.py`、`config/speaker.yaml`：节点名、topic 等启动配置。
- `speaker.py`：命令行入口，复用 `tts_engine`，不要把引擎再复制一份。
- `tts-models/matcha-icefall-zh-en/`：Matcha 模型、`tokens.txt`、`lexicon.txt`、`espeak-ng-data/`。
- `tts-models/vocos-16khz-univ.onnx`：Matcha vocoder，在 `tts-models/` 根下。
- `tts-models/vits-piper-zh_CN-huayan-medium/`：可选；不存在则跳过。
- `requirements.txt` / `deploy.sh`：Python 依赖。新增依赖必须同步这两个文件。

不要提交或改动 `espeak-ng-data/` 下的语音数据，除非任务就是更新模型。

## 运行与依赖

- ROS 2 Humble + Python 3.10。`ros2 run` 用系统解释器，该解释器上要能 `import sherpa_onnx` 和 `rclpy`。
- pip：`sherpa-onnx`、`sounddevice`、`numpy`。
- 系统：`libportaudio2`；WSL 无 ALSA 设备时可走 `ffplay` + Pulse。
- 引擎 `provider="cpu"`、`num_threads=4`。不要默认改 CUDA。

## 改代码时

- 节点名用 launch 参数 `node_name`（以及 `-r __node:=`）。topic 用参数 `text_topic`，不要写死订阅名。
- 正在播放时新消息入队，不要打断、不要丢弃。
- VITS / Matcha 加载失败互不影响。ROS 节点 `engine:=auto` 时只选一个（优先 Matcha）。
- 模型路径用 `resolve_model_dir()` / 参数 `model_dir`，Matcha vocoder 在 `tts-models/` 根下。
- 语速默认 `1.0`。Matcha 配置保留 `lexicon` 与 `data_dir`。

## 不要做的事

- 不要替换大模型（`.onnx`、lexicon、espeak 数据），除非用户明确要求。
- 不要引入在线 TTS API。
- 不要删掉 CLI。
- 不要把大模型复制进 `install/`，除非用户要求。

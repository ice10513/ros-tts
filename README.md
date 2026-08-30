# ros-tts

离线中文（及中英混合）语音合成。基于 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)。

这是 ROS 2 Humble 包 `ros_tts`：节点启动后一直运行，别人往 topic 发文字即可排队播放。命令行脚本 `speaker.py` 仍可单独试听。

## 功能

- **Matcha**（默认）：`tts-models/matcha-icefall-zh-en` + `vocos-16khz-univ.onnx`
- **VITS**（可选）：存在 `tts-models/vits-piper-zh_CN-huayan-medium` 时可用
- CPU 推理；正在播放时新句子入队，说完再接下一句

## 环境要求

- ROS 2 Humble
- Python 3.10（Humble 默认）
- 可播放声音的设备（WSL 需 WSLg / PulseAudio；无 ALSA 时会尝试 `ffplay`）
- 系统库：`libportaudio2`、`wget`

## 安装 Python 依赖

```bash
chmod +x deploy.sh
./deploy.sh --mirror aliyun
```

`ros2 run` 走系统 Python，需要在该解释器上也能导入 TTS 库：

```bash
source /opt/ros/humble/setup.bash
python3 -m pip install --user -r requirements.txt
```

## 构建

在本仓库根目录（包就在这里，不必再套一层 `src/`）：

```bash
source /opt/ros/humble/setup.bash
colcon build --paths . --symlink-install
source install/setup.bash
```

## ROS 2 节点

默认节点名 **`tts_speaker`**，默认 topic **`/tts/text`**（`std_msgs/String`）。两者都可以改。

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ros_tts tts.launch.py
```

发文字：

```bash
ros2 topic pub --once /tts/text std_msgs/msg/String "{data: '你好，这是语音合成测试'}"
```

### 配置节点名和 topic

Launch 参数：

```bash
ros2 launch ros_tts tts.launch.py \
  node_name:=robot_tts \
  text_topic:=/robot/speak
```

`ros2 run`：

```bash
ros2 run ros_tts speaker_node --ros-args \
  -r __node:=robot_tts \
  -p text_topic:=/robot/speak \
  -p engine:=auto \
  -p speed:=1.0
```

其它参数：

| 参数 | 默认 | 说明 |
|------|------|------|
| `node_name` | `tts_speaker` | 节点名（launch 参数；run 时用 `-r __node:=`） |
| `text_topic` | `/tts/text` | 文字 topic |
| `engine` | `auto` | `auto` / `matcha` / `vits` |
| `model_dir` | 自动查找 | `tts-models` 路径 |
| `speed` | `1.0` | 语速 |

也可改 `config/speaker.yaml`（用 `/**:` 写参数，换节点名仍然生效），然后：

```bash
ros2 launch ros_tts tts.launch.py params_file:=/绝对路径/speaker.yaml
```

环境变量 `ROS_TTS_MODEL_DIR` 可覆盖模型目录。

## 命令行试听

```bash
source .venv/bin/activate
python speaker.py "你好，这是语音合成测试"
```

会加载所有已就位的引擎并各读一遍。

## 模型布局

```
tts-models/
  vocos-16khz-univ.onnx                 # Matcha vocoder（必需）
  matcha-icefall-zh-en/
    model-steps-3.onnx
    tokens.txt
    lexicon.txt
    espeak-ng-data/
  vits-piper-zh_CN-huayan-medium/       # 可选
    zh_CN-huayan-medium.onnx
    tokens.txt
    espeak-ng-data/
```

Matcha 声学模型来源：[ModelScope matcha_tts_zh_en](https://modelscope.cn/models/dengcunqin/matcha_tts_zh_en_20251010/summary)。

缺少 vocoder 时，首次加载 Matcha 会下载到 `tts-models/vocos-16khz-univ.onnx`。

## 项目结构

| 路径 | 说明 |
|------|------|
| `ros_tts/speaker_node.py` | ROS 2 节点 |
| `ros_tts/tts_engine.py` | TTS 引擎 |
| `launch/tts.launch.py` | 启动文件 |
| `config/speaker.yaml` | 默认参数 |
| `speaker.py` | 命令行入口 |
| `tts-models/` | 本地 ONNX 与词典 |
| `package.xml` / `setup.py` | ament_python 包 |

## 故障排除

- **未找到可用模型**：确认 `tts-models/matcha-icefall-zh-en` 存在；或设 `model_dir` / `ROS_TTS_MODEL_DIR`。
- **Matcha 配置验证失败**：vocoder 须在 `tts-models/vocos-16khz-univ.onnx`。
- **sounddevice / PortAudio Error querying device -1**：WSL 上 PortAudio 往往看不到 Pulse。节点会尝试 `ffplay`。要让 `sounddevice` 直接出声可安装 `libasound2-plugins`。
- **`ModuleNotFoundError: sherpa_onnx`**：`ros2 run` 没用到 `.venv`，需对系统 Python `pip install --user -r requirements.txt`。

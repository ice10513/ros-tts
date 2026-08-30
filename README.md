# ros-tts

离线中文（及中英混合）语音合成。基于 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)，本地加载 ONNX 模型后用系统音频设备播放。

当前是独立 Python 脚本，尚未封装为 ROS 节点。

## 功能

- **Matcha**（默认可用）：`tts-models/matcha-icefall-zh-en` + `vocos-16khz-univ.onnx`
- **VITS**（可选）：若存在 `tts-models/vits-piper-zh_CN-huayan-medium` 则一并加载
- CPU 推理；命令行传入文本，依次用已加载引擎朗读

## 环境要求

- Linux（含 WSL2）
- Python 3.8+
- 可播放声音的音频设备（WSL 需 WSLg / PulseAudio 正常工作）
- 系统库：`libportaudio2`（`sounddevice`）、`wget`（缺失 vocoder 时自动下载）

## 安装

在仓库根目录执行：

```bash
chmod +x deploy.sh
./deploy.sh
```

脚本会：

1. 安装系统包（`python3-venv`、`libportaudio2`、`libsndfile1`、`wget` 等，已安装则跳过）
2. 创建 `.venv`
3. 按 `requirements.txt` 安装 `sherpa-onnx`、`sounddevice`、`numpy`
4. 校验 `import`

常用参数：

```bash
./deploy.sh --mirror tsinghua    # 清华 PyPI 镜像（可选 aliyun / tencent）
./deploy.sh --no-venv            # 装到当前 Python，不建虚拟环境
./deploy.sh --skip-system        # 跳过 apt
./deploy.sh --python python3.11  # 指定解释器
```

手动安装等价于：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Debian/Ubuntu 若播放报错，可先安装：

```bash
sudo apt-get install -y libportaudio2 libsndfile1
```

## 使用

```bash
source .venv/bin/activate
python speaker.py "你好，这是语音合成测试"
```

无参数时打印用法。脚本会检测 `tts-models/` 下已有模型，加载成功的引擎会各朗读一遍。

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

若缺少 vocoder，首次加载 Matcha 时会从 GitHub 下载到 `tts-models/vocos-16khz-univ.onnx`。也可手动下载：

- https://github.com/k2-fsa/sherpa-onnx/releases/download/vocoder-models/vocos-16khz-univ.onnx
- https://modelscope.cn/models/dengcunqin/matcha_tts_zh_en_20251010/resolve/master/vocos-16khz-univ.onnx

VITS Piper 华严模型需自行放到上述目录，缺失时只跑 Matcha。

## 项目结构

| 路径 | 说明 |
|------|------|
| `speaker.py` | TTS 引擎与命令行入口 |
| `tts-models/` | 本地 ONNX 与词典 |
| `requirements.txt` | Python 依赖 |
| `deploy.sh` | 部署 / 安装依赖 |
| `AGENTS.md` | 给 Agent 的仓库约定 |

## 故障排除

- **未找到可用模型**：确认 `tts-models/matcha-icefall-zh-en` 存在且含 `model-steps-3.onnx`。
- **Matcha 配置验证失败**：检查 vocoder 是否在 `tts-models/vocos-16khz-univ.onnx`（不是子目录内）。
- **sounddevice / PortAudio 错误**：安装 `libportaudio2`；WSL 下确认 Windows 宿主能出声。
- **合成失败（空音频）**：换一句更短、含中文或中英混合的文本再试。

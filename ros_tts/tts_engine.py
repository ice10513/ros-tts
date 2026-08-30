"""离线 TTS 引擎（VITS / Matcha），供 CLI 与 ROS 节点共用。"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
import sherpa_onnx as sherpa
import sounddevice as sd

SPEED = 1.0

_PULSE_SOCKET = "/mnt/wslg/PulseServer"


def resolve_model_dir(explicit: str | None = None) -> str:
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_dir():
            return str(path.resolve())

    env = os.environ.get("ROS_TTS_MODEL_DIR")
    if env:
        path = Path(env).expanduser()
        if path.is_dir():
            return str(path.resolve())

    try:
        from ament_index_python.packages import get_package_share_directory

        share = Path(get_package_share_directory("ros_tts")) / "tts-models"
        if share.is_dir():
            return str(share)
    except Exception:
        pass

    cwd_models = Path.cwd() / "tts-models"
    if (cwd_models / "matcha-icefall-zh-en").is_dir() or (
        cwd_models / "vocos-16khz-univ.onnx"
    ).is_file():
        return str(cwd_models.resolve())

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "tts-models"
        if (candidate / "matcha-icefall-zh-en").is_dir() or (
            candidate / "vocos-16khz-univ.onnx"
        ).is_file():
            return str(candidate)

    raise FileNotFoundError(
        "找不到 tts-models，请设置参数 model_dir 或环境变量 ROS_TTS_MODEL_DIR"
    )


def play_audio(samples, sample_rate) -> bool:
    """优先 sounddevice；无输出设备时回退到 ffplay（WSLg Pulse）。"""
    try:
        devices = sd.query_devices()
        default_out = sd.default.device[1] if sd.default.device is not None else -1
        if default_out is not None and int(default_out) >= 0:
            sd.play(samples, sample_rate)
            sd.wait()
            return True
        if devices is not None:
            for device in devices:
                if device["max_output_channels"] > 0:
                    sd.play(samples, sample_rate)
                    sd.wait()
                    return True
    except Exception as exc:
        print(f"[TTS] sounddevice 播放失败: {exc}")

    ffplay = shutil.which("ffplay")
    if not ffplay:
        print("[TTS] 无可用音频设备，且未找到 ffplay")
        return False

    pcm = (np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0) * 32767.0).astype(
        np.int16
    )
    fd, wav_path = tempfile.mkstemp(prefix="ros_tts_", suffix=".wav")
    os.close(fd)
    try:
        with wave.open(wav_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(int(sample_rate))
            wav_file.writeframes(pcm.tobytes())
        env = os.environ.copy()
        if os.path.exists(_PULSE_SOCKET):
            env.setdefault("PULSE_SERVER", f"unix:{_PULSE_SOCKET}")
        subprocess.run(
            [ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet", wav_path],
            env=env,
            check=False,
        )
        return True
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass


class TTSEngine:
    def __init__(self, name, model_root):
        self.name = name
        self.model_root = model_root
        self.tts = None

    def synthesize(self, text, speed=SPEED, output_file=None):
        raise NotImplementedError


class VitsEngine(TTSEngine):
    def __init__(self, model_root, model_dir="vits-piper-zh_CN-huayan-medium"):
        super().__init__("VITS", model_root)
        model_path = os.path.join(model_root, model_dir, "zh_CN-huayan-medium.onnx")
        tokens_path = os.path.join(model_root, model_dir, "tokens.txt")
        data_dir = os.path.join(model_root, model_dir, "espeak-ng-data")

        config = sherpa.OfflineTtsConfig(
            model=sherpa.OfflineTtsModelConfig(
                vits=sherpa.OfflineTtsVitsModelConfig(
                    model=model_path,
                    data_dir=data_dir,
                    tokens=tokens_path,
                ),
                num_threads=4,
                provider="cpu",
            ),
            max_num_sentences=2,
        )

        if not config.validate():
            raise ValueError("VITS 配置验证失败")

        self.tts = sherpa.OfflineTts(config)
        print(f"[VITS] 模型已加载: {model_dir}")

    def synthesize(self, text, speed=SPEED, output_file=None):
        gen_config = sherpa.GenerationConfig()
        gen_config.speed = speed
        gen_config.silence_scale = 0.2

        audio = self.tts.generate(text, gen_config)
        if len(audio.samples) == 0:
            print("[VITS] 合成失败")
            return None

        play_audio(audio.samples, audio.sample_rate)
        print(f"[VITS] 播放完成 ({len(audio.samples)/audio.sample_rate:.2f}s)")
        return True


class MatchaEngine(TTSEngine):
    def __init__(self, model_root, model_dir="matcha-icefall-zh-en"):
        super().__init__("Matcha", model_root)

        model_path = os.path.join(model_root, model_dir, "model-steps-3.onnx")
        vocoder_path = os.path.join(model_root, "vocos-16khz-univ.onnx")
        tokens_path = os.path.join(model_root, model_dir, "tokens.txt")
        lexicon_path = os.path.join(model_root, model_dir, "lexicon.txt")
        data_dir = os.path.join(model_root, model_dir, "espeak-ng-data")

        if not os.path.exists(vocoder_path):
            print("[Matcha] 缺少 vocoder，正在下载...")
            url = (
                "https://github.com/k2-fsa/sherpa-onnx/releases/download/"
                "vocoder-models/vocos-16khz-univ.onnx"
            )
            subprocess.check_call(["wget", "-O", vocoder_path, url])
            print("[Matcha] vocoder 下载完成")

        config = sherpa.OfflineTtsConfig(
            model=sherpa.OfflineTtsModelConfig(
                matcha=sherpa.OfflineTtsMatchaModelConfig(
                    acoustic_model=model_path,
                    vocoder=vocoder_path,
                    tokens=tokens_path,
                    lexicon=lexicon_path,
                    data_dir=data_dir,
                ),
                num_threads=4,
                provider="cpu",
            ),
            max_num_sentences=2,
        )

        if not config.validate():
            raise ValueError("Matcha 配置验证失败")

        self.tts = sherpa.OfflineTts(config)
        print(f"[Matcha] 模型已加载: {model_dir}")

    def synthesize(self, text, speed=SPEED, output_file=None):
        gen_config = sherpa.GenerationConfig()
        gen_config.speed = speed

        audio = self.tts.generate(text, gen_config)
        if len(audio.samples) == 0:
            print("[Matcha] 合成失败")
            return None

        play_audio(audio.samples, audio.sample_rate)
        print(f"[Matcha] 播放完成 ({len(audio.samples)/audio.sample_rate:.2f}s)")
        return True


def load_engine(engine="auto", model_dir=None):
    """加载一个引擎，供 ROS 节点使用。auto 优先 Matcha。"""
    model_root = resolve_model_dir(model_dir)
    kind = (engine or "auto").strip().lower()
    matcha_dir = os.path.join(model_root, "matcha-icefall-zh-en")
    vits_dir = os.path.join(model_root, "vits-piper-zh_CN-huayan-medium")

    def try_matcha():
        if not os.path.isdir(matcha_dir):
            raise FileNotFoundError(f"Matcha 模型目录不存在: {matcha_dir}")
        return MatchaEngine(model_root, "matcha-icefall-zh-en")

    def try_vits():
        if not os.path.isdir(vits_dir):
            raise FileNotFoundError(f"VITS 模型目录不存在: {vits_dir}")
        return VitsEngine(model_root, "vits-piper-zh_CN-huayan-medium")

    if kind == "matcha":
        return try_matcha()
    if kind == "vits":
        return try_vits()

    errors = []
    if os.path.isdir(matcha_dir):
        try:
            return try_matcha()
        except Exception as exc:
            errors.append(f"Matcha: {exc}")
    if os.path.isdir(vits_dir):
        try:
            return try_vits()
        except Exception as exc:
            errors.append(f"VITS: {exc}")
    detail = "; ".join(errors) if errors else f"目录为空: {model_root}"
    raise RuntimeError(f"未找到可用模型，{detail}")


def load_available_engines(model_dir=None):
    """加载所有可用引擎，供 CLI 试听。"""
    model_root = resolve_model_dir(model_dir)
    engines = []

    vits_dir = os.path.join(model_root, "vits-piper-zh_CN-huayan-medium")
    if os.path.isdir(vits_dir):
        try:
            engines.append(VitsEngine(model_root, "vits-piper-zh_CN-huayan-medium"))
        except Exception as exc:
            print(f"[VITS] 加载失败: {exc}")

    matcha_dir = os.path.join(model_root, "matcha-icefall-zh-en")
    if os.path.isdir(matcha_dir):
        try:
            engines.append(MatchaEngine(model_root, "matcha-icefall-zh-en"))
        except Exception as exc:
            print(f"[Matcha] 加载失败: {exc}")

    return engines

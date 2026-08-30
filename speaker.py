#!/usr/bin/env python3
"""
离线中文语音合成 (TTS) - 支持 VITS 和 Matcha 模型
"""

import os
import sys
import subprocess

import sherpa_onnx as sherpa
import sounddevice as sd


MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts-models")

SPEED = 1.0


class TTSEngine:
    """TTS 引擎基类"""
    def __init__(self, name):
        self.name = name
        self.tts = None

    def synthesize(self, text, speed=SPEED, output_file=None):
        raise NotImplementedError


class VitsEngine(TTSEngine):
    """VITS 模型引擎"""
    def __init__(self, model_dir="vits-piper-zh_CN-huayan-medium"):
        super().__init__("VITS")
        model_path = os.path.join(MODEL_DIR, model_dir, "zh_CN-huayan-medium.onnx")
        tokens_path = os.path.join(MODEL_DIR, model_dir, "tokens.txt")
        data_dir = os.path.join(MODEL_DIR, model_dir, "espeak-ng-data")

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

        sd.play(audio.samples, audio.sample_rate)
        sd.wait()
        print(f"[VITS] 播放完成 ({len(audio.samples)/audio.sample_rate:.2f}s)")
        return True


class MatchaEngine(TTSEngine):
    """Matcha 模型引擎"""
    def __init__(self, model_dir="matcha-icefall-zh-en"):
        super().__init__("Matcha")
        
        model_path = os.path.join(MODEL_DIR, model_dir, "model-steps-3.onnx")
        vocoder_path = os.path.join(MODEL_DIR, "vocos-16khz-univ.onnx")
        tokens_path = os.path.join(MODEL_DIR, model_dir, "tokens.txt")
        lexicon_path = os.path.join(MODEL_DIR, model_dir, "lexicon.txt")
        data_dir = os.path.join(MODEL_DIR, model_dir, "espeak-ng-data")
        
        if not os.path.exists(vocoder_path):
            print("[Matcha] 缺少 vocoder，正在下载...")
            url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/vocoder-models/vocos-16khz-univ.onnx"
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

        sd.play(audio.samples, audio.sample_rate)
        sd.wait()
        print(f"[Matcha] 播放完成 ({len(audio.samples)/audio.sample_rate:.2f}s)")
        return True


def main():
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        print("用法: speaker.py \"要朗读的文字\"")
        return

    engines = []

    vits_dir = os.path.join(MODEL_DIR, "vits-piper-zh_CN-huayan-medium")
    if os.path.exists(vits_dir):
        try:
            engines.append(VitsEngine("vits-piper-zh_CN-huayan-medium"))
        except Exception as e:
            print(f"[VITS] 加载失败: {e}")

    matcha_dir = os.path.join(MODEL_DIR, "matcha-icefall-zh-en")
    if os.path.exists(matcha_dir):
        try:
            engines.append(MatchaEngine("matcha-icefall-zh-en"))
        except Exception as e:
            print(f"[Matcha] 加载失败: {e}")

    if not engines:
        print("未找到可用模型，请下载模型到 tts-models 目录")
        return

    print(f"\n已加载 {len(engines)} 个引擎\n")
    print(f"朗读文字: {text}\n")

    for engine in engines:
        engine.synthesize(text)

    print("\n全部完成！")


if __name__ == "__main__":
    main()

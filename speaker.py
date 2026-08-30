#!/usr/bin/env python3
"""
离线中文语音合成 (TTS) - 支持 VITS 和 Matcha 模型
"""

import sys

from ros_tts.tts_engine import load_available_engines


def main():
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        print('用法: speaker.py "要朗读的文字"')
        return

    engines = load_available_engines()
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

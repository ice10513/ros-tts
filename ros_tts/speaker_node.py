"""持久运行的 TTS 节点：订阅文字 topic，排队播放。"""

from __future__ import annotations

import queue
import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from ros_tts.tts_engine import load_engine, resolve_model_dir


class SpeakerNode(Node):
    def __init__(self):
        super().__init__("tts_speaker")

        self.declare_parameter("text_topic", "/tts/text")
        self.declare_parameter("model_dir", "")
        self.declare_parameter("engine", "auto")
        self.declare_parameter("speed", 1.0)

        text_topic = (
            self.get_parameter("text_topic").get_parameter_value().string_value.strip()
            or "/tts/text"
        )
        model_dir_param = (
            self.get_parameter("model_dir").get_parameter_value().string_value.strip()
        )
        engine_name = (
            self.get_parameter("engine").get_parameter_value().string_value.strip()
            or "auto"
        )
        self._speed = self.get_parameter("speed").get_parameter_value().double_value

        model_dir = resolve_model_dir(model_dir_param or None)
        self.get_logger().info(
            f"node={self.get_fully_qualified_name()} topic={text_topic} "
            f"engine={engine_name} model_dir={model_dir}"
        )

        self._engine = load_engine(engine_name, model_dir)
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._run_worker, daemon=True)
        self._worker.start()

        self.create_subscription(String, text_topic, self._on_text, 10)
        self.get_logger().info(f"已订阅 {text_topic}，排队播放")

    def _on_text(self, msg: String) -> None:
        text = (msg.data or "").strip()
        if not text:
            return
        self._queue.put(text)
        self.get_logger().info(f"入队 (size={self._queue.qsize()}) {text}")

    def _run_worker(self) -> None:
        while not self._stop.is_set():
            try:
                text = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if text is None:
                break
            try:
                self.get_logger().info(f"开始播放: {text}")
                self._engine.synthesize(text, speed=self._speed)
            except Exception as exc:
                self.get_logger().error(f"播放失败: {exc}")
            finally:
                self._queue.task_done()

    def destroy_node(self):
        self._stop.set()
        self._queue.put(None)
        if self._worker.is_alive():
            self._worker.join(timeout=5.0)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = SpeakerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

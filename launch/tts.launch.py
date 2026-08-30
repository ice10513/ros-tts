import os
import sys
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def find_model_dir() -> str:
    env = os.environ.get("ROS_TTS_MODEL_DIR")
    if env and os.path.isdir(env):
        return env
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "tts-models"
        if (candidate / "matcha-icefall-zh-en").is_dir():
            return str(candidate)
    return ""


def find_venv_site_packages() -> str:
    pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    for parent in Path(__file__).resolve().parents:
        site = parent / ".venv" / "lib" / pyver / "site-packages"
        if not site.is_dir():
            continue
        if (site / "sherpa_onnx").exists() or list(site.glob("sherpa_onnx*.dist-info")):
            return str(site)
    return ""


def generate_launch_description():
    pkg_share = FindPackageShare("ros_tts")
    default_params = PathJoinSubstitution([pkg_share, "config", "speaker.yaml"])
    venv_site = find_venv_site_packages()
    pythonpath = os.environ.get("PYTHONPATH", "")
    if venv_site:
        pythonpath = (
            venv_site + os.pathsep + pythonpath if pythonpath else venv_site
        )

    actions = [
        DeclareLaunchArgument(
            "node_name",
            default_value="tts_speaker",
            description="ROS 2 节点名，可按机器人覆盖",
        ),
        DeclareLaunchArgument(
            "text_topic",
            default_value="/tts/text",
            description="接收待朗读文字的 std_msgs/String topic",
        ),
        DeclareLaunchArgument(
            "engine",
            default_value="auto",
            description="TTS 引擎: auto | matcha | vits",
        ),
        DeclareLaunchArgument(
            "model_dir",
            default_value=find_model_dir(),
            description="tts-models 目录，空则自动查找",
        ),
        DeclareLaunchArgument(
            "speed",
            default_value="1.0",
            description="语速",
        ),
        DeclareLaunchArgument(
            "params_file",
            default_value=default_params,
            description="额外参数 YAML",
        ),
        Node(
            package="ros_tts",
            executable="speaker_node",
            name=LaunchConfiguration("node_name"),
            output="screen",
            emulate_tty=True,
            parameters=[
                LaunchConfiguration("params_file"),
                {
                    "text_topic": LaunchConfiguration("text_topic"),
                    "engine": LaunchConfiguration("engine"),
                    "model_dir": LaunchConfiguration("model_dir"),
                    "speed": ParameterValue(
                        LaunchConfiguration("speed"), value_type=float
                    ),
                },
            ],
        ),
    ]
    if pythonpath:
        actions.insert(0, SetEnvironmentVariable("PYTHONPATH", pythonpath))
    return LaunchDescription(actions)

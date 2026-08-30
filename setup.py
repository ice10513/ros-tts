from glob import glob

from setuptools import find_packages, setup

package_name = "ros_tts"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ice",
    maintainer_email="ice@example.com",
    description="Offline TTS ROS 2 node",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "speaker_node = ros_tts.speaker_node:main",
        ],
    },
)

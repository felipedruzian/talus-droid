from glob import glob
from setuptools import find_packages, setup

package_name = "talus_base"
package_glob = "talus_base.*"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(include=[package_name, package_glob]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Felip",
    maintainer_email="felip@todo.todo",
    description="Serial bridge and runtime support for the Talus mobile base.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "talus_base_bridge = talus_base.serial_bridge:main",
            "talus_kinect_validate = talus_base.kinect_validation.runner:main",
            "talus_kinect_sample_image = talus_base.kinect_validation.sampler:main",
        ],
    },
)

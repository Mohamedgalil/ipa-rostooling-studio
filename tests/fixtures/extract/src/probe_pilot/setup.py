from setuptools import setup

package_name = "probe_pilot"

setup(
    name=package_name,
    version="0.0.0",
    packages=[package_name],
    entry_points={
        "console_scripts": [
            "probe_pilot_node = probe_pilot.pilot:main",
        ],
    },
)

from setuptools import setup, find_packages

setup(
    name="brightpanel",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "brightpanel = brightpanel.cli.main:main",
            "brightpanel-gui = brightpanel.gui.app:run_app",
        ],
    },
)

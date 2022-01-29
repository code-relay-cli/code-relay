from setuptools import setup

setup(
    name="coderelay",
    version="0.1.0",
    py_modules=["coderelay"],
    install_requires=["Click", "ujson", "requests", "platformdirs", "progress"],
    entry_points={
        "console_scripts": [
            "coderelay = coderelay:cli",
        ],
    },
)

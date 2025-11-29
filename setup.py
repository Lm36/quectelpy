#!/usr/bin/env python3
"""
Setup script for quectelpy.
"""

from setuptools import setup, find_packages

setup(
    name="quectelpy",
    version="0.1.0",
    description="Python library for controlling Quectel cellular modems via AT commands",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Luke",
    url="https://github.com/lm36/quectelpy",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "pyserial>=3.5",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-timeout>=2.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "quectel-cli=quectelpy.cli:main",
        ],
    },
    keywords=["quectel", "modem", "cellular", "at-commands", "iot", "4g", "lte"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Communications",
        "Topic :: System :: Hardware :: Hardware Drivers",
        "Operating System :: POSIX :: Linux",
        "License :: OSI Approved :: MIT License",
    ],
)
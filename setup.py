"""Build file for Pro Check Sensor pypi library

Copyright (c) 2021 Sean Brogan

SPDX-License-Identifier: MIT

"""
import setuptools

with open("readme.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mopeka-pro-check",
    version="0.0.4",
    author="Sean Brogan",
    author_email="spbrogan@live.com",
    description="A library for reading Mopeka Pro Check BLE sensors",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/spbrogan/mopeka_pro_check",
    license='MIT',
    packages=setuptools.find_packages(),
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    install_requires=[
        'bleson>=0.1.6'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
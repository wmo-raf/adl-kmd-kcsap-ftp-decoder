#!/usr/bin/env python
import os

from setuptools import find_packages, setup

PROJECT_DIR = os.path.dirname(__file__)
REQUIREMENTS_DIR = os.path.join(PROJECT_DIR, "requirements")
VERSION = "0.1.1"


def get_requirements(env):
    with open(os.path.join(REQUIREMENTS_DIR, f"{env}.txt")) as fp:
        return [
            x.strip()
            for x in fp.read().split("\n")
            if not x.strip().startswith("#") and not x.strip().startswith("-")
        ]


install_requires = get_requirements("base")

setup(
    name="adl-kmd-kcsap-ftp-decoder",
    version=VERSION,
    url="https://github.com/wmo-raf/adl-kmd-kcsap-ftp-decoder",
    author="WMO RAF",
    author_email="erick.otenyo@wmo.int",
    license="MIT",
    description="ADL FTP decoder for Kenya Meteorological Department (KMD) KCSAP AWS minute files",
    long_description="ADL FTP decoder for Kenya Meteorological Department (KMD) KCSAP AWS minute files",
    platforms=["linux"],
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    install_requires=install_requires
)

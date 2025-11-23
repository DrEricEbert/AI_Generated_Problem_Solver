"""
Setup-Script für Messsequenz-System
"""

from setuptools import setup, find_packages
import os

# Lese README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Lese Requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="measurement-sequence-system",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Professionelles Messsequenz-Verwaltungssystem mit Plugin-Architektur",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/measurement-sequence-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'measurement-system=main:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': ['*.json', '*.ini', '*.txt'],
    },
)

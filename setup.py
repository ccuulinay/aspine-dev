import pathlib
from setuptools import setup

# The directory containing this file
ROOT = pathlib.Path(__file__).parent

# The text of the README file
README_TEXT = (ROOT / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="aspine",
    version="0.0.1",
    description="Read the latest Real Python tutorials",
    long_description=README_TEXT,
    long_description_content_type="text/markdown",
    url="https://github.com/ccuulinay/***",
    author="ccuulinay",
    author_email="ccuulinay@gmail.com",
    license="MIT",
    classifiers=[
        'Intended Audience :: Developers',
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["aspine"],
    include_package_data=True,
    # install_requires=[],
)

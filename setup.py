"""
Setup script for Aspine 2.0
"""
from setuptools import setup, find_packages
from pathlib import Path

# The directory containing this file
ROOT = Path(__file__).parent

# The text of the README file
README = (ROOT / "README.md").read_text(encoding="utf-8")

# The long description
long_description = """
Aspine 2.0 - Python-native async + multiprocessing hybrid caching system

Aspine provides a high-performance in-memory cache with:
- Asyncio for client-side concurrency
- Multiprocessing for server-side data isolation
- Queue-based communication between layers
- LRU eviction and TTL support
- Optional disk persistence
- Pub/sub for cache invalidation
"""

setup(
    name="aspine",
    version="2.0.0",
    description="Python-native async + multiprocessing hybrid caching system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ccuulinay/aspine-dev",
    project_urls={
        "Documentation": "https://aspine.readthedocs.io/",
        "Source": "https://github.com/ccuulinay/aspine-dev",
        "Tracker": "https://github.com/ccuulinay/aspine-dev/issues",
    },
    author="ccuulinay",
    author_email="ccuulinay@gmail.com",
    license="MIT",
    python_requires=">=3.11",
    packages=find_packages(exclude=["tests*", "docs*", "poc*"]),
    include_package_data=True,
    install_requires=[
        "typer>=0.9.0",
        "rich>=13.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "coverage[toml]>=7.0.0",
        ],
        "docs": [
            "jupyter>=1.0.0",
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
        ],
        "perf": [
            "pytest-benchmark>=4.0.0",
            "memory-profiler>=0.60.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "aspine=aspine.cli:app",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Internet :: Name Service (DNS)",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
        "Topic :: System :: Networking",
        "Topic :: Utilities",
    ],
    keywords="cache, caching, async, asyncio, multiprocessing, storage, memory, redis-like",
    platforms=["any"],
    zip_safe=False,
)

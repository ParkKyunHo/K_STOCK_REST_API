"""
키움증권 REST API 백테스팅 시스템 패키지 설정
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="kiwoom-backtest",
    version="0.1.0",
    author="Park Kyun Ho",
    author_email="your.email@example.com",
    description="키움증권 REST API를 활용한 주식 거래 전략 백테스팅 시스템",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ParkKyunHo/K_STOCK_REST_API",
    packages=find_packages(include=["src", "src.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "mypy>=1.7.1",
            "black>=23.12.0",
            "isort>=5.13.2",
            "flake8>=6.1.0",
            "pylint>=3.0.3",
        ],
        "docs": [
            "sphinx>=7.2.6",
            "sphinx-rtd-theme>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "kiwoom-backtest=src.presentation.cli.main:main",
            "kiwoom-ui=src.presentation.ui.main:main",
        ],
    },
    package_data={
        "src": ["config/*.yaml", "config/*.json"],
    },
    include_package_data=True,
    zip_safe=False,
)
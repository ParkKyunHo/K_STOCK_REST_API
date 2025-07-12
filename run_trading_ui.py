#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Trading UI 실행 스크립트
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.presentation.ui.application import main

if __name__ == "__main__":
    main()
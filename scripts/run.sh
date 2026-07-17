#!/bin/bash
# 一键运行: ./run.sh [yaml文件] [输出docx]
cd "$(dirname "$0")"
exec ./venv/bin/python generate_notice.py "$@"

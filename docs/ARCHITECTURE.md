# 架构说明

## 设计原则

1. **AI 与模板分离**:AI 只负责"内容生成",docx 排版由 python-docx 模板负责
2. **YAML 作为中转**:人和 AI 都能编辑,git 友好,版本可追溯
3. **CLI 友好**:每一步都能独立跑,排查问题方便

## 模块

### ai_suggest.py
- 输入:隐患描述(纯文本,stdin 或 argv)
- 输出:JSON → 写到 notice.yaml + 打印可拷贝文本
- 用 DeepSeek API(model = deepseek-chat)
- 提示词硬编码(详见 PROMPT)

### generate_notice.py
- 输入:notice.yaml
- 输出:.docx
- python-docx 实现:
  - A4 页边距 2.5cm
  - 字体:标题黑体,正文宋体
  - 段落首行缩进

### PowerShell `ai-suggest` 函数
- 配置在 `Documents\WindowsPowerShell\profile.ps1`
- 内部走 `wsl bash -c ...` + Python 脚本
- UTF-8 BOM 解决 PowerShell 5.1 中文路径 mojibake 问题

## 编码注意

WSL ↔ Windows PowerShell 中文路径编码:
- PowerShell profile 加 UTF-8 BOM
- 顶部强制 `$OutputEncoding = UTF8`
- WSLENV 让 WSL 看到 Windows 环境变量

# 智安通 · Safety Notice AI

> **施工现场安全隐患整改通知书 · 智能生成器**
> 一句话隐患 → AI 自动出:合规条款 + 整改要求 + 完整通知文本 + Word 文档

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![For Construction Safety](https://img.shields.io/badge/Domain-Construction%20Safety-orange.svg)]()

---

## 为什么做这个

我是工地上的一名安全员。在工地,**每周要起草 5–10 份《安全隐患整改通知书》**。

每份通知都有固定结构(抬头 / 法规依据 / 整改要求 / 闭环段),但每次:

- 翻开 6-7 本规范书查条款号 —— 10 分钟
  - 想"合规又有抓手"的整改要求(动词开头,SMART) —— 15 分钟
- 一句句敲到 Word 模板 —— 10 分钟

**一份 = 30+ 分钟,一周 5 份 = 2.5 小时,全是低创造性劳动**。

---

## 它能干什么

```powershell
PS> ai-suggest 电线泡水未及时处理
```

→ **30 秒后**,你拿到:

```
安全隐患整改通知书
致:XX项目部:
　　2026年7月17日,安监部于日常巡检中,发现你单位施工现场临时用电区域
违反《施工现场临时用电安全技术规范》(JGJ 46-2005)第7.1.6条,施工现场
临时用电线路及配电箱浸泡于积水中,存在漏电、短路及触电事故风险,未及时整改。

现对你单位要求如下:
1. 立即切断泡水区域电源,将浸泡电线及配电箱移至干燥安全处……
2. 全面排查施工现场所有临时用电线路、配电箱及用电设备周边积水情况……
3. 严格执行《施工现场临时用电安全技术规范》(JGJ 46-2005)第7.1.6条……

本通知下发之日起 3 日内完成全部整改,并将整改结果书面报安监部……
发文单位:安监部(盖章)
```

支持的隐患类型样例:

- 临时用电(电线泡水 / 配电箱无门 / PE 保护缺失)
- 高处作业(未系安全带 / 临边无防护)
- 深基坑(支护变形 / 边坡堆载)
- 脚手架(连墙件被拆 / 立杆悬空)
- 个人防护(不戴安全帽 / 安全带低挂高用)
- …… 等 20+ 种

---

## 工作流程

```
┌─────────────────┐
│ 隐患描述 (一句)  │
│  "电线泡水"      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ DeepSeek API                │
│   - 识别适用规范             │
│   - 引到具体条款             │
│   - 生成 SMART 整改要求      │
└────────┬────────────────────┘
         │  JSON
         ▼
┌─────────────────┐
│  notice.yaml    │
│   (可手动改)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ python-docx     │
│   生成 .docx    │
└─────────────────┘
         │
         ▼
   整改通知.docx
   (双击在 Word 打开)
```

---

## 快速开始

### 环境要求

- Windows 10/11 + **WSL2**(Ubuntu 20.04+)
- 或 macOS / Linux
- Python 3.10+
- DeepSeek API Key([免费获取](https://platform.deepseek.com/api_keys))

### 安装

```bash
git clone https://github.com/yjl666-ai/safety-notice.git
cd safety-notice
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 配置 API Key

**macOS / Linux:**

```bash
export DEEPSEEK_API_KEY="sk-你的key"
```

**Windows / WSL(推荐):** 直接跑配置向导

```powershell
. .\scripts\set-deepseek-key.ps1
```

按提示粘贴新 key,向导自动写到 Windows 环境变量 + WSL 文件(权限 600)。

### 使用

#### 模式 A:AI 智能出内容(推荐)

```bash
# 把"隐患描述"换成你的话
echo "高处作业未系安全带" | ./venv/bin/python ai_suggest.py
```

#### 模式 B:手动填字段

```bash
cp notice.yaml.example notice.yaml
# 编辑 notice.yaml
./scripts/run.sh notice.yaml 整改通知.docx
```

输出 `整改通知.docx` 在 Word 中可直接打开、编辑、盖章。

---

## 项目结构

```
safety-notice/
├── ai_suggest.py            # DeepSeek API 调用,JSON → YAML
├── generate_notice.py       # YAML → .docx (python-docx)
├── notice.yaml.example      # 输入模板
├── requirements.txt         # python-docx, pyyaml
├── scripts/
│   ├── run.sh               # 一键跑(YAML → docx)
│   └── set-deepseek-key.ps1 # Windows 配置 key 向导
└── docs/
    └── 架构.md               # 详细说明
```

---

## 局限 & Roadmap

### 当前局限

- ⚠️ LLM 引用的条款号**仍需人工核对一次**(有极小概率引错)
- 抬头单位名称、照片图号(`见图1、2、3`)等占位信息需要手动补
- 暂未对接照片 OCR 自动化图号

### Roadmap

- [X]  YAML → .docx 文档生成
- [X]  DeepSeek API 智能内容生成
- [X]  Windows PowerShell 一行集成(`ai-suggest`)
- [ ]  整改闭环回执(扫码 / 签字后上传存证)
- [ ]  多项目并行管理(YAML 多版本)
- [ ]  历史隐患库检索 / 复用
- [ ]  微信小程序版(给工人端扫码整改)

---

## 关于作者

**yjl** · 安全员 → AI × 智慧工地

项目安全员,自学 Python + LLM。正在从现场安全岗转向 **AI × 建工科技**。

- GitHub: [@yjl666-ai](https://github.com/yjl666-ai)
- 邮箱:yuanjiale2026@163.com

---

## License

MIT — 自由使用、修改、商用。详见 [LICENSE](LICENSE)。

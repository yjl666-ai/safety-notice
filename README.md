# 智安通 · Safety Notice AI

> **施工现场安全隐患整改通知书 · 智能生成器**
> N 条隐患(文本 / 照片) → AI 自动出:合规条款 + 整改要求 + 完整通知 + Word 文档

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![For Construction Safety](https://img.shields.io/badge/Domain-Construction%20Safety-orange.svg)]()

> **当前版本:v0.4** — 新增**照片 → 整改通知单**融合模式(Qwen-VL-Max 看图识别 → DeepSeek 写通知)

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

### 模式 A:文本隐患(老用法,完全兼容)

```powershell
PS> ai-suggest 电线泡水未及时处理
```

→ **30 秒后**,你拿到完整的整改通知 + 引用规范 + 针对性整改要求 + 可直接打开的 Word。

### 模式 B:多条隐患一次出(v0.3 新增)

```powershell
PS> ai-suggest @"
电线泡水未及时处理
高处作业未系安全带
基坑边坡堆土超载
灭火器失效
"@
```

→ **4 条隐患融合成 1 段描述 + 4 条针对性整改**(一对一,不写通用整改句)。

### 模式 C:照片 → 通知单融合(v0.4 新增)⭐

```powershell
PS> ai-suggest --photos .\工地照片\
```

→ **1-多张现场照片** → Qwen-VL-Max 视觉识别每张图的隐患 → 自动喂给 DeepSeek → 出完整通知 + docx。

工作流:**拍照 → 丢进文件夹 → 一条命令 → docx 可发**。

---

## 工作流程

```
                  ┌─────────────────────┐
                  │ 隐患来源(任选一种)    │
                  └─────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   文本隐患           stdin / -i           --photos 照片
  (命令行参数)        (交互式)             (Qwen-VL-Max)
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                  ┌─────────────────────┐
                  │   DeepSeek API      │
                  │   文字生成:N 条隐患  │
                  │   → 1 段描述 + N 条  │
                  │     针对性整改        │
                  └──────────┬──────────┘
                             │ JSON
                             ▼
                       notice.yaml
                             │
                             ▼
                    ┌─────────────────┐
                    │  python-docx     │
                    │  → .docx          │
                    └────────┬─────────┘
                             ▼
                       整改通知.docx
                       (2x2 照片占位 +
                        一段描述 +
                        N 条整改要求)
```

---

## 快速开始

### 环境要求

- Windows 10/11 + **WSL2**(Ubuntu 20.04+) / 或 macOS / Linux
- Python 3.10+
- **DeepSeek API Key**(文字生成,必需) — [免费获取](https://platform.deepseek.com/api_keys)
- **阿里云百炼 API Key**(照片识别,v0.4 可选) — [免费获取](https://dashscope.console.aliyun.com/apiKey)

### 安装

```bash
git clone https://github.com/yjl666-ai/safety-notice.git
cd safety-notice
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 配置 API Key

**DeepSeek(必需):**

```powershell
. .\scripts\set-deepseek-key.ps1
```

**阿里云百炼(可选,只用于 --photos 模式):**

```powershell
. .\scripts\set-dashscope-key.ps1
```

按提示粘贴新 key,向导自动写到 Windows 环境变量 + WSL 文件(权限 600)。

> ⚠️ **安全提醒**:如果你的 key 曾在 chat / Git commit / 桌面脚本里出现过,**必须先去对应平台 rotate** 再配进来。

### 使用

#### A. 文本隐患

```bash
# 单条
./venv/bin/python ai_suggest.py "电线泡水未及时处理"

# 多条(空格分隔)
./venv/bin/python ai_suggest.py "电线泡水" "高处未系安全带" "基坑堆土超载"

# 多行 stdin
echo -e "电线泡水\n高处未系安全带" | ./venv/bin/python ai_suggest.py

# 交互式
./venv/bin/python ai_suggest.py -i
```

#### B. 照片融合(v0.4 新)

```bash
# 单张图
./venv/bin/python ai_suggest.py --photos photo1.jpg

# 多张图(空格分隔)
./venv/bin/python ai_suggest.py --photos photo1.jpg photo2.jpg photo3.jpg

# 整个文件夹(按文件名排序)
./venv/bin/python ai_suggest.py --photos ./工地照片/

# 自定义 API 端点(走代理时)
./venv/bin/python ai_suggest.py --photos photo.jpg \
    --base-url https://your-proxy.com/v1 \
    --model qwen-vl-max
```

#### C. 手动填字段(无 AI)

```bash
cp notice.yaml.example notice.yaml
# 用编辑器改 notice.yaml
./scripts/run.sh notice.yaml 整改通知.docx
```

#### D. 出 docx

```bash
./venv/bin/python generate_notice.py notice.yaml 整改通知.docx
```

输出 `整改通知.docx` 在 Word 中可直接打开、编辑、盖章。

---

## 项目结构

```
safety-notice/
├── ai_suggest.py              # 主入口:DeepSeek(文字)+ Qwen-VL(照片)
├── generate_notice.py         # YAML → .docx(python-docx)
├── app.py                     # Flask Web UI(多行 textarea)
├── notice.yaml.example        # 输入模板
├── requirements.txt           # python-docx, pyyaml, flask
├── scripts/
│   ├── run.sh                 # 一键跑(YAML → docx)
│   ├── set-deepseek-key.ps1   # DeepSeek key 配置向导
│   ├── set-dashscope-key.ps1  # 阿里云百炼 key 配置向导
│   └── launch-ui.bat          # Windows 一键启动 Web UI
└── docs/
    └── 架构.md                 # 详细说明
```

---

## 局限 & Roadmap

### 当前局限

- ⚠️ LLM 引用的条款号**仍需人工核对一次**(有极小概率引错)
- 抬头单位名称、照片图号(`见图1、2、3`)等占位信息需要手动补
- v0.4 照片融合模式**不在 docx 里嵌入照片**(用户自己贴图,避免 AI 误匹配)
- Qwen-VL-Max 看图**仍可能漏报**部分隐患,人工复核必要

### Roadmap

- [x] YAML → .docx 文档生成
- [x] DeepSeek API 智能内容生成
- [x] Windows PowerShell 一行集成(`ai-suggest`)
- [x] **多隐患支持**(v0.3) — N 条隐患 → 1 段描述 + N 条针对性整改
- [x] **照片 → 通知单融合**(v0.4) — Qwen-VL-Max + DeepSeek 端到端
- [ ] 整改闭环回执(扫码 / 签字后上传存证)
- [ ] 多项目并行管理(YAML 多版本)
- [ ] 历史隐患库检索 / 复用
- [ ] 微信小程序版(给工人端扫码整改)

---

## 关于作者

**袁嘉乐(yjl)** · 安全员 → AI × 智慧工地

项目安全员,自学 Python + LLM。正在从现场安全岗转向 **AI × 建工科技**。

- GitHub: [@yjl666-ai](https://github.com/yjl666-ai)
- 邮箱:yuanjiale2026@163.com

---

## License

MIT — 自由使用、修改、商用。详见 [LICENSE](LICENSE)。
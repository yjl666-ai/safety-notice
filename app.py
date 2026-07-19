#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — 智安通 Web UI (多隐患版本)

用法:
    ./venv/bin/python app.py
然后浏览器打开 http://localhost:5000
"""
import sys
import subprocess
import os
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string

HERE = Path(__file__).parent.resolve()
os.chdir(HERE)

app = Flask(__name__)

INDEX_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>智安通 · Safety Notice AI</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
           max-width: 820px; margin: 32px auto; padding: 0 18px; color: #1f2937; }
    h1 { font-size: 28px; margin-bottom: 4px; }
    .sub { color: #6b7280; margin: 0 0 24px; font-size: 14px; }
    .row { margin-bottom: 16px; }
    label { display: block; font-weight: 600; margin-bottom: 6px; font-size: 14px; }
    textarea { width: 100%; min-height: 140px; padding: 12px;
              font-size: 14px; border-radius: 8px;
              border: 1px solid #d1d5db; font-family: inherit;
              resize: vertical; line-height: 1.6; }
    textarea:focus { outline: none; border-color: #2563eb;
                     box-shadow: 0 0 0 3px rgba(37,99,235,0.15); }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 6px; }
    button { background: #2563eb; color: white; border: none;
             padding: 10px 18px; border-radius: 8px; cursor: pointer;
             font-size: 14px; font-weight: 500; }
    button:hover { background: #1d4ed8; }
    button:disabled { background: #9ca3af; cursor: not-allowed; }
    .btn-secondary { background: #64748b; }
    .btn-secondary:hover { background: #475569; }
    .btn-success { background: #059669; }
    .btn-success:hover { background: #047857; }
    .status { padding: 10px 14px; border-radius: 8px; margin: 14px 0;
              font-size: 14px; display: none; }
    .status.info    { background: #dbeafe; color: #1e40af; }
    .status.success { background: #d1fae5; color: #065f46; }
    .status.error   { background: #fee2e2; color: #991b1b; }
    pre.output { background: #1f2937; color: #e5e7eb; padding: 18px;
                 border-radius: 8px; white-space: pre-wrap;
                 font-size: 13px; line-height: 1.6; max-height: 500px;
                 overflow: auto; display: none; font-family: ui-monospace, "Cascadia Mono", Consolas, monospace; }
    .hr { border: 0; border-top: 1px solid #e5e7eb; margin: 24px 0; }
    .footer { color: #9ca3af; font-size: 12px; margin-top: 32px; text-align: center; }
    .copy { background: #f3f4f6; border: 1px solid #e5e7eb;
            padding: 4px 10px; border-radius: 6px; cursor: pointer;
            font-size: 12px; }
    .copy:hover { background: #e5e7eb; }
    .hint { font-size: 12px; color: #9ca3af; }
  </style>
</head>
<body>
  <h1>🔧 智安通 <span style="font-size:18px; color:#9ca3af">Safety Notice AI</span></h1>
  <p class="sub">施工现场安全隐患整改通知书 · 多隐患智能生成器</p>

  <div class="row">
    <label>隐患描述 <span class="hint">(每行一条,1-6 条;AI 会融合成一段描述 + 针对性整改)</span></label>
    <textarea id="hazards" placeholder="例:
电线泡水未及时处理
高处作业未系安全带
基坑边坡堆土超载
灭火器失效"></textarea>
  </div>

  <div class="actions">
    <button id="btn-ai" onclick="aiSuggest()">🤖 AI 出通知</button>
    <button class="btn-secondary" id="btn-docx" onclick="makeDocx()">📝 生成 .docx 并打开 Word</button>
    <button class="copy" onclick="copyOutput()">复制通知</button>
  </div>

  <div id="status" class="status"></div>

  <hr class="hr">
  <div class="hint">通知内容 ↓(可复制 / 可滚动)</div>
  <pre id="output" class="output"></pre>

  <div class="footer">智安通 v0.3 · Flask UI · MIT · 多隐患版本</div>

  <script>
    function status(msg, kind='info') {
      const s = document.getElementById('status');
      s.className = 'status ' + kind;
      s.textContent = msg;
      s.style.display = 'block';
    }
    function setBusy(b) {
      document.getElementById('btn-ai').disabled = b;
      document.getElementById('btn-docx').disabled = b;
    }
    function parseHazards() {
      const raw = document.getElementById('hazards').value;
      return raw.split('\\n').map(s => s.trim()).filter(Boolean);
    }
    async function aiSuggest() {
      const hazards = parseHazards();
      if (hazards.length === 0) { status('⚠ 请先输入至少一条隐患描述', 'error'); return; }
      if (hazards.length > 6) { status('⚠ 一次最多 6 条,请精简', 'error'); return; }
      setBusy(true);
      status(`🤖 AI 在思考中... (${hazards.length} 条隐患,通常 5-15 秒)`, 'info');
      document.getElementById('output').style.display = 'none';
      try {
        const r = await fetch('/api/ai', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({hazards}),
        });
        const d = await r.json();
        if (d.error) { status('❌ ' + d.error, 'error'); return; }
        document.getElementById('output').textContent = d.text;
        document.getElementById('output').style.display = 'block';
        status(`✅ 通知已生成 (${hazards.length} 条隐患 → 1 段描述 + ${hazards.length} 条针对性整改)`, 'success');
      } catch (e) {
        status('❌ 网络错误:' + e, 'error');
      } finally {
        setBusy(false);
      }
    }
    async function makeDocx() {
      setBusy(true);
      status('📝 生成 .docx 中...', 'info');
      try {
        const r = await fetch('/api/docx', {method: 'POST'});
        const d = await r.json();
        if (d.error) { status('❌ ' + d.error, 'error'); return; }
        status('✅ .docx 已生成,Word 正在打开...', 'success');
      } catch (e) {
        status('❌ 出错:' + e, 'error');
      } finally {
        setBusy(false);
      }
    }
    function copyOutput() {
      const t = document.getElementById('output').textContent;
      if (!t) { status('⚠ 没有内容可复制', 'error'); return; }
      navigator.clipboard.writeText(t).then(() => {
        status('✅ 已复制到剪贴板', 'success');
      });
    }
  </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(INDEX_HTML)


@app.route('/api/ai', methods=['POST'])
def api_ai():
    try:
        data = request.get_json(silent=True) or {}
        hazards = data.get('hazards') or []
        if isinstance(hazards, str):
            # 兼容旧版单字符串调用
            hazards = [s.strip() for s in hazards.split('\n') if s.strip()]
        hazards = [s for s in (str(h).strip() for h in hazards) if s]
        if not hazards:
            return jsonify({'error': '隐患描述为空'}), 400
        if len(hazards) > 6:
            return jsonify({'error': '一次最多 6 条隐患'}), 400

        # 调 ai_suggest.py (stdin 喂 hazards,每行一条)
        proc = subprocess.run(
            [sys.executable, str(HERE / 'ai_suggest.py')],
            input='\n'.join(hazards),
            capture_output=True,
            text=True,
            cwd=str(HERE),
            timeout=90,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
        )

        if proc.returncode != 0:
            return jsonify({'error': proc.stderr.strip() or 'AI 调用失败'}), 500

        return jsonify({'text': proc.stdout, 'count': len(hazards)})
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'AI 思考超时(90s)'}), 504
    except Exception as e:
        return jsonify({'error': f'服务器错误:{e}'}), 500


@app.route('/api/docx', methods=['POST'])
def api_docx():
    try:
        yaml_path = HERE / 'notice.yaml'
        if not yaml_path.exists():
            return jsonify({'error': '请先点 "AI 出通知" 生成内容'}), 400

        # 直接调 generate_notice.py 出 docx,不依赖 bash
        proc = subprocess.run(
            [sys.executable, str(HERE / 'generate_notice.py'),
             'notice.yaml', '整改通知.docx'],
            cwd=str(HERE),
            capture_output=True,
            text=True,
            timeout=20,
        )

        if proc.returncode != 0:
            return jsonify({'error': (proc.stderr or proc.stdout or '生成失败').strip()}), 500

        # 试图打开 Word(失败不阻断)
        try:
            subprocess.Popen(
                ['cmd.exe', '/c', 'start', '', str(HERE / '整改通知.docx')],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass  # 不影响成功状态

        return jsonify({
            'ok': True,
            'path': 'D:\\新建文件夹\\龙虾\\safety-notice\\整改通知.docx',
        })
    except Exception as e:
        return jsonify({'error': f'服务器错误:{e}'}), 500


@app.route('/health')
def health():
    return jsonify({'ok': True})


if __name__ == '__main__':
    # HF Spaces 期望 PORT=7860,本地默认 5000
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    print(f'\n✅ 智安通 UI 已启动:')
    print(f'   浏览器打开: http://localhost:{port}\n')
    app.run(host=host, port=port, debug=False, use_reloader=False)
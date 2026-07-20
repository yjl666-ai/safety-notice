#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — 智安通 Web UI (v0.4.1: 文本 + 照片双模式)

用法:
    python app.py
然后浏览器打开 http://localhost:5000
"""
import sys
import subprocess
import os
import shutil
import tempfile
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename

import db  # 数据库模块

HERE = Path(__file__).parent.resolve()
os.chdir(HERE)
db.init_db()  # 启动时自动建表

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB 上传限制

INDEX_HTML = r"""
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

    /* ── 模式切换 tab ── */
    .tabs { display: flex; gap: 0; margin-bottom: 24px; border-bottom: 2px solid #e5e7eb; }
    .tab { padding: 10px 24px; cursor: pointer; font-size: 14px; font-weight: 500;
           color: #6b7280; border-bottom: 2px solid transparent; margin-bottom: -2px;
           transition: all .15s; user-select: none; }
    .tab:hover { color: #374151; }
    .tab.active { color: #2563eb; border-bottom-color: #2563eb; }

    /* ── 通用 ── */
    .row { margin-bottom: 16px; }
    label { display: block; font-weight: 600; margin-bottom: 6px; font-size: 14px; }
    textarea { width: 100%; min-height: 140px; padding: 12px;
              font-size: 14px; border-radius: 8px;
              border: 1px solid #d1d5db; font-family: inherit;
              resize: vertical; line-height: 1.6; }
    textarea:focus { outline: none; border-color: #2563eb;
                     box-shadow: 0 0 0 3px rgba(37,99,235,0.15); }

    /* ── 照片上传区 ── */
    .drop-zone { border: 2px dashed #d1d5db; border-radius: 12px; padding: 40px 20px;
                 text-align: center; cursor: pointer; transition: all .2s; min-height: 160px;
                 display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .drop-zone:hover, .drop-zone.drag-over { border-color: #2563eb; background: #f0f5ff; }
    .drop-zone.has-files { border-style: solid; border-color: #059669; background: #f0fdf4; }
    .drop-icon { font-size: 40px; margin-bottom: 8px; }
    .drop-text { font-size: 14px; color: #6b7280; }
    .drop-hint { font-size: 12px; color: #9ca3af; margin-top: 4px; }

    /* ── 缩略图预览 ── */
    .preview-grid { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
    .preview-item { position: relative; width: 100px; height: 100px; border-radius: 8px;
                    overflow: hidden; border: 1px solid #e5e7eb; }
    .preview-item img { width: 100%; height: 100%; object-fit: cover; }
    .preview-item .remove { position: absolute; top: 2px; right: 2px;
          background: rgba(0,0,0,.6); color: white; border: none; border-radius: 50%;
          width: 22px; height: 22px; font-size: 12px; cursor: pointer; line-height: 22px; text-align: center; }
    .preview-item .filename { position: absolute; bottom: 0; left: 0; right: 0;
          background: rgba(0,0,0,.5); color: white; font-size: 10px; padding: 2px 4px;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* ── 按钮 & 状态 ── */
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
    .status.info    { background: #dbeafe; color: #1e40af; display: block; }
    .status.success { background: #d1fae5; color: #065f46; display: block; }
    .status.error   { background: #fee2e2; color: #991b1b; display: block; }
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
  <p class="sub">施工现场安全隐患整改通知书 · 双模式智能生成器</p>

  <!-- ── 模式切换 ── -->
  <div class="tabs">
    <div class="tab active" onclick="switchMode('text')" id="tab-text">📝 文本输入</div>
    <div class="tab" onclick="switchMode('photo')" id="tab-photo">📷 照片上传</div>
  </div>

  <!-- ── 文本模式 ── -->
  <div id="panel-text">
    <div class="row">
      <label>隐患描述 <span class="hint">(每行一条,1-6 条;AI 会融合成一段描述 + 针对性整改)</span></label>
      <textarea id="hazards" placeholder="例:
电线泡水未及时处理
高处作业未系安全带
基坑边坡堆土超载
灭火器失效"></textarea>
    </div>
  </div>

  <!-- ── 照片模式 ── -->
  <div id="panel-photo" style="display:none">
    <div class="row">
      <label>上传工地照片 <span class="hint">(支持 .jpg .png .webp .bmp · Qwen-VL-Max 看图识别隐患)</span></label>
      <div class="drop-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
        <div class="drop-icon">📷</div>
        <div class="drop-text">点击选择照片 或拖拽到此处</div>
        <div class="drop-hint" id="file-count">每次最多 6 张</div>
      </div>
      <input type="file" id="file-input" accept="image/jpeg,image/png,image/webp,image/bmp"
             multiple style="display:none" onchange="handleFiles(this.files)">
      <div class="preview-grid" id="preview-grid"></div>
    </div>
  </div>

  <!-- ── 按钮 ── -->
  <div class="actions">
    <button id="btn-ai" onclick="aiSuggest()">🤖 AI 出通知</button>
    <button class="btn-secondary" id="btn-docx" onclick="makeDocx()">📝 生成 .docx</button>
    <button class="copy" onclick="copyOutput()">复制通知</button>
  </div>

  <div id="status" class="status"></div>

  <hr class="hr">
  <div class="hint">通知内容 ↓(可复制 / 可滚动)</div>
  <pre id="output" class="output"></pre>

  <div class="footer">智安通 v0.5 · Flask UI · MIT · <a href="/history">📋 历史记录</a></div>

  <script>
    // ── 模式切换 ──
    let currentMode = 'text';
    function switchMode(mode) {
      currentMode = mode;
      document.getElementById('panel-text').style.display = mode === 'text' ? '' : 'none';
      document.getElementById('panel-photo').style.display = mode === 'photo' ? '' : 'none';
      document.getElementById('tab-text').classList.toggle('active', mode === 'text');
      document.getElementById('tab-photo').classList.toggle('active', mode === 'photo');
    }

    // ── 照片文件管理 ──
    let selectedFiles = [];
    function handleFiles(files) {
      for (const f of files) {
        if (selectedFiles.length >= 6) break;
        if (!f.type.startsWith('image/')) continue;
        if (!selectedFiles.some(x => x.name === f.name && x.size === f.size)) {
          selectedFiles.push(f);
        }
      }
      document.getElementById('file-input').value = '';
      renderPreviews();
    }

    function removeFile(idx) {
      selectedFiles.splice(idx, 1);
      renderPreviews();
    }

    function renderPreviews() {
      const grid = document.getElementById('preview-grid');
      const zone = document.getElementById('drop-zone');
      const count = document.getElementById('file-count');
      grid.innerHTML = '';
      selectedFiles.forEach((f, i) => {
        const div = document.createElement('div');
        div.className = 'preview-item';
        const img = document.createElement('img');
        img.src = URL.createObjectURL(f);
        const rm = document.createElement('span');
        rm.className = 'remove';
        rm.textContent = '✕';
        rm.onclick = (e) => { e.stopPropagation(); removeFile(i); };
        const nm = document.createElement('div');
        nm.className = 'filename';
        nm.textContent = f.name;
        div.appendChild(img); div.appendChild(rm); div.appendChild(nm);
        grid.appendChild(div);
      });
      if (selectedFiles.length > 0) {
        zone.classList.add('has-files');
        count.textContent = `已选 ${selectedFiles.length} 张`;
      } else {
        zone.classList.remove('has-files');
        count.textContent = '每次最多 6 张';
      }
    }

    // ── 拖拽支持 ──
    const dropZone = document.getElementById('drop-zone');
    dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', e => {
      e.preventDefault();
      dropZone.classList.remove('drag-over');
      handleFiles(e.dataTransfer.files);
    });

    // ── 状态 & 通用 ──
    function status(msg, kind) {
      const s = document.getElementById('status');
      s.className = 'status ' + (kind || 'info');
      s.textContent = msg;
    }
    function setBusy(b) {
      document.getElementById('btn-ai').disabled = b;
      document.getElementById('btn-docx').disabled = b;
    }

    // ── AI 出通知 ──
    async function aiSuggest() {
      if (currentMode === 'text') {
        await aiSuggestText();
      } else {
        await aiSuggestPhoto();
      }
    }

    async function aiSuggestText() {
      const raw = document.getElementById('hazards').value;
      const hazards = raw.split('\n').map(s => s.trim()).filter(Boolean);
      if (!hazards.length) { status('⚠ 请先输入至少一条隐患描述', 'error'); return; }
      if (hazards.length > 6) { status('⚠ 一次最多 6 条', 'error'); return; }
      setBusy(true);
      status(`🤖 AI 思考中... (${hazards.length} 条隐患)`, 'info');
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
        status(`✅ 通知已生成 (${hazards.length} 条隐患)`, 'success');
      } catch (e) {
        status('❌ 网络错误: ' + e, 'error');
      } finally { setBusy(false); }
    }

    async function aiSuggestPhoto() {
      if (!selectedFiles.length) { status('⚠ 请先选择照片', 'error'); return; }
      setBusy(true);
      status(`🔍 Qwen-VL-Max 识别 ${selectedFiles.length} 张照片中...`, 'info');
      document.getElementById('output').style.display = 'none';
      try {
        const fd = new FormData();
        selectedFiles.forEach(f => fd.append('photos', f));
        const r = await fetch('/api/photos', { method: 'POST', body: fd });
        const d = await r.json();
        if (d.error) { status('❌ ' + d.error, 'error'); return; }
        document.getElementById('output').textContent = d.text;
        document.getElementById('output').style.display = 'block';
        status(`✅ 通知已生成 (${d.count} 张照片 → ${d.count} 条隐患)`, 'success');
      } catch (e) {
        status('❌ 网络错误: ' + e, 'error');
      } finally { setBusy(false); }
    }

    async function makeDocx() {
      setBusy(true);
      status('📝 生成 .docx 中...', 'info');
      try {
        const r = await fetch('/api/docx', {method: 'POST'});
        const d = await r.json();
        if (d.error) { status('❌ ' + d.error, 'error'); return; }
        status('✅ .docx 已生成 → ' + d.path, 'success');
      } catch (e) {
        status('❌ 出错: ' + e, 'error');
      } finally { setBusy(false); }
    }

    function copyOutput() {
      const t = document.getElementById('output').textContent;
      if (!t) { status('⚠ 没有内容可复制', 'error'); return; }
      navigator.clipboard.writeText(t).then(() => status('✅ 已复制到剪贴板', 'success'));
    }
  </script>
</body>
</html>
"""


# ════════════════════════════════════════════════════════════════
# API 路由
# ════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)


@app.route('/api/ai', methods=['POST'])
def api_ai():
    """文本模式:隐患列表 → AI 出通知"""
    try:
        data = request.get_json(silent=True) or {}
        hazards = data.get('hazards') or []
        if isinstance(hazards, str):
            hazards = [s.strip() for s in hazards.split('\n') if s.strip()]
        hazards = [s for s in (str(h).strip() for h in hazards) if s]
        if not hazards:
            return jsonify({'error': '隐患描述为空'}), 400
        if len(hazards) > 6:
            return jsonify({'error': '一次最多 6 条隐患'}), 400

        proc = subprocess.run(
            [sys.executable, str(HERE / 'ai_suggest.py'), '--output', 'notice'],
            input='\n'.join(hazards),
            capture_output=True, text=True,
            cwd=str(HERE), timeout=90,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
        )
        if proc.returncode != 0:
            return jsonify({'error': proc.stderr.strip() or 'AI 调用失败'}), 500
        # 存档到数据库
        db.save_notice("", "text", hazards, proc.stdout)
        return jsonify({'text': proc.stdout, 'count': len(hazards)})
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'AI 思考超时(90s)'}), 504
    except Exception as e:
        return jsonify({'error': f'服务器错误:{e}'}), 500


@app.route('/api/photos', methods=['POST'])
def api_photos():
    """照片模式:上传照片 → Qwen-VL 识别 → DeepSeek 出通知"""
    files = request.files.getlist('photos')
    if not files or len(files) == 0:
        return jsonify({'error': '请选择至少一张照片'}), 400
    if len(files) > 6:
        return jsonify({'error': '一次最多 6 张照片'}), 400

    tmpdir = None
    try:
        # 保存上传文件到临时目录
        tmpdir = tempfile.mkdtemp(prefix='safety-photos-')
        saved = []
        for f in files:
            if f.filename:
                name = secure_filename(f.filename) or f'photo_{len(saved)}.jpg'
                path = os.path.join(tmpdir, name)
                f.save(path)
                saved.append(path)

        if not saved:
            return jsonify({'error': '没有有效的照片文件'}), 400

        # 调 ai_suggest.py --photos
        proc = subprocess.run(
            [sys.executable, str(HERE / 'ai_suggest.py'),
             '--photos'] + saved + ['--output', 'notice'],
            capture_output=True, text=True,
            cwd=str(HERE), timeout=120,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
        )
        if proc.returncode != 0:
            err = proc.stderr.strip() or 'AI 调用失败'
            return jsonify({'error': err}), 500

        # 统计成功识别的隐患条数
        count = sum(1 for ln in proc.stderr.split('\n') if ln.startswith('✓ ['))
        # 从 stderr 提取隐患描述（格式: "✓ [1/3] file.jpg: 隐患描述..."）
        hazards = []
        for ln in proc.stderr.split('\n'):
            if ln.startswith('✓ [') and ': ' in ln:
                hazards.append(ln.split(': ', 1)[1].strip())
        # 存档到数据库
        db.save_notice("", "photos", hazards or [f"{count}条隐患"], proc.stdout, photo_count=count)
        return jsonify({'text': proc.stdout, 'count': count})
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'AI 思考超时(120s)'}), 504
    except Exception as e:
        return jsonify({'error': f'服务器错误:{e}'}), 500
    finally:
        if tmpdir and os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)


@app.route('/api/docx', methods=['POST'])
def api_docx():
    """生成 .docx 并返回下载链接"""
    try:
        yaml_path = HERE / 'notice.yaml'
        if not yaml_path.exists():
            return jsonify({'error': '请先点 "AI 出通知" 生成内容'}), 400

        proc = subprocess.run(
            [sys.executable, str(HERE / 'generate_notice.py'),
             'notice.yaml', '整改通知.docx'],
            cwd=str(HERE),
            capture_output=True, text=True, timeout=20,
        )
        if proc.returncode != 0:
            return jsonify({'error': (proc.stderr or proc.stdout or '生成失败').strip()}), 500

        return jsonify({
            'ok': True,
            'path': str((HERE / '整改通知.docx').resolve()),
        })
    except Exception as e:
        return jsonify({'error': f'服务器错误:{e}'}), 500


@app.route('/api/history')
def api_history():
    """返回历史记录 JSON"""
    rows = db.list_notices(50)
    return jsonify(rows)


@app.route('/history')
def history_page():
    """历史记录页面"""
    rows = db.list_notices(50)
    items = ""
    for r in rows:
        hazards_parsed = []
        try:
            import json as _json
            hazards_parsed = _json.loads(r["hazards"])
        except Exception:
            hazards_parsed = [r["hazards"]]
        hazards_str = "、".join(hazards_parsed[:3])
        source_label = "📷" if r["source"] == "photos" else "📝"
        items += f"""
        <div style="border:1px solid #e5e7eb;border-radius:8px;padding:14px;margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <strong>#{r["id"]} {source_label} {r["project"] or "未命名"}</strong>
            <span style="color:#9ca3af;font-size:12px">{r["created_at"]}</span>
          </div>
          <div style="color:#6b7280;font-size:13px;margin-top:6px">{hazards_str}</div>
          <details style="margin-top:8px">
            <summary style="cursor:pointer;color:#2563eb;font-size:13px">查看通知全文</summary>
            <pre style="background:#1f2937;color:#e5e7eb;padding:14px;border-radius:6px;font-size:12px;white-space:pre-wrap;margin-top:6px">{r["notice"]}</pre>
          </details>
        </div>"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>历史记录 · 智安通</title>
<style>
*{{box-sizing:border-box}}body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;max-width:820px;margin:32px auto;padding:0 18px;color:#1f2937}}
h1{{font-size:24px}}a{{color:#2563eb;text-decoration:none}}a:hover{{text-decoration:underline}}
.back{{display:inline-block;margin-bottom:20px;font-size:14px}}
</style></head>
<body>
<a class="back" href="/">← 返回首页</a>
<h1>📋 历史记录</h1>
<p style="color:#9ca3af;font-size:14px">共 {len(rows)} 条通知</p>
{items}
</body></html>"""


@app.route('/health')
def health():
    return jsonify({'ok': True})


if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    print(f'\n✅ 智安通 UI 已启动 (v0.4.1 文本+照片双模式):')
    print(f'   浏览器打开: http://localhost:{port}\n')
    app.run(host=host, port=port, debug=False, use_reloader=False)

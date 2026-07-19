# set-dashscope-key.ps1
# ── 一次性配置 阿里云百炼(Qwen-VL) API key ──
# 用法: PowerShell 里跑 `& "D:\新建文件夹\龙虾\safety-notice\scripts\set-dashscope-key.ps1"`
#       然后按提示粘贴新 key
#
# 注: 如果你的 key 是 sk-ws-... 格式(看起来像 LiteLLM proxy 颁发),
#     说明你走的是代理,记得同时设 DASHSCOPE_BASE_URL 环境变量:
#     [Environment]::SetEnvironmentVariable("DASHSCOPE_BASE_URL", "https://your-proxy.com/v1", "User")

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  阿里云百炼 (Qwen-VL) API key 配置向导" -ForegroundColor Cyan
Write-Host "══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "操作流程:"
Write-Host "  1. 浏览器打开 https://dashscope.console.aliyun.com/apiKey"
Write-Host "  2. 删除旧 key(⚠️ 如果在 chat/桌面脚本里露过面,务必先 rotate)" -ForegroundColor Yellow
Write-Host "  3. 创建新 key → 复制(只显示一次!)" -ForegroundColor Yellow
Write-Host "  4. 回来把新 key 粘到下面,回车" -ForegroundColor Cyan
Write-Host ""

# ── 读 key(输入不可见)──
$secure = Read-Host "粘贴新 key (输入隐藏)" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$plainKey = [System.Runtime.InteropServices.Marshal].PtrToStringAuto($BSTR)

if ([string]::IsNullOrWhiteSpace($plainKey)) {
    Write-Host "❌ key 是空的。" -ForegroundColor Red
    exit 1
}

# ── 写到 Windows 用户级环境变量(永久)──
[Environment]::SetEnvironmentVariable("DASHSCOPE_API_KEY", $plainKey, "User")

# ── 写到 WSL 文件(权限 600,只有你能读)──
$tempFile = Join-Path $env:TEMP "_dashscope_key.tmp"
try {
    $plainKey | Out-File -FilePath $tempFile -Encoding utf8 -NoNewline
    wsl bash -c "mkdir -p ~/.config && cp '$tempFile' ~/.config/dashscope_key.txt && chmod 600 ~/.config/dashscope_key.txt && rm '$tempFile'"
} finally {
    Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
}

# ── 配置 WSLENV 透传(让 wsl 看到 Windows 环境变量)──
$profilePath = "$env:USERPROFILE\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
$marker = '# === DASHSCOPE_KEY_WSLENV ==='
if (Test-Path $profilePath) {
    $content = Get-Content $profilePath -Raw
    if ($content -notmatch [regex]::Escape($marker)) {
        Add-Content -Path $profilePath -Value @"

$marker
`$env:WSLENV = (`$env:WSLENV + ':DASHSCOPE_API_KEY/u').Trim(':')
"@
    }
}

# ── 清理内存 ──
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR) | Out-Null
Remove-Variable plainKey -ErrorAction SilentlyContinue

# ── 检查 ──
Write-Host ""
Write-Host "✓ 配置完成" -ForegroundColor Green
Write-Host "  · Windows 环境变量:DASHSCOPE_API_KEY (用户级,新开 PowerShell 生效)"
Write-Host "  · WSL 文件:~/.config/dashscope_key.txt (权限 600)"
Write-Host "  · WSLENV 桥接:已配置(下次开 PowerShell 生效)"
Write-Host ""
Write-Host "下一步:" -ForegroundColor Cyan
Write-Host "  1. 关闭所有 PowerShell 窗口,新开一个"
Write-Host "  2. 试: ai-suggest --photos photo.jpg"
Write-Host ""
Write-Host "⚠️  如果你的 key 是 sk-ws-... 格式(代理),还要设:" -ForegroundColor Yellow
Write-Host "   [Environment]::SetEnvironmentVariable('DASHSCOPE_BASE_URL', 'https://your-proxy/v1', 'User')" -ForegroundColor Yellow
Write-Host ""
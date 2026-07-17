# set-deepseek-key.ps1
# ── 一次性配置 DeepSeek API key ──
# 用法: PowerShell 里跑 `& "D:\新建文件夹\龙虾\safety-notice\set-deepseek-key.ps1"`
#       然后按提示粘贴新 key

$ErrorActionPreference = "Stop"
$SecretDir = "D:\新建文件夹\龙虾\safety-notice\.secrets"

Write-Host ""
Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  DeepSeek API key 配置向导" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "操作流程:"
Write-Host "  1. 浏览器打开 https://platform.deepseek.com/api_keys"
Write-Host "  2. 删除旧 key sk-642…f787(已暴露在 chat 里)" -ForegroundColor Yellow
Write-Host "  3. 创建新 key → 复制(只显示一次!)" -ForegroundColor Yellow
Write-Host "  4. 回来把新 key 粘到下面,回车" -ForegroundColor Cyan
Write-Host ""

# ── 读 key(输入不可见)──
$secure = Read-Host "粘贴新 key (输入隐藏)" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$plainKey = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

if ([string]::IsNullOrWhiteSpace($plainKey)) {
    Write-Host "❌ key 是空的。" -ForegroundColor Red
    exit 1
}
if (-not $plainKey.StartsWith("sk-")) {
    Write-Host "⚠ key 不像标准 sk- 开头,继续但请核对。" -ForegroundColor Yellow
}

# ── 写到 Windows 用户级环境变量(永久)──
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", $plainKey, "User")

# ── 写到 WSL 文件(权限 600,只有你能读)──
New-Item -ItemType Directory -Force -Path $SecretDir | Out-Null
$tempFile = Join-Path $SecretDir "_key.tmp"
try {
    $plainKey | Out-File -FilePath $tempFile -Encoding utf8 -NoNewline
    $wslDest = "/root/.config/deepseek_key.txt"
    wsl bash -c "mkdir -p ~/.config && cp '$tempFile' '$wslDest' && chmod 600 '$wslDest' && rm '$tempFile'"
} finally {
    Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
}

# ── 配置 WSLENV 透传(让 wsl 看到 Windows 环境变量)──
$profilePath = "$env:USERPROFILE\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
$marker = '# === DEEPSEEK_KEY_WSLENV ==='
if (Test-Path $profilePath) {
    $content = Get-Content $profilePath -Raw
    if ($content -notmatch [regex]::Escape($marker)) {
        Add-Content -Path $profilePath -Value @"

$marker
`$env:WSLENV = 'DEEPSEEK_API_KEY/u'
"@
    }
}

# ── 清理内存 ──
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR) | Out-Null
Remove-Variable plainKey -ErrorAction SilentlyContinue

# ── 检查 ──
Write-Host ""
Write-Host "✓ 配置完成" -ForegroundColor Green
Write-Host "  · Windows 环境变量:DEEPSEEK_API_KEY (用户级,新开 PowerShell 生效)"
Write-Host "  · WSL 文件:~/.config/deepseek_key.txt (权限 600)"
Write-Host "  · WSLENV 桥接:已配置(下次开 PowerShell 生效)"
Write-Host ""
Write-Host "下一步:" -ForegroundColor Cyan
Write-Host "  1. 关闭所有 PowerShell 窗口,新开一个"
Write-Host "  2. 试:`ai-suggest 电线泡水`"
Write-Host ""

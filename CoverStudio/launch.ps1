param(
    [string]$Page = "/",
    [int]$Port = 8791
)

$ErrorActionPreference = "SilentlyContinue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseUrl = "http://127.0.0.1:$Port"
$TargetUrl = "$BaseUrl$Page"

function Test-StudioAlive {
    try {
        $resp = Invoke-RestMethod -Uri "$BaseUrl/state" -TimeoutSec 2
        return ($null -ne $resp -and $null -ne $resp.state)
    } catch {
        return $false
    }
}

if (-not (Test-StudioAlive)) {
    $candidates = @(
        (Get-Command pythonw.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
        "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe",
        (Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    ) | Where-Object { $_ -and (Test-Path $_) }

    $PyExe = $candidates | Select-Object -First 1
    if (-not $PyExe) {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show("未找到 Python 环境，请先安装 Python 3.10+。", "INKA+ 设计台") | Out-Null
        exit 1
    }

    $StudioPy = Join-Path $Root "studio.py"
    Start-Process -FilePath $PyExe -ArgumentList @("`"$StudioPy`"", "serve", "--port", "$Port") -WorkingDirectory $Root -WindowStyle Hidden

    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 250
        if (Test-StudioAlive) { break }
    }
}

if (Test-StudioAlive) {
    Start-Process $TargetUrl
} else {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show("设计台服务未能启动（端口 $Port），请检查端口占用或手动运行 CoverStudio/启动封面工坊.cmd 查看报错。", "INKA+ 设计台") | Out-Null
    exit 1
}

param(
    [Parameter(Mandatory = $true)]
    [string]$TexBin
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$logs = Join-Path $root 'logs'
$source = Join-Path $root 'source'
$pdfDirectory = Join-Path $root 'pdf'
New-Item -ItemType Directory -Force -Path $logs, $pdfDirectory | Out-Null

$resolvedTexBin = (Resolve-Path -LiteralPath $TexBin).Path
$env:MMAGENT_TEX_BIN = $resolvedTexBin
$env:Path = "$resolvedTexBin;$env:Path"

function Invoke-CapturedCommand {
    param(
        [string]$Id,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $root
    )
    $stdout = Join-Path $logs "$Id.stdout.log"
    $stderr = Join-Path $logs "$Id.stderr.log"
    New-Item -ItemType File -Force -Path $stdout, $stderr | Out-Null
    $started = Get-Date
    try {
        $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -Wait -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        $exitCode = $process.ExitCode
        $startError = $null
    }
    catch {
        $exitCode = -1
        $startError = $_.Exception.Message
        $startError | Set-Content -LiteralPath $stderr -Encoding UTF8
    }
    $finished = Get-Date
    return [ordered]@{
        id = $Id
        file = $FilePath
        arguments = $Arguments
        working_directory = $WorkingDirectory
        started_at = $started.ToString('o')
        finished_at = $finished.ToString('o')
        duration_seconds = [math]::Round(($finished - $started).TotalSeconds, 3)
        exit_code = $exitCode
        stdout = (Resolve-Path -LiteralPath $stdout).Path
        stderr = (Resolve-Path -LiteralPath $stderr).Path
        start_error = $startError
    }
}

$commands = @()
$commands += Invoke-CapturedCommand -Id 'where-xelatex' -FilePath 'where.exe' -Arguments @('xelatex')
$commands += Invoke-CapturedCommand -Id 'xelatex-version' -FilePath 'xelatex.exe' -Arguments @('--version')
$commands += Invoke-CapturedCommand -Id 'where-latexmk' -FilePath 'where.exe' -Arguments @('latexmk')
$commands += Invoke-CapturedCommand -Id 'latexmk-version' -FilePath 'latexmk.exe' -Arguments @('-v')
$commands += Invoke-CapturedCommand -Id 'tlmgr-scheme-full' -FilePath 'tlmgr.bat' -Arguments @('info', '--only-installed', 'scheme-full')
$commands += Invoke-CapturedCommand -Id 'kpsewhich-ctexart' -FilePath 'kpsewhich.exe' -Arguments @('ctexart.cls')
$commands += Invoke-CapturedCommand -Id 'kpsewhich-booktabs' -FilePath 'kpsewhich.exe' -Arguments @('booktabs.sty')
$commands += Invoke-CapturedCommand -Id 'kpsewhich-graphicx' -FilePath 'kpsewhich.exe' -Arguments @('graphicx.sty')
$commands += Invoke-CapturedCommand -Id 'kpsewhich-amsmath' -FilePath 'kpsewhich.exe' -Arguments @('amsmath.sty')
$commands += Invoke-CapturedCommand -Id 'latexmk-chinese-acceptance' -FilePath 'latexmk.exe' -Arguments @('-xelatex', '-interaction=nonstopmode', '-halt-on-error', 'main.tex') -WorkingDirectory $source

$sourcePdf = Join-Path $source 'main.pdf'
$targetPdf = Join-Path $pdfDirectory 'xelatex_chinese_acceptance.pdf'
if (Test-Path -LiteralPath $sourcePdf) {
    Copy-Item -LiteralPath $sourcePdf -Destination $targetPdf -Force
}
$sourceEngineLog = Join-Path $source 'main.log'
if (Test-Path -LiteralPath $sourceEngineLog) {
    Copy-Item -LiteralPath $sourceEngineLog -Destination (Join-Path $logs 'chinese-acceptance-xelatex.log') -Force
}

$pdfExists = Test-Path -LiteralPath $targetPdf
$pdfSize = if ($pdfExists) { (Get-Item -LiteralPath $targetPdf).Length } else { 0 }
$pdfHeader = if ($pdfExists) {
    $bytes = [System.IO.File]::ReadAllBytes($targetPdf)
    if ($bytes.Length -ge 5) { [System.Text.Encoding]::ASCII.GetString($bytes, 0, 5) } else { '' }
} else { '' }
$pdfHash = if ($pdfExists) { (Get-FileHash -LiteralPath $targetPdf -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
$passed = ($commands | Where-Object { $_.exit_code -ne 0 }).Count -eq 0 -and $pdfExists -and $pdfSize -gt 1024 -and $pdfHeader -eq '%PDF-'
$summary = [ordered]@{
    schema_version = '1.0'
    checked_at = (Get-Date).ToString('o')
    tex_bin = $resolvedTexBin
    commands = $commands
    pdf = [ordered]@{
        path = if ($pdfExists) { (Resolve-Path -LiteralPath $targetPdf).Path } else { $targetPdf }
        exists = $pdfExists
        size_bytes = $pdfSize
        header = $pdfHeader
        sha256 = $pdfHash
    }
    status = if ($passed) { 'passed' } else { 'failed' }
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $root 'tex_environment_results.json') -Encoding UTF8
$summary | ConvertTo-Json -Depth 8
if (-not $passed) { exit 1 }

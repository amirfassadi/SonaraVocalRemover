$ErrorActionPreference = "Continue"

$inputFile = "C:\Users\Amir\Music\16. Daryache Noor.mp3"
$outputRoot = "D:\Dropbox\MirancoProjects\SonaraVocalRemover\sonara-backend\model-tests"

# مدل‌هایی که امشب تست می‌کنیم
$models = @(
    "htdemucs_ft",
    "htdemucs_6s",
    "mdx",
    "mdx_extra",
    "mdx_extra_q",
    "mdx_q",
    "repro_mdx_a",
    "repro_mdx_a_hybrid_only",
    "repro_mdx_a_time_only"
)

New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

foreach ($model in $models) {

    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host " STARTING MODEL: $model" -ForegroundColor Yellow
    Write-Host "=============================================" -ForegroundColor Cyan

    $modelOutput = Join-Path $outputRoot $model

    New-Item -ItemType Directory -Force -Path $modelOutput | Out-Null

    $startTime = Get-Date

    try {

        python -m demucs `
            -n $model `
            -d cpu `
            --two-stems=vocals `
            --float32 `
            -o $modelOutput `
            "$inputFile"

        $exitCode = $LASTEXITCODE

    }
    catch {

        Write-Host "ERROR running $model : $_" -ForegroundColor Red
        $exitCode = 1
    }

    $endTime = Get-Date
    $duration = $endTime - $startTime

    $logFile = Join-Path $modelOutput "result.txt"

    @"
Model: $model
Input: $inputFile
Started: $startTime
Finished: $endTime
Duration: $duration
ExitCode: $exitCode
"@ | Out-File -Encoding UTF8 $logFile

    if ($exitCode -eq 0) {
        Write-Host "MODEL COMPLETED: $model" -ForegroundColor Green
    }
    else {
        Write-Host "MODEL FAILED: $model" -ForegroundColor Red
    }

    Write-Host "Duration: $duration" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host " ALL MODEL TESTS FINISHED" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

Start-Sleep -Seconds 30

shutdown.exe /s /t 120 /c "SonaraVocalRemover - Demucs model tests completed"
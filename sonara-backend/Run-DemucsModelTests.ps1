param(
    [Parameter(Mandatory = $false)]
    [string]$InputFile = "C:\Users\Amir\Music\16. Daryache Noor.mp3",

    [Parameter(Mandatory = $false)]
    [string]$OutputRoot = (Join-Path $PSScriptRoot "model-tests"),

    # حداکثر زمان مجاز برای هر مدل
    [Parameter(Mandatory = $false)]
    [int]$TimeoutHours = 24,

    # تعداد jobهای دموکس. روی CPU پیشنهاد می‌شود 1 بماند تا مصرف
    # حافظه کنترل‌شده باشد.
    [Parameter(Mandatory = $false)]
    [int]$Jobs = 1,

    # فقط اگر این گزینه داده شود، بعد از اتمام همه مدل‌ها سیستم خاموش می‌شود
    [Parameter(Mandatory = $false)]
    [switch]$ShutdownWhenDone
)

$ErrorActionPreference = "Stop"

# ============================================================
# MODELS
# ============================================================

$Models = @(
    "htdemucs",
    "htdemucs_ft",
    "htdemucs_6s",
    "hdemucs_mmi",
    "mdx",
    "mdx_extra",
    "mdx_extra_q",
    "mdx_q",
    "repro_mdx_a",
    "repro_mdx_a_hybrid_only",
    "repro_mdx_a_time_only"
)

# ============================================================
# FUNCTIONS
# ============================================================

function Write-Log {
    param(
        [string]$Message,
        [string]$LogFile
    )

    $Line = "[{0}] {1}" -f `
        (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), `
        $Message

    Write-Host $Line

    Add-Content `
        -LiteralPath $LogFile `
        -Value $Line `
        -Encoding UTF8
}


function Get-TrackName {
    param(
        [string]$Path
    )

    return [System.IO.Path]::GetFileNameWithoutExtension($Path)
}


function Test-ModelCompleted {
    param(
        [string]$FinalDir,
        [string]$TrackName
    )

    $VocalsFile = Join-Path `
        $FinalDir `
        "$TrackName.vocals.wav"

    $InstrumentalFile = Join-Path `
        $FinalDir `
        "$TrackName.instrumental.wav"

    $MarkerFile = Join-Path `
        $FinalDir `
        "$TrackName.completed"

    # Complete فقط زمانی است که:
    # 1. vocals وجود داشته باشد
    # 2. instrumental وجود داشته باشد
    # 3. هر دو حجم بیشتر از صفر داشته باشند
    # 4. marker هم وجود داشته باشد

    if (
        (Test-Path -LiteralPath $VocalsFile -PathType Leaf) -and
        (Test-Path -LiteralPath $InstrumentalFile -PathType Leaf) -and
        (Test-Path -LiteralPath $MarkerFile -PathType Leaf)
    ) {

        $VocalsSize = (Get-Item -LiteralPath $VocalsFile).Length
        $InstrumentalSize = (Get-Item -LiteralPath $InstrumentalFile).Length

        if (
            ($VocalsSize -gt 0) -and
            ($InstrumentalSize -gt 0)
        ) {
            return $true
        }
    }

    return $false
}


function Remove-PreviousFinalFiles {
    param(
        [string]$FinalDir,
        [string]$TrackName
    )

    $FilesToRemove = @(
        "$TrackName.vocals.wav",
        "$TrackName.instrumental.wav",
        "$TrackName.completed"
    )

    foreach ($FileName in $FilesToRemove) {

        $Path = Join-Path `
            $FinalDir `
            $FileName

        if (Test-Path -LiteralPath $Path) {

            Write-Host `
                "Removing previous incomplete file: $Path"

            Remove-Item `
                -LiteralPath $Path `
                -Force
        }
    }
}


function Find-DemucsOutputs {
    param(
        [string]$DemucsModelDir,
        [string]$TrackName
    )

    # ========================================================
    # IMPORTANT
    #
    # NEVER search the whole model-tests directory.
    #
    # We search ONLY:
    #
    # <ModelOutput>\<Model>\<TrackName>\
    #
    # This prevents an old vocals.wav from another attempt
    # being mistaken for the new result.
    # ========================================================

    $TrackDir = Join-Path `
        $DemucsModelDir `
        $TrackName

    if (
        -not (
            Test-Path `
                -LiteralPath $TrackDir `
                -PathType Container
        )
    ) {
        return $null
    }

    $VocalsFile = Join-Path `
        $TrackDir `
        "vocals.wav"

    $InstrumentalFile = Join-Path `
        $TrackDir `
        "no_vocals.wav"

    if (
        (Test-Path -LiteralPath $VocalsFile -PathType Leaf) -and
        (Test-Path -LiteralPath $InstrumentalFile -PathType Leaf)
    ) {

        $VocalsSize = `
            (Get-Item -LiteralPath $VocalsFile).Length

        $InstrumentalSize = `
            (Get-Item -LiteralPath $InstrumentalFile).Length

        if (
            ($VocalsSize -gt 0) -and
            ($InstrumentalSize -gt 0)
        ) {

            return @{
                Vocals = $VocalsFile
                Instrumental = $InstrumentalFile
            }
        }
    }

    return $null
}


function Stop-ProcessTree {
    param(
        [System.Diagnostics.Process]$Process
    )

    # ========================================================
    # $Process.Kill() alone only kills the immediate process.
    # Demucs (and multiprocessing/jobs under it) can spawn
    # child python processes that would otherwise be left
    # running as orphans after a timeout kill.
    #
    # PowerShell 7+ / .NET Core 3+ supports Kill($true) which
    # kills the whole process tree. On Windows PowerShell 5.1
    # that overload doesn't exist, so we fall back to
    # taskkill /T /F which does the same thing via the OS.
    # ========================================================

    if ($null -eq $Process) {
        return
    }

    try {

        $KillMethod = $Process.GetType().GetMethod(
            "Kill",
            [Type[]]@([bool])
        )

        if ($null -ne $KillMethod) {

            # PowerShell 7+ / .NET Core: kill entire tree.
            $Process.Kill($true)
        }
        else {

            # Windows PowerShell 5.1 fallback.
            & taskkill.exe /PID $Process.Id /T /F | Out-Null
        }
    }
    catch {

        # Last resort fallback if either approach above throws.
        try {
            & taskkill.exe /PID $Process.Id /T /F | Out-Null
        }
        catch {
        }
    }
}


# ============================================================
# INITIAL CHECKS
# ============================================================

if (
    -not (
        Test-Path `
            -LiteralPath $InputFile `
            -PathType Leaf
    )
) {
    throw "Input file not found: $InputFile"
}


$PythonCommand = Get-Command `
    python `
    -ErrorAction SilentlyContinue

if (-not $PythonCommand) {
    throw "Python was not found. Please activate the Sonara .venv first."
}


$TrackName = Get-TrackName $InputFile


New-Item `
    -ItemType Directory `
    -Force `
    -Path $OutputRoot |
    Out-Null


$MainLog = Join-Path `
    $OutputRoot `
    "run-model-tests.log"


Add-Content `
    -LiteralPath $MainLog `
    -Value "" `
    -Encoding UTF8


Write-Log `
    "==================================================" `
    $MainLog

Write-Log `
    "SonaraVocalRemover Demucs Model Test" `
    $MainLog

Write-Log `
    "Input : $InputFile" `
    $MainLog

Write-Log `
    "Output: $OutputRoot" `
    $MainLog

Write-Log `
    "Jobs  : $Jobs" `
    $MainLog

Write-Log `
    "Models: $($Models -join ', ')" `
    $MainLog

Write-Log `
    "==================================================" `
    $MainLog


$TimeoutSeconds = $TimeoutHours * 3600


# ============================================================
# MODEL LOOP
# ============================================================

foreach ($Model in $Models) {

    $ModelOutput = Join-Path `
        $OutputRoot `
        $Model

    $FinalDir = Join-Path `
        $ModelOutput `
        "final"

    $LogFile = Join-Path `
        $ModelOutput `
        "$Model.log"


    New-Item `
        -ItemType Directory `
        -Force `
        -Path $ModelOutput |
        Out-Null


    New-Item `
        -ItemType Directory `
        -Force `
        -Path $FinalDir |
        Out-Null


    # ========================================================
    # CHECK IF ALREADY COMPLETE
    # ========================================================

    if (
        Test-ModelCompleted `
            -FinalDir $FinalDir `
            -TrackName $TrackName
    ) {

        Write-Log `
            "SKIP $Model - final outputs already complete." `
            $MainLog

        continue
    }


    # ========================================================
    # CLEAN PREVIOUS INCOMPLETE FINAL OUTPUT
    # ========================================================

    Remove-PreviousFinalFiles `
        -FinalDir $FinalDir `
        -TrackName $TrackName


    Write-Log "" $MainLog

    Write-Log `
        "=============================================" `
        $MainLog

    Write-Log `
        "STARTING MODEL: $Model" `
        $MainLog

    Write-Log `
        "=============================================" `
        $MainLog


    $StartTime = Get-Date

    $Process = $null


    try {

        # ====================================================
        # DEMUCS COMMAND
        # ====================================================

        $Arguments = @(
            "-m",
            "demucs",

            "-d",
            "cpu",

            "-n",
            $Model,

            "--two-stems=vocals",

            "--jobs",
            "$Jobs",

            "--float32",

            "--clip-mode",
            "rescale",

            "--filename",
            "{track}/{stem}.{ext}",

            "-o",
            $ModelOutput,

            $InputFile
        )


        # ====================================================
        # BUILD ARGUMENT STRING
        # ====================================================

        $ArgumentLine = (
            $Arguments |
            ForEach-Object {
                '"' + ($_ -replace '"', '\"') + '"'
            }
        ) -join " "


        # ====================================================
        # START PYTHON PROCESS
        # ====================================================

        $ProcessInfo = `
            New-Object System.Diagnostics.ProcessStartInfo

        $ProcessInfo.FileName = "python"

        $ProcessInfo.Arguments = $ArgumentLine

        $ProcessInfo.WorkingDirectory = `
            $PSScriptRoot

        $ProcessInfo.UseShellExecute = $false

        $ProcessInfo.RedirectStandardOutput = $true

        $ProcessInfo.RedirectStandardError = $true

        $ProcessInfo.CreateNoWindow = $true


        $Process = `
            New-Object System.Diagnostics.Process

        $Process.StartInfo = $ProcessInfo


        $null = $Process.Start()


        # ====================================================
        # READ OUTPUT ASYNCHRONOUSLY
        # Prevent stdout/stderr pipe deadlock
        # ====================================================

        $StdOutTask = `
            $Process.StandardOutput.ReadToEndAsync()

        $StdErrTask = `
            $Process.StandardError.ReadToEndAsync()


        $Deadline = `
            (Get-Date).AddSeconds($TimeoutSeconds)


        # ====================================================
        # MONITOR PROCESS
        # ====================================================

        $TimedOut = $false


        while (-not $Process.HasExited) {

            if ((Get-Date) -ge $Deadline) {

                $TimedOut = $true

                Write-Log `
                    "TIMEOUT: $Model exceeded $TimeoutHours hour(s)." `
                    $LogFile

                Write-Log `
                    "TIMEOUT: $Model exceeded $TimeoutHours hour(s). Terminating process tree." `
                    $MainLog

                Stop-ProcessTree -Process $Process

                try {
                    $Process.WaitForExit(30000) | Out-Null
                }
                catch {
                }

                throw `
                    "Model timeout after $TimeoutHours hour(s)."
            }


            Start-Sleep `
                -Seconds 10


            $Elapsed = `
                (Get-Date) - $StartTime


            Write-Host (
                "[{0}] {1} running - {2:hh\:mm\:ss}" -f
                (Get-Date -Format "HH:mm:ss"),
                $Model,
                $Elapsed
            )
        }


        # ====================================================
        # GET PROCESS OUTPUT
        # ====================================================

        # Only read the async task results if we didn't already
        # kill the process on timeout above (those tasks may
        # never complete cleanly after a hard kill).

        if (-not $TimedOut) {

            $StdOut = $StdOutTask.Result

            $StdErr = $StdErrTask.Result


            if ($StdOut) {

                Add-Content `
                    -LiteralPath $LogFile `
                    -Value $StdOut `
                    -Encoding UTF8
            }


            if ($StdErr) {

                Add-Content `
                    -LiteralPath $LogFile `
                    -Value $StdErr `
                    -Encoding UTF8
            }
        }


        $ExitCode = `
            $Process.ExitCode


        if ($ExitCode -ne 0) {

            throw `
                "Demucs exited with code $ExitCode."
        }


        # ====================================================
        # EXPECTED DEMUCS OUTPUT
        #
        # ModelOutput
        #    |
        #    +-- Model
        #         |
        #         +-- TrackName
        #              |
        #              +-- vocals.wav
        #              +-- no_vocals.wav
        #
        # ====================================================

        $DemucsModelDir = Join-Path `
            $ModelOutput `
            $Model


        $Outputs = Find-DemucsOutputs `
            -DemucsModelDir $DemucsModelDir `
            -TrackName $TrackName


        if ($null -eq $Outputs) {

            throw (
                "Demucs finished but valid output files were not found in: " +
                "$DemucsModelDir\$TrackName"
            )
        }


        # ====================================================
        # COPY VERIFIED OUTPUTS
        # ====================================================

        $FinalVocals = Join-Path `
            $FinalDir `
            "$TrackName.vocals.wav"


        $FinalInstrumental = Join-Path `
            $FinalDir `
            "$TrackName.instrumental.wav"


        Copy-Item `
            -LiteralPath $Outputs.Vocals `
            -Destination $FinalVocals `
            -Force


        Copy-Item `
            -LiteralPath $Outputs.Instrumental `
            -Destination $FinalInstrumental `
            -Force


        # ====================================================
        # VERIFY FINAL COPIES
        # ====================================================

        if (
            -not (
                Test-Path `
                    -LiteralPath $FinalVocals `
                    -PathType Leaf
            )
        ) {
            throw "Final vocals file was not created."
        }


        if (
            -not (
                Test-Path `
                    -LiteralPath $FinalInstrumental `
                    -PathType Leaf
            )
        ) {
            throw "Final instrumental file was not created."
        }


        $FinalVocalsSize = `
            (Get-Item -LiteralPath $FinalVocals).Length


        $FinalInstrumentalSize = `
            (Get-Item -LiteralPath $FinalInstrumental).Length


        if ($FinalVocalsSize -le 0) {
            throw "Final vocals file is empty."
        }


        if ($FinalInstrumentalSize -le 0) {
            throw "Final instrumental file is empty."
        }


        # ====================================================
        # IMPORTANT:
        #
        # COMPLETION MARKER IS CREATED ONLY AFTER EVERYTHING
        # HAS BEEN VERIFIED.
        # ====================================================

        $MarkerFile = Join-Path `
            $FinalDir `
            "$TrackName.completed"


        $MarkerContent = @"
model=$Model
input=$InputFile
completed=$(Get-Date -Format o)
vocals=$FinalVocals
instrumental=$FinalInstrumental
vocals_size=$FinalVocalsSize
instrumental_size=$FinalInstrumentalSize
"@


        Set-Content `
            -LiteralPath $MarkerFile `
            -Value $MarkerContent `
            -Encoding UTF8


        $Duration = `
            (Get-Date) - $StartTime


        Write-Log `
            "SUCCESS $Model - completed in $($Duration.ToString('hh\:mm\:ss'))" `
            $LogFile


        Write-Log `
            "SUCCESS $Model" `
            $MainLog
    }


    catch {

        Write-Log `
            "FAILED $Model - $($_.Exception.Message)" `
            $LogFile


        Write-Log `
            "FAILED $Model - $($_.Exception.Message) - continuing to next model." `
            $MainLog


        # مهم:
        # اینجا continue نمی‌زنیم چون finally باید اجرا شود.
        continue
    }


    finally {

        if ($null -ne $Process) {

            try {
                $Process.Dispose()
            }
            catch {
            }
        }
    }
}


# ============================================================
# FINISHED
# ============================================================

Write-Log "" $MainLog

Write-Log `
    "==================================================" `
    $MainLog

Write-Log `
    "ALL MODEL TESTS FINISHED" `
    $MainLog

Write-Log `
    "==================================================" `
    $MainLog


# ============================================================
# OPTIONAL SHUTDOWN
# ============================================================

if ($ShutdownWhenDone) {

    Write-Log `
        "Shutdown requested." `
        $MainLog

    Write-Log `
        "System will shut down in 60 seconds." `
        $MainLog


    shutdown.exe `
        /s `
        /t 60 `
        /c "SonaraVocalRemover Demucs model tests completed."
}

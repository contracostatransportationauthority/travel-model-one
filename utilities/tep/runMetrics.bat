@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d %~dp0

if not exist logs mkdir logs

set LOGFILE=logs\scenario_metrics.log
set CONFIG_FILE=config\scenario_metrics.json
for %%I in ("%~dp0.") do set "METRICS_PROJECT=%%~fI"
set "PYTHONPATH=%METRICS_PROJECT%\src"

:: =============================================================================
:: Prerequisites
::
:: The travel-model run does not automatically create every intermediate file
:: required by the TEP metrics. Before the Python metric package can run:
::
:: 1. RunCoreSummaries.bat must create the files under core_summaries.
::    R_HOME and R_LIB are borrowed from the scenario runtime unless explicitly
::    overridden. The scenario must contain the standard Core Summary scripts.
::
:: 2. export_highway_assignment_dbfs.job converts the five renamed loaded
::    highway networks to DBF and exports AM link geometry. The Python highway
::    preprocessor combines them with the shared RTPC boundaries to create the
::    GeoPackage used by the highway and school-area metrics.
::
:: 3. convert_trnlinks.job must extract SEQ from each transit-link DBF into
::    the matching *_converted.csv file. This requires CUBE's runtpp command
::    to be installed and available on PATH.
::
:: 4. sum_transit_times.job must combine transit trip and skim matrices into
::    metrics\transit_times_by_acc_mode_egr_taz.csv for Transit Waiting Time.
::
:: 5. export_nonmotorized_distances.job must export DIST, DISTWALK, and
::    DISTBIKE from skims\nonmotskm.tpp for the Active Transportation metric.
::    This also requires CUBE's runtpp command.
::
:: All prerequisite scripts must be run from the scenario directory because their input
:: and output paths are relative to the model run.
:: IMPORTANT: The packaged CUBE jobs currently target iteration 3. This runner
:: stops if the JSON requests a different iteration.
:: =============================================================================

for /f "usebackq delims=" %%I in (`uv run --directory "%METRICS_PROJECT%" --project "%METRICS_PROJECT%" --locked python -c "from tep_metrics.core.config import load_config; print(load_config(r'%CONFIG_FILE%')['_scenario_dir'])"`) do set "SCENARIO_DIR=%%I"
for /f "usebackq delims=" %%I in (`uv run --directory "%METRICS_PROJECT%" --project "%METRICS_PROJECT%" --locked python -c "from tep_metrics.core.config import load_config; print(load_config(r'%CONFIG_FILE%')['run']['iteration'])"`) do set "MODEL_ITERATION=%%I"

if not defined SCENARIO_DIR (
    echo ERROR: Could not resolve paths.scenario_dir from %CONFIG_FILE%.
    pause
    exit /b 1
)

if not exist "%SCENARIO_DIR%" (
    echo ERROR: Scenario directory does not exist: %SCENARIO_DIR%
    pause
    exit /b 1
)

:: =============================================================================
:: Runtime tools
::
:: Default: borrow R and CUBE locations from the selected scenario's
:: CTRAMP\runtime\SetPath.bat, just as RunModel.bat does. SetPath.bat also
:: changes PATH and activates Conda, so it is called temporarily: this runner
:: retains only R_HOME, R_LIB, and TPP_PATH, then restores its original PATH.
::
:: Optional machine-specific overrides (highest priority):
::   TEP_R_HOME   Full R installation directory
::   TEP_R_LIB    R package-library directory
::   TEP_TPP_PATH Semicolon-separated CUBE executable directories
::   TEP_RUNTPP   Full path to runtpp.exe or a compatible wrapper executable
:: =============================================================================

set "SCENARIO_SET_PATH=%SCENARIO_DIR%\CTRAMP\runtime\SetPath.bat"
if not exist "!SCENARIO_SET_PATH!" set "SCENARIO_SET_PATH=%~dp0..\..\model-files\runtime\SetPath.bat"

if not exist "!SCENARIO_SET_PATH!" goto runtime_borrow_complete
setlocal
call "!SCENARIO_SET_PATH!" >nul 2>&1
set "TEMP_R_HOME=!R_HOME!"
set "TEMP_R_LIB=!R_LIB!"
set "TEMP_TPP_PATH=!TPP_PATH!"
endlocal & set "BORROWED_R_HOME=%TEMP_R_HOME%" & set "BORROWED_R_LIB=%TEMP_R_LIB%" & set "BORROWED_TPP_PATH=%TEMP_TPP_PATH%"
:runtime_borrow_complete

if defined BORROWED_R_HOME set "R_HOME=!BORROWED_R_HOME!"
if defined BORROWED_R_LIB set "R_LIB=!BORROWED_R_LIB!"
if defined BORROWED_TPP_PATH set "TPP_PATH=!BORROWED_TPP_PATH!"

if defined TEP_R_HOME set "R_HOME=!TEP_R_HOME!"
if defined TEP_R_LIB set "R_LIB=!TEP_R_LIB!"
if defined TEP_TPP_PATH set "TPP_PATH=!TEP_TPP_PATH!"
if defined R_LIB set "R_LIBS_USER=!R_LIB!"

set "RUNTPP_EXE=runtpp"
if defined TEP_RUNTPP set "RUNTPP_EXE=!TEP_RUNTPP!"
if defined TPP_PATH set "PATH=!TPP_PATH!;!PATH!"

if /I not "%MODEL_ITERATION%"=="iter3" (
    echo ERROR: The prerequisite scripts currently support only iter3.
    echo Configured iteration: %MODEL_ITERATION%
    pause
    exit /b 1
)

uv run --directory "%METRICS_PROJECT%" --project "%METRICS_PROJECT%" --locked python preprocessing\check_inputs.py --config "%CONFIG_FILE%" --group core_summaries >nul 2>&1
if errorlevel 1 (set "CORE_READY=0") else (set "CORE_READY=1")
uv run --directory "%METRICS_PROJECT%" --project "%METRICS_PROJECT%" --locked python preprocessing\check_inputs.py --config "%CONFIG_FILE%" --group highway_exports >nul 2>&1
if errorlevel 1 (set "HIGHWAY_EXPORTS_READY=0") else (set "HIGHWAY_EXPORTS_READY=1")
uv run --directory "%METRICS_PROJECT%" --project "%METRICS_PROJECT%" --locked python preprocessing\check_inputs.py --config "%CONFIG_FILE%" --group highway_network >nul 2>&1
if errorlevel 1 (set "HIGHWAY_NETWORK_READY=0") else (set "HIGHWAY_NETWORK_READY=1")
uv run --directory "%METRICS_PROJECT%" --project "%METRICS_PROJECT%" --locked python preprocessing\check_inputs.py --config "%CONFIG_FILE%" --group transit_sequences >nul 2>&1
if errorlevel 1 (set "TRANSIT_SEQ_READY=0") else (set "TRANSIT_SEQ_READY=1")
uv run --directory "%METRICS_PROJECT%" --project "%METRICS_PROJECT%" --locked python preprocessing\check_inputs.py --config "%CONFIG_FILE%" --group transit_waiting >nul 2>&1
if errorlevel 1 (set "TRANSIT_WAIT_READY=0") else (set "TRANSIT_WAIT_READY=1")
uv run --directory "%METRICS_PROJECT%" --project "%METRICS_PROJECT%" --locked python preprocessing\check_inputs.py --config "%CONFIG_FILE%" --group nonmotorized >nul 2>&1
if errorlevel 1 (set "NONMOT_READY=0") else (set "NONMOT_READY=1")

if "%CORE_READY%"=="0" (
    if not defined R_HOME (
        echo ERROR: R_HOME must be set to generate missing Core Summaries.
        pause
        exit /b 1
    )
    if not exist "%R_HOME%\bin\x64\Rscript.exe" (
        echo ERROR: Rscript was not found under R_HOME: %R_HOME%
        pause
        exit /b 1
    )
    echo Using R_HOME: %R_HOME%
    echo Using R_LIB:  %R_LIB%
)

set "NEED_CUBE=0"
if "%HIGHWAY_EXPORTS_READY%"=="0" set "NEED_CUBE=1"
if "%TRANSIT_SEQ_READY%"=="0" set "NEED_CUBE=1"
if "%TRANSIT_WAIT_READY%"=="0" set "NEED_CUBE=1"
if "%NONMOT_READY%"=="0" set "NEED_CUBE=1"

if "%NEED_CUBE%"=="1" (
    where "%RUNTPP_EXE%" >nul 2>&1
    if errorlevel 1 (
        if not exist "%RUNTPP_EXE%" (
            echo ERROR: Some preprocessing outputs are missing and CUBE runtpp was not found.
            echo Runner: %RUNTPP_EXE%
            pause
            exit /b 1
        )
    )
    echo Using CUBE runner: %RUNTPP_EXE%
)

for %%I in ("%~dp0..\..\model-files\RunCoreSummaries.bat") do set "CORE_SUMMARIES_BAT=%%~fI"
for %%I in ("%~dp0preprocessing\cube\export_highway_assignment_dbfs.job") do set "EXPORT_HIGHWAY_JOB=%%~fI"
for %%I in ("%~dp0preprocessing\cube\convert_trnlinks.job") do set "CONVERT_TRNLINKS_JOB=%%~fI"
for %%I in ("%~dp0preprocessing\cube\sum_transit_times.job") do set "SUM_TRANSIT_TIMES_JOB=%%~fI"
for %%I in ("%~dp0preprocessing\cube\export_nonmotorized_distances.job") do set "EXPORT_NONMOT_JOB=%%~fI"

if not exist "%CORE_SUMMARIES_BAT%" (
    echo ERROR: Core Summaries runner not found: %CORE_SUMMARIES_BAT%
    pause
    exit /b 1
)

if not exist "%EXPORT_HIGHWAY_JOB%" (
    echo ERROR: Highway DBF export job not found: %EXPORT_HIGHWAY_JOB%
    pause
    exit /b 1
)

if not exist "%CONVERT_TRNLINKS_JOB%" (
    echo ERROR: Transit conversion job not found: %CONVERT_TRNLINKS_JOB%
    pause
    exit /b 1
)

if not exist "%SUM_TRANSIT_TIMES_JOB%" (
    echo ERROR: Transit-time summary job not found: %SUM_TRANSIT_TIMES_JOB%
    pause
    exit /b 1
)

if not exist "%EXPORT_NONMOT_JOB%" (
    echo ERROR: Nonmotorized-distance export job not found: %EXPORT_NONMOT_JOB%
    pause
    exit /b 1
)

echo =====================================
echo Preparing Scenario Metric Inputs
echo =====================================
echo Scenario directory: %SCENARIO_DIR%
echo.

call :capture_time WORKFLOW_START

pushd "%SCENARIO_DIR%"

echo [1/7] Running Core Summaries...
call :capture_time STEP_START
if "%CORE_READY%"=="1" (
    echo Reusing existing Core Summary metric inputs.
) else (
    call "%CORE_SUMMARIES_BAT%"
    if errorlevel 1 (
        echo.
        echo ERROR: Core Summaries failed.
        popd
        pause
        exit /b 1
    )
)
call :report_elapsed STEP_START "Step 1 elapsed"

echo.
echo [2/7] Exporting highway assignment DBFs and geometry with CUBE...
call :capture_time STEP_START
if "%HIGHWAY_EXPORTS_READY%"=="1" (
    echo Reusing existing highway DBFs and geometry shapefile.
) else (
    if not exist "GIS_data" mkdir "GIS_data"
    "%RUNTPP_EXE%" "%EXPORT_HIGHWAY_JOB%"
    if errorlevel 1 (
        echo.
        echo ERROR: Highway assignment DBF export failed.
        popd
        pause
        exit /b 1
    )
)
call :report_elapsed STEP_START "Step 2 elapsed"

echo.
echo [3/7] Building the five-period RTPC highway GeoPackage...
call :capture_time STEP_START
if "%HIGHWAY_NETWORK_READY%"=="1" (
    echo Reusing existing RTPC highway GeoPackage.
) else (
    popd
    uv run --directory "%METRICS_PROJECT%" --project "%METRICS_PROJECT%" --locked python preprocessing\build_highway_network.py --config "%CONFIG_FILE%"
    if errorlevel 1 (
        echo.
        echo ERROR: RTPC highway GeoPackage preprocessing failed.
        pause
        exit /b 1
    )
    pushd "%SCENARIO_DIR%"
)
call :report_elapsed STEP_START "Step 3 elapsed"

echo.
echo [4/7] Creating transit SEQ conversion files with CUBE...
call :capture_time STEP_START
if "%TRANSIT_SEQ_READY%"=="1" (
    echo Reusing existing transit sequence CSVs.
) else (
    "%RUNTPP_EXE%" "%CONVERT_TRNLINKS_JOB%"
    if errorlevel 1 (
        echo.
        echo ERROR: Transit-link conversion failed.
        popd
        pause
        exit /b 1
    )
)
call :report_elapsed STEP_START "Step 4 elapsed"

echo.
echo [5/7] Summarizing transit waiting times with CUBE...
call :capture_time STEP_START
if "%TRANSIT_WAIT_READY%"=="1" (
    echo Reusing existing transit waiting-time CSV.
) else (
    if not exist metrics mkdir metrics
    del /q "metrics\transit_times_by_acc_mode_egr_taz*.csv" >nul 2>&1
    "%RUNTPP_EXE%" "%SUM_TRANSIT_TIMES_JOB%"
    if errorlevel 1 (
        echo.
        echo ERROR: Transit-time summary failed.
        popd
        pause
        exit /b 1
    )
    if not exist "metrics\transit_times_by_acc_mode_egr_taz.csv" (
        echo ERROR: CUBE completed without creating the transit waiting-time input.
        popd
        pause
        exit /b 1
    )
)
call :report_elapsed STEP_START "Step 5 elapsed"

echo.
echo [6/7] Exporting nonmotorized distance skims with CUBE...
call :capture_time STEP_START
if "%NONMOT_READY%"=="1" (
    echo Reusing existing nonmotorized-distance CSV.
) else (
    if not exist "skims\nonmotskm.tpp" (
        echo ERROR: Required nonmotorized skim does not exist:
        echo        %SCENARIO_DIR%\skims\nonmotskm.tpp
        popd
        pause
        exit /b 1
    )
    if not exist database mkdir database
    "%RUNTPP_EXE%" "%EXPORT_NONMOT_JOB%"
    if errorlevel 1 (
        echo.
        echo ERROR: Nonmotorized-distance export failed.
        popd
        pause
        exit /b 1
    )
    if not exist "database\nonmotorized_distances.csv" (
        echo ERROR: CUBE completed without creating database\nonmotorized_distances.csv.
        popd
        pause
        exit /b 1
    )
)
call :report_elapsed STEP_START "Step 6 elapsed"

popd

echo.
echo [7/7] Running Scenario Metrics...
call :capture_time STEP_START
uv run --directory "%METRICS_PROJECT%" --project "%METRICS_PROJECT%" --locked python -m tep_metrics --config "%CONFIG_FILE%"


if errorlevel 1 (
    echo.
    echo Metrics failed.
    pause
    exit /b 1
)
call :report_elapsed STEP_START "Step 7 elapsed"

echo.
echo Metrics completed successfully.
call :report_elapsed WORKFLOW_START "Total workflow elapsed"
pause
endlocal
exit /b 0

:: Store the current local time as centiseconds since midnight. Using a numeric
:: value avoids locale-specific date parsing and works with standard cmd.exe.
:capture_time
set "TIMER_NOW=%TIME: =0%"
set /a "TIMER_VALUE=(1%TIMER_NOW:~0,2%-100)*360000 + (1%TIMER_NOW:~3,2%-100)*6000 + (1%TIMER_NOW:~6,2%-100)*100 + (1%TIMER_NOW:~9,2%-100)"
set "%~1=%TIMER_VALUE%"
exit /b 0

:: Print elapsed time as HH:MM:SS.cc. The midnight adjustment keeps a step
:: accurate if it starts before midnight and finishes the following day.
:report_elapsed
call :capture_time TIMER_END
set /a "TIMER_ELAPSED=TIMER_END-!%~1!"
if !TIMER_ELAPSED! lss 0 set /a "TIMER_ELAPSED+=8640000"
set /a "TIMER_HOURS=TIMER_ELAPSED/360000, TIMER_REMAINDER=TIMER_ELAPSED%%360000, TIMER_MINUTES=TIMER_REMAINDER/6000, TIMER_REMAINDER%%=6000, TIMER_SECONDS=TIMER_REMAINDER/100, TIMER_CENTISECONDS=TIMER_REMAINDER%%100"
set "TIMER_HOURS=0!TIMER_HOURS!"
set "TIMER_MINUTES=0!TIMER_MINUTES!"
set "TIMER_SECONDS=0!TIMER_SECONDS!"
set "TIMER_CENTISECONDS=0!TIMER_CENTISECONDS!"
echo %~2: !TIMER_HOURS:~-2!:!TIMER_MINUTES:~-2!:!TIMER_SECONDS:~-2!.!TIMER_CENTISECONDS:~-2!
exit /b 0

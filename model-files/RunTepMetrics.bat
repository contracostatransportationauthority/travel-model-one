@echo off
setlocal EnableExtensions

:: =============================================================================
:: Scenario-root launcher for the CCTA TEP metrics.
::
:: During scenario setup, copy this file from CTRAMP\model-files to the scenario
:: root alongside RunModel.bat. Its location then defines the scenario directory:
::
::   <scenario>\RunTepMetrics.bat
::   <scenario>\CTRAMP\utilities\tep\runMetrics.bat
:: =============================================================================

for %%I in ("%~dp0.") do set "TEP_SCENARIO_DIR=%%~fI"
set "TEP_PROJECT=%TEP_SCENARIO_DIR%\CTRAMP\utilities\tep"
set "TEP_RUNNER=%TEP_PROJECT%\runMetrics.bat"

if not exist "%TEP_RUNNER%" (
    echo ERROR: The packaged TEP metrics runner was not found:
    echo        %TEP_RUNNER%
    echo.
    echo RunTepMetrics.bat must be located in the scenario root, with the
    echo repository installed under the scenario's CTRAMP folder.
    pause
    exit /b 1
)

echo TEP scenario directory: %TEP_SCENARIO_DIR%
call "%TEP_RUNNER%"
set "TEP_EXIT_CODE=%ERRORLEVEL%"

endlocal & exit /b %TEP_EXIT_CODE%

:: ------------------------------------------------------------------------------------------------------
::
:: Step 1:  Specify file locations
::
:: ------------------------------------------------------------------------------------------------------

:: All TEP scenarios are year 2050
set YEAR=2050
:: set the location of the model run folder on D; this is where the input and output directories will be copied to
set RUN_DIR=D:\Scenarios\%YEAR%_BaseY_BCM%YEAR%

:: Should strategies be included? AddStrategies=Yes for Project runs; AddStrategies=No for NoProject runs.
:: Not clear this is actually used. Will probably comment this out; TEP includes some strategies but not others.
set AddStrategies=Yes

:: set the location of the Travel Model Release
:: use master for now until we create a release
set GITHUB_DIR=C:\Model_BCM\Model_Files\AlaCC_Model_TEP_branch\travel-model-one
:: some inputs come from off-the-shelf model
set BCM_INPUTS_SHELF=C:\Model_BCM\Model_Files\Alacc_Inputs
:: For TEP-specific inputs that don't vary by scenario
set BCM_INPUTS_TEP=D:\TEP_COMMON_INPUTS
set Software_Dir=C:\Model_BCM\Model_Files\AlaCC_Software
:: HIGH or MED
set COMPUTER_SETTING=HIGH


::Inputs for the nonres models
set INPUT_NONRES=%BCM_INPUTS_SHELF%\nonres



:: set the location of the overrides directory (for Blueprint strategies)
:: set BP_OVERRIDE_DIR=D:\Projects\BCM\2015_BaseY_BCM2015\travel-model-overrides

:: ------------------------------------------------------------------------------------------------------
::
:: Step 2:  Set up folder structure and copy CTRAMP
::
:: ------------------------------------------------------------------------------------------------------

for /f "delims=[] tokens=2" %%a in ('ping -4 -n 1 %ComputerName% ^| findstr [') do set HOST_IP_ADDRESS=%%a
SET HOST_IP_ADDRESS=localhost
echo HOST_IP_ADDRESS: %HOST_IP_ADDRESS%

SET computer_prefix=%computername:~0,4%
mkdir %RUN_DIR%
echo SET SOFTWARE_DIR=%Software_Dir%> %RUN_DIR%\Set_Software_Dr.cmd
echo SET COMPUTER_SETTING=%COMPUTER_SETTING%>> %RUN_DIR%\Set_Software_Dr.cmd
COMPUTER_SETTING
cd /d %RUN_DIR%
:: copy over CTRAMP
mkdir CTRAMP\model
::mkdir Software
mkdir CTRAMP\runtime
mkdir CTRAMP\scripts
mkdir CTRAMP\scripts\metrics
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\model"       CTRAMP\model
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\runtime"     CTRAMP\runtime
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\model-files\scripts"     CTRAMP\scripts
c:\windows\system32\Robocopy.exe /E "%GITHUB_DIR%\utilities\RTP\metrics"   CTRAMP\scripts\metrics
::c:\windows\system32\Robocopy.exe /E "%Software_Dir%"       				   Software
copy /Y "%GITHUB_DIR%\utilities\monitoring\notify_slack.py"                CTRAMP\scripts
copy /Y "%GITHUB_DIR%\model-files\RunIteration.bat"                        CTRAMP
copy /Y "%GITHUB_DIR%\model-files\RunModel.bat"                            .
copy /Y "%GITHUB_DIR%\model-files\click_to_runmodel.bat"                   .
copy /Y "%GITHUB_DIR%\model-files\RunPostProcess.bat"                      .
copy /Y "%GITHUB_DIR%\model-files\RunLogsums.bat"                          .
copy /Y "%GITHUB_DIR%\model-files\RunCoreSummaries.bat"                    .
copy /Y "%GITHUB_DIR%\model-files\RunPrepareEmfac.bat"                     .
copy /Y "%GITHUB_DIR%\utilities\RTP\RunMetrics.bat"                        .
copy /Y "%GITHUB_DIR%\utilities\RTP\RunScenarioMetrics.bat"                .
copy /Y "%GITHUB_DIR%\utilities\RTP\ExtractKeyFiles.bat"                   .
copy /Y "%GITHUB_DIR%\utilities\RTP\QAQC\Run_QAQC.bat"                     .
copy /Y "%GITHUB_DIR%\utilities\check-setupmodel\Check_SetupModelLog.py"   .
copy /Y "%GITHUB_DIR%\utilities\dbf_to_csv\create_landuse_csv.R"   		   CTRAMP\scripts\preprocess

:: we're not using slack
::if "%COMPUTER_PREFIX%" == "WIN-" (copy "%GITHUB_DIR%\utilities\monitoring\notify_slack.py"  "CTRAMP\scripts\notify_slack.py")
::if "%COMPUTER_PREFIX%" == "WIN-"    set HOST_IP_ADDRESS=10.0.0.59

:: ------------------------------------------------------------------------------------------------------
::
:: Step 3: Copy inputs common to all TEP scenarios
::
:: ------------------------------------------------------------------------------------------------------

:: popsyn and land use
mkdir popsyn
mkdir INPUT\popsyn
mkdir INPUT\landuse
copy "%BCM_INPUTS_SHELF%\nonres\IZ_OZ_PCT_EXT.dat"          	INPUT\landuse\IZ_OZ_PCT_EXT.dat
copy "%BCM_INPUTS_SHELF%\nonres\SD2TAZ_KF.prn"          		INPUT\landuse\SD2TAZ_KF.prn
copy "%BCM_INPUTS_SHELF%\nonres\TAZ2CO.prn"          			INPUT\landuse\TAZ2CO.prn
copy "%BCM_INPUTS_SHELF%\nonres\TAZ2COUNTY.prn"          		INPUT\landuse\TAZ2COUNTY.prn
copy "%BCM_INPUTS_SHELF%\nonres\TAZ2SD.prn"          			INPUT\landuse\TAZ2SD.prn
copy "%BCM_INPUTS_SHELF%\nonres\walkAccessBuffers.float.csv"    INPUT\landuse\walkAccessBuffers.float.csv
copy "%BCM_INPUTS_SHELF%\inputs_%YEAR%\ZMAST.dbf"          			INPUT\landuse\ZMAST.dbf


copy %BCM_INPUTS_SHELF%\inputs_%YEAR%\hhFile%YEAR%.csv												INPUT\popsyn\hhFile.%YEAR%.csv
copy %BCM_INPUTS_SHELF%\inputs_%YEAR%\personFile%YEAR%.csv											INPUT\popsyn\personFile.%YEAR%.csv
c:\windows\system32\Robocopy.exe /E "%INPUT_NONRES%"                   							INPUT\nonres

mkdir INPUT\metrics
copy /Y "%BCM_INPUTS_SHELF%\metrics\*.*"                                                     		INPUT\metrics

set PREV_RUN_DIR=%BCM_INPUTS_SHELF%\inputs_%YEAR%\warmstart


:: mkdir skims
:: warmstart (copy from the previous run)
mkdir INPUT\warmstart\main
mkdir INPUT\warmstart\nonres
copy /Y "%PREV_RUN_DIR%\main\*.tpp"                                                       		INPUT\warmstart\main
copy /Y "%PREV_RUN_DIR%\nonres\*.tpp"                                                     		INPUT\warmstart\nonres


:: Transit network properties that are not scenario-specific
:mkdir INPUT\trn
c:\windows\system32\Robocopy.exe /E "%BCM_INPUTS_SHELF%\trn"                                     		INPUT\trn

:: ------------------------------------------------------------------------------------------------------
::
:: Step 4: Copy TEP-specific inputs that apply to all TEP scenarios
::
:: ------------------------------------------------------------------------------------------------------

:: the properties file (TEP-specific: omits MTC complete streets policy)
set PARAMS=%GITHUB_DIR%\config\params_TEP_%YEAR%.properties
copy /Y "%PARAMS%"                                                                               INPUT\params.properties

:: the telecommute constants (TEP-specific: omits MTC TDM policy)
copy /Y "%BCM_INPUTS_TEP%telecommute_constants_TEP_%YEAR%.csv" "INPUT/landuse/telecommute_constants.csv"
copy /Y "%BCM_INPUTS_SHELF%\inputs_%YEAR%\telecommute_max_rate_county.csv" "INPUT/landuse/telecommute_max_rate_county.csv"

:: the toll file
mkdir INPUT\hwy
copy "%BCM_INPUTS_TEP\tolls.csv"                                        	INPUT\hwy\tolls.csv

:: ------------------------------------------------------------------------------------------------------
::
:: Step 5: Copy scenario-specific inputs
:: 
:: ------------------------------------------------------------------------------------------------------

set SCENARIO_INPUTS=D:\network_building\ccta_tep_baseline\data\scenario_files\model_networks\2050

:: highway network
copy "%SCENARIO_INPUTS\hwy\complete_network_with_externals.net"     INPUT\hwy\complete_network_with_externals.net


:: scenario-specific parts of transit network
copy "%SCENARIO_INPUTS%\trn\transit.lin"                                        	INPUT\trn\transit.lin
copy "%SCENARIO_INPUTS%\trn\vehtype.pts"                                        	INPUT\trn\vehtype.pts

:: Mobility hub assumptions
:: For baseline, don't need to change anything. For some scenarios will need to rename eg
:: seemless_xfers_2035_and_beyond.block = seemless_xfers_all.block
:end
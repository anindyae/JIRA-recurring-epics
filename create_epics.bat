@echo off
REM ============================================
REM JIRA Recurring Epic Creator
REM ============================================

cd /d "%~dp0"

REM Check if no arguments provided (double-clicked) - show interactive menu
if "%~1"=="" (
    :menu
    cls
    echo.
    echo =============================================
    echo   JIRA Recurring Epic Creator
    echo =============================================
    echo.
    echo   [1] Create CC Gantt epics for current month
    echo   [2] List available templates
    echo   [3] Test JIRA connection
    echo   [4] Exit
    echo.
    echo =============================================
    set /p choice="Select an option (1-4): "
    
    if "%choice%"=="1" goto :create_epics
    if "%choice%"=="2" goto :list_templates
    if "%choice%"=="3" goto :test_connection
    if "%choice%"=="4" exit /b 0
    
    echo Invalid choice. Please try again.
    timeout /t 2 > nul
    goto :menu
)

REM Check if virtual environment exists
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe jira_epic_creator.py %*
) else (
    python jira_epic_creator.py %*
)
goto :end

:create_epics
echo.
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe jira_epic_creator.py create -t cc-gantt-meetings -t cc-gantt-test-setup -t cc-gantt-qa-tasks -t cc-gantt-automation-tasks
) else (
    python jira_epic_creator.py create -t cc-gantt-meetings -t cc-gantt-test-setup -t cc-gantt-qa-tasks -t cc-gantt-automation-tasks
)
goto :end

:list_templates
echo.
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe jira_epic_creator.py list-templates
) else (
    python jira_epic_creator.py list-templates
)
goto :end

:test_connection
echo.
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe jira_epic_creator.py test-connection
) else (
    python jira_epic_creator.py test-connection
)
goto :end

:end
REM Always keep window open until user presses a key
echo.
echo =============================================
echo Press any key to close this window...
echo =============================================
pause > nul

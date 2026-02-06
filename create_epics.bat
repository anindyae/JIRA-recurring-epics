@echo off
REM ============================================
REM JIRA Recurring Epic Creator
REM ============================================
REM Usage:
REM   create_epics.bat                     - Show help
REM   create_epics.bat create              - Create CC Gantt epics for current month
REM   create_epics.bat --dry-run create    - Preview without creating
REM   create_epics.bat create --month 3    - Create for March
REM   create_epics.bat list-templates      - Show available templates
REM   create_epics.bat test-connection     - Test JIRA connection
REM ============================================

cd /d "%~dp0"

REM Check if no arguments provided (double-clicked)
if "%~1"=="" (
    echo.
    echo =============================================
    echo   JIRA Recurring Epic Creator
    echo =============================================
    echo.
    echo Usage:
    echo   create_epics.bat create -t cc-gantt-meetings -t cc-gantt-test-setup -t cc-gantt-qa-tasks -t cc-gantt-automation-tasks
    echo.
    echo Commands:
    echo   create              Create epics for current month
    echo   list-templates      Show available templates
    echo   test-connection     Test JIRA connection
    echo   preview [template]  Preview a template
    echo.
    echo Options:
    echo   --dry-run           Preview without creating
    echo   -t [template]       Specify template ^(can use multiple^)
    echo   --month [1-12]      Specify month
    echo   --year [YYYY]       Specify year
    echo   -y                  Skip confirmation prompts
    echo.
    pause
    exit /b 0
)

REM Check if virtual environment exists
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe jira_epic_creator.py %*
) else (
    python jira_epic_creator.py %*
)

REM Keep window open if double-clicked (check if running in interactive mode)
echo.
if /i "%CMDCMDLINE:"=%" == "%COMSPEC% " (
    pause
)

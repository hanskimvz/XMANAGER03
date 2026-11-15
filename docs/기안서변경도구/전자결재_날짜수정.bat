@echo off
REM ============================================================
REM  Approval Date Editor - launcher (standalone)
REM
REM  Requires Python with SQLAlchemy + psycopg2.
REM  The backend .venv already has them - keep PY pointed at it.
REM  If you move PCs/paths, edit the PY line below.
REM  Target DB is chosen by APP_ENV (development / production),
REM  connection details come from db_config.ini.
REM ============================================================

set "PY=H:\Electronic Approval System\X-MANAGER_R0.1 (2)\X-MANAGER_R0.1\backend\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

set APP_ENV=development

cd /d "%~dp0"
"%PY%" edit_approval_dates_gui.py

if errorlevel 1 pause

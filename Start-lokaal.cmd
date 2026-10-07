@echo off
setlocal
cd /d "%~dp0"
set "TASK_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%TASK_PYTHON%" set "TASK_PYTHON=python"
if not exist ".venv\Scripts\python.exe" (
  "%TASK_PYTHON%" -m venv .venv
  if errorlevel 1 goto failed
)
if not exist ".venv\ready.txt" (
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto failed
  echo installed>.venv\ready.txt
)
echo Open http://127.0.0.1:8766/ in je browser.
echo Houd dit venster open zolang je de applicatie gebruikt.
.venv\Scripts\python.exe app.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Starten is niet gelukt. Controleer de melding hierboven.
echo Als de pagina al werkt, hoef je geen tweede server te starten.
pause
exit /b 1

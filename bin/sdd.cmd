@echo off
setlocal
set "SDD_KIT_ROOT=%~dp0.."
if defined PYTHONPATH (
  set "PYTHONPATH=%SDD_KIT_ROOT%;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%SDD_KIT_ROOT%"
)
where python >nul 2>nul
if errorlevel 1 goto usepy
python -m sdd %*
exit /b %ERRORLEVEL%
:usepy
py -3 -m sdd %*
exit /b %ERRORLEVEL%

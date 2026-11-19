@echo off
chcp 65001 >nul
setlocal
set "PY="
if exist "%USERPROFILE%\anaconda3\python.exe" set "PY=%USERPROFILE%\anaconda3\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\anaconda3\python.exe" set "PY=%LOCALAPPDATA%\anaconda3\python.exe"
if not defined PY if exist "C:\ProgramData\anaconda3\python.exe" set "PY=C:\ProgramData\anaconda3\python.exe"
if not defined PY if exist "%USERPROFILE%\miniconda3\python.exe" set "PY=%USERPROFILE%\miniconda3\python.exe"
if not defined PY for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PY="%%D\python.exe""
if not defined PY (py -3 -c "import sys" >nul 2>nul && set "PY=py -3")
if not defined PY (python -c "import sys" >nul 2>nul && set "PY=python")
if not defined PY (
  echo Python was not found.
  echo Install "Python 3.12" from Microsoft Store, then run this again.
  pause
  exit /b 1
)
set PYTHONIOENCODING=utf-8
%PY% "%~dp0_tools\rename_pdfs.py" %*
echo.
pause

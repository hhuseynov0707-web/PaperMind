@echo off
REM ===========================================================================
REM  PaperMind — yedeyi cek ve berpani sina.
REM
REM  Qosa klikle ise dusur. cmd/PowerShell-den de isledile biler.
REM
REM  Niye .bat lazim oldu:
REM    Git PATH-de deyil, ona gore cmd-de `bash` tapilmir. PATH-i deyismek
REM    de olardi, amma bu fayl hec ne deyismir — bash.exe-ni ozu tapir.
REM ===========================================================================
setlocal

cd /d "%~dp0"

set "BASH="
for %%P in (
  "%ProgramFiles%\Git\bin\bash.exe"
  "%ProgramFiles(x86)%\Git\bin\bash.exe"
  "%LocalAppData%\Programs\Git\bin\bash.exe"
) do if not defined BASH if exist %%P set "BASH=%%~P"

if not defined BASH (
  echo.
  echo   XETA: bash.exe tapilmadi.
  echo   Git for Windows qurulubmu?  https://git-scm.com/download/win
  echo.
  pause
  exit /b 1
)

echo.
echo   ===  1/2  Kenar surət cekilir  ===
echo.
"%BASH%" scripts/backup-pull.sh
if errorlevel 1 (
  echo.
  echo   Cekilis alinmadi — berpa sinagi atlanir.
  pause
  exit /b 1
)

echo.
echo   ===  2/2  Berpa sinanir  ===
echo.
"%BASH%" scripts/restore-test.sh

echo.
echo   Bitdi. Pencereni baglaya bilersen.
pause

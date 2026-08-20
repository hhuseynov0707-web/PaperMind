@echo off
REM ===========================================================================
REM  n8n interfeysini ac.
REM
REM  Qosa klikle ise dusur.
REM
REM  n8n internete ACIQ DEYIL (127.0.0.1:5678) - qesdendir. Ora catmaq ucun
REM  SSH tuneli qurulur: serverin 5678 portu bu kompyuterde 15678 olur.
REM
REM  Pencereni ACIQ saxla. Baglayanda tunel de baglanir.
REM  Port 5679 ISLEMIR - Codespaces onu tutub, ona gore 15678 isledilir.
REM ===========================================================================
setlocal

set "SSH=C:\Windows\System32\OpenSSH\ssh.exe"
if not exist "%SSH%" set "SSH=%ProgramFiles%\Git\usr\bin\ssh.exe"
if not exist "%SSH%" (
  echo.
  echo   XETA: ssh.exe tapilmadi.
  echo.
  pause
  exit /b 1
)

set "KEY=%USERPROFILE%\.ssh\papermind"
if not exist "%KEY%" (
  echo.
  echo   XETA: acar tapilmadi: %KEY%
  echo.
  pause
  exit /b 1
)

echo.
echo   Tunel qurulur...
echo.
echo   Hazir olanda brauzerde ac:   http://localhost:15678
echo.
echo   Bu pencereni ACIQ saxla. Baglamaq ucun Ctrl+C.
echo.

start "" http://localhost:15678
"%SSH%" -i "%KEY%" -L 15678:localhost:5678 root@2.28.22.89

echo.
echo   Tunel baglandi.
pause

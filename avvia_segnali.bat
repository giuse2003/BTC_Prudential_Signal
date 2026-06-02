@echo off
setlocal

REM Avvia l'app Python e apre automaticamente report + grafico.
REM Esecuzione: doppio click su questo file.

cd /d "%~dp0"

REM Preferiamo il launcher "py" se presente (più affidabile su Windows).
where py >nul 2>nul
if %errorlevel%==0 (
  py -3.13 main.py --open
  goto :done
)

REM Fallback su "python" nel PATH.
where python >nul 2>nul
if %errorlevel%==0 (
  python main.py --open
  goto :done
)

echo.
echo ERRORE: non trovo Python (ne' "py" ne' "python") nel PATH.
echo - Installa Python 3.13 e assicurati di spuntare "Add Python to PATH".
echo - Oppure esegui da PowerShell: python main.py --open
echo.

:done
echo.
echo Premi un tasto per chiudere...
pause >nul


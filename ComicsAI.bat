@echo off
setlocal EnableDelayedExpansion
title Comics AI Studio - Local Control Panel
color 0B

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "ENV_FILE=%PROJECT_DIR%\.env"
set "PORT=8000"

:MAIN_MENU
cls
call :LOAD_ENV
call :CHECK_STATUS

echo.
echo  ============================================================
echo              Comics AI Studio - Local Control Panel
echo  ============================================================
echo.
echo   Local App URL   : http://127.0.0.1:%PORT%
if not "!LAN_IP!"=="" (
    echo   Home Wi-Fi URL  : http://!LAN_IP!:%PORT%
    echo   Tachiyomi / LRR : http://!LAN_IP!:%PORT%
    echo   OPDS Catalog    : http://!LAN_IP!:%PORT%/opds
)
if "!APP_UP!"=="1" (
    echo   App Status      : [RUNNING] on port %PORT%
) else (
    echo   App Status      : [STOPPED]
)
echo.
echo   Compute Endpoints (.env):
echo   ------------------------------------------------------------
echo   LLM URL         : !LLM_BASE_URL!
echo   LLM Model       : !LLM_MODEL!
if "!LLM_UP!"=="1" (
    echo   LLM Status      : [ONLINE]
) else (
    echo   LLM Status      : [OFFLINE / UNREACHABLE]
)
echo   ComfyUI URL     : !COMFYUI_BASE_URL!
if "!COMFY_UP!"=="1" (
    echo   ComfyUI Status  : [ONLINE]
) else (
    echo   ComfyUI Status  : [OFFLINE / UNREACHABLE]
)
echo  ============================================================
echo.
echo   [1] Start App (Local + Home Wi-Fi for Tachiyomi) + Browser
echo   [2] Start App (This PC Only - 127.0.0.1) + Browser
echo   [3] Stop Local App
echo   [4] Configure LLM & ComfyUI Endpoints (Local / Remote)
echo   [5] Test Connections (LLM & ComfyUI)
echo   [6] Open Local UI in Browser (http://127.0.0.1:%PORT%)
echo   [7] Refresh Status
echo   [0] Exit
echo.
set "CHOICE="
set /p "CHOICE=  Choose an option [0-7]: "

if "%CHOICE%"=="1" goto START_LAN
if "%CHOICE%"=="2" goto START_LOCAL
if "%CHOICE%"=="3" goto STOP_APP
if "%CHOICE%"=="4" goto CONFIG_ENDPOINTS
if "%CHOICE%"=="5" goto TEST_CONNECTIONS
if "%CHOICE%"=="6" goto OPEN_BROWSER
if "%CHOICE%"=="7" goto MAIN_MENU
if "%CHOICE%"=="0" goto EXIT_APP

echo.
echo  [!] Invalid option.
timeout /t 1 /nobreak >nul
goto MAIN_MENU

:LOAD_ENV
set "LLM_BASE_URL=http://127.0.0.1:11434/v1"
set "LLM_MODEL=gemma3n:e4b"
set "LLM_API_KEY=local"
set "COMFYUI_BASE_URL=http://127.0.0.1:8188"
if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
        set "K=%%A"
        set "V=%%B"
        if "!K!"=="LLM_BASE_URL" set "LLM_BASE_URL=!V!"
        if "!K!"=="LLM_MODEL" set "LLM_MODEL=!V!"
        if "!K!"=="LLM_API_KEY" set "LLM_API_KEY=!V!"
        if "!K!"=="COMFYUI_BASE_URL" set "COMFYUI_BASE_URL=!V!"
    )
)
exit /b 0

:CHECK_STATUS
set "APP_UP=0"
set "LLM_UP=0"
set "COMFY_UP=0"
set "LAN_IP="

netstat -ano 2>nul | findstr /C:":%PORT% " | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL%==0 set "APP_UP=1"

for /f %%I in ('powershell -NoProfile -Command "$ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.InterfaceAlias -notmatch 'Loopback|vEthernet|WSL' -and $_.IPAddress -notmatch '^169\.254\.' } | Select-Object -First 1 -ExpandProperty IPAddress; if ($ip) { $ip }"') do set "LAN_IP=%%I"
for /f %%R in ('powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri ('!LLM_BASE_URL!/models') -TimeoutSec 2 -UseBasicParsing; if ($r.StatusCode -lt 500) { '1' } else { '0' } } catch { '0' }"') do set "LLM_UP=%%R"
for /f %%R in ('powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri ('!COMFYUI_BASE_URL!/system_stats') -TimeoutSec 2 -UseBasicParsing; if ($r.StatusCode -lt 500) { '1' } else { '0' } } catch { '0' }"') do set "COMFY_UP=%%R"
exit /b 0

:START_LAN
set "BIND_HOST=0.0.0.0"
goto DO_START

:START_LOCAL
set "BIND_HOST=127.0.0.1"
goto DO_START

:DO_START
echo.
if "!APP_UP!"=="1" (
    echo  [*] App is already running on port %PORT%. Opening browser...
    start "" "http://127.0.0.1:%PORT%"
    timeout /t 2 /nobreak >nul
    goto MAIN_MENU
)
echo  Starting Comics AI Studio on %BIND_HOST%:%PORT% ...
pushd "%PROJECT_DIR%"
start "Comics AI Studio - Server" cmd /k "title Comics AI Studio - Server && python -m uvicorn app.main:app --host %BIND_HOST% --port %PORT%"
popd
echo  Waiting for server to initialize...
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:%PORT%"
echo  [OK] Started!
timeout /t 2 /nobreak >nul
goto MAIN_MENU

:STOP_APP
echo.
echo  Stopping Comics AI Studio on port %PORT%...
set "KILLED=0"
for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr /C:":%PORT% " ^| findstr "LISTENING"') do (
    taskkill /PID %%P /F >nul 2>&1
    set "KILLED=1"
)
if "!KILLED!"=="1" (
    echo  [OK] Server stopped.
) else (
    echo  [*] Server was not running.
)
timeout /t 2 /nobreak >nul
goto MAIN_MENU

:CONFIG_ENDPOINTS
cls
call :LOAD_ENV
echo.
echo  ============================================================
echo       Configure Compute Endpoints (Leave empty to keep)
echo  ============================================================
echo.
echo   Current LLM_BASE_URL     : !LLM_BASE_URL!
set "NEW_LLM_URL="
set /p "NEW_LLM_URL=  New LLM_BASE_URL         : "
if not "!NEW_LLM_URL!"=="" set "LLM_BASE_URL=!NEW_LLM_URL!"

echo.
echo   Current LLM_MODEL        : !LLM_MODEL!
set "NEW_LLM_MODEL="
set /p "NEW_LLM_MODEL=  New LLM_MODEL            : "
if not "!NEW_LLM_MODEL!"=="" set "LLM_MODEL=!NEW_LLM_MODEL!"

echo.
echo   Current LLM_API_KEY      : !LLM_API_KEY!
set "NEW_LLM_KEY="
set /p "NEW_LLM_KEY=  New LLM_API_KEY          : "
if not "!NEW_LLM_KEY!"=="" set "LLM_API_KEY=!NEW_LLM_KEY!"

echo.
echo   Current COMFYUI_BASE_URL : !COMFYUI_BASE_URL!
set "NEW_COMFY_URL="
set /p "NEW_COMFY_URL=  New COMFYUI_BASE_URL     : "
if not "!NEW_COMFY_URL!"=="" set "COMFYUI_BASE_URL=!NEW_COMFY_URL!"

powershell -NoProfile -Command "$envPath = '%ENV_FILE%'; $lines = if (Test-Path $envPath) { Get-Content $envPath } else { @() }; $map = [ordered]@{}; foreach ($l in $lines) { if ($l -match '^([^#=]+)=(.*)$') { $map[$matches[1].Trim()] = $matches[2] } }; $map['LLM_BASE_URL'] = '!LLM_BASE_URL!'; $map['LLM_MODEL'] = '!LLM_MODEL!'; $map['LLM_API_KEY'] = '!LLM_API_KEY!'; $map['COMFYUI_BASE_URL'] = '!COMFYUI_BASE_URL!'; if (-not $map.Contains('COMFYUI_TIMEOUT_SECONDS')) { $map['COMFYUI_TIMEOUT_SECONDS'] = '300' }; if (-not $map.Contains('OUTPUT_DIR')) { $map['OUTPUT_DIR'] = 'outputs' }; if (-not $map.Contains('WORKFLOW_DIR')) { $map['WORKFLOW_DIR'] = 'workflows' }; $out = $map.GetEnumerator() | ForEach-Object { \"$($_.Key)=$($_.Value)\" }; Set-Content -Path $envPath -Value $out -Encoding UTF8"

echo.
echo  [OK] Saved to .env!
call :CHECK_STATUS
if "!APP_UP!"=="1" (
    echo.
    set "RESTART_NOW="
    set /p "RESTART_NOW=  Server is running. Restart it now to apply changes? [Y/N]: "
    if /I "!RESTART_NOW!"=="Y" (
        for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr /C:":%PORT% " ^| findstr "LISTENING"') do taskkill /PID %%P /F >nul 2>&1
        timeout /t 1 /nobreak >nul
        pushd "%PROJECT_DIR%"
        start "Comics AI Studio - Server" cmd /k "title Comics AI Studio - Server && python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%"
        popd
        echo  [OK] Server restarted with new settings.
    )
)
timeout /t 2 /nobreak >nul
goto MAIN_MENU

:TEST_CONNECTIONS
echo.
echo  Testing LLM (!LLM_BASE_URL!)...
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri ('!LLM_BASE_URL!/models') -TimeoutSec 4 -UseBasicParsing; Write-Host ('  [OK] LLM reachable (HTTP ' + $r.StatusCode + ')') -ForegroundColor Green } catch { Write-Host ('  [FAIL] LLM unreachable: ' + $_.Exception.Message) -ForegroundColor Red }"
echo  Testing ComfyUI (!COMFYUI_BASE_URL!)...
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri ('!COMFYUI_BASE_URL!/system_stats') -TimeoutSec 4 -UseBasicParsing; Write-Host ('  [OK] ComfyUI reachable (HTTP ' + $r.StatusCode + ')') -ForegroundColor Green } catch { Write-Host ('  [FAIL] ComfyUI unreachable: ' + $_.Exception.Message) -ForegroundColor Red }"
echo.
pause
goto MAIN_MENU

:OPEN_BROWSER
start "" "http://127.0.0.1:%PORT%"
goto MAIN_MENU

:EXIT_APP
exit /b 0

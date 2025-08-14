@echo off
REM Navegar para o diretorio do script
cd /d "%~dp0"

REM Verificar se o Python esta disponivel
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Python nao encontrado no sistema!
    pause
    exit /b 1
)

echo ============================================
echo   GOvGO Dashboard - MODO DEBUG ATIVO
echo   Logs aparecerao em tempo real abaixo
echo   URL: http://localhost:8055
echo ============================================
echo.

REM Executar Python com debug em background para nao bloquear
start /b python GvG_SU_Report_v1.py --debug

REM Aguardar inicializacao e abrir browser na mesma janela
timeout /t 4 /nobreak >nul

REM Abrir Chrome diretamente
"C:\Program Files\Google\Chrome\Application\chrome.exe" http://localhost:8055 2>nul || "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" http://localhost:8055 2>nul || start http://localhost:8055

echo.
echo ============================================
echo   Browser aberto! Dashboard rodando...
echo   Pressione Ctrl+C para parar
echo ============================================
echo.

REM Manter janela aberta
:loop
timeout /t 30 /nobreak >nul
echo [%TIME%] Dashboard ativo...
goto loop


@echo off
echo ================================================================================
echo                         GOVGO v1 - PIPELINE AUTOMATICO
echo ================================================================================
echo.
echo Este script executa em sequencia:
echo   03_download_pncp_contracts.py    - Download de contratos PNCP
echo   04_generate_embeddings.py        - Geracao de embeddings
echo   05_categorize_contracts.py       - Categorizacao de contratos
echo.
echo ================================================================================

REM Definir diretório do script
cd /d "%~dp0"

REM Gerar timestamp único para toda a sessão do pipeline
for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set mydate=%%c%%b%%a
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set mytime=%%a%%b
set mytime=%mytime: =0%
set PIPELINE_TIMESTAMP=%mydate%_%mytime:~0,4%
set PIPELINE_LOG_FILE=log_%PIPELINE_TIMESTAMP%.log

echo [INFO] Sessao do pipeline: %PIPELINE_TIMESTAMP%
echo [INFO] Arquivo de log: %PIPELINE_LOG_FILE%

REM Inicializar arquivo de log unificado
echo ================================================================================ > ..\logs\%PIPELINE_LOG_FILE%
echo GOVGO v1 - PIPELINE AUTOMATICO - SESSAO %PIPELINE_TIMESTAMP% >> ..\logs\%PIPELINE_LOG_FILE%
echo ================================================================================ >> ..\logs\%PIPELINE_LOG_FILE%
echo Horario de inicio: %date% %time% >> ..\logs\%PIPELINE_LOG_FILE%
echo -------------------------------------------------------------------------------- >> ..\logs\%PIPELINE_LOG_FILE%
echo. >> ..\logs\%PIPELINE_LOG_FILE%

REM Verificar se Python está disponível
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] ERRO: Python nao encontrado no PATH
    echo    Instale Python ou adicione ao PATH do sistema
    pause
    exit /b 1
)

echo [INFO] Iniciando pipeline automatico...
echo.

REM ================================================================================
REM ETAPA 1: DOWNLOAD CONTRATOS PNCP
REM ================================================================================
echo [ETAPA 1/3] [DOWNLOAD] Executando download de contratos PNCP...
echo ================================================================================

set PIPELINE_STEP=1
python 03_download_pncp_contracts.py
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] ERRO na etapa 1 - Download de contratos falhou
    echo    Verifique logs acima e tente novamente
    pause
    exit /b 1
)

echo.
echo [SUCESSO] ETAPA 1 CONCLUIDA - Download de contratos finalizado
echo.

REM ================================================================================
REM ETAPA 2: GERAR EMBEDDINGS
REM ================================================================================
echo [ETAPA 2/3] [EMBEDDINGS] Executando geracao de embeddings...
echo ================================================================================

set PIPELINE_STEP=2
python 04_generate_embeddings.py
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] ERRO na etapa 2 - Geracao de embeddings falhou
    echo    Verifique logs acima e tente novamente
    pause
    exit /b 1
)

echo.
echo [SUCESSO] ETAPA 2 CONCLUIDA - Embeddings gerados com sucesso
echo.

REM ================================================================================
REM ETAPA 3: CATEGORIZAR CONTRATOS
REM ================================================================================
echo [ETAPA 3/3] [CATEGORIZAR] Executando categorizacao de contratos...
echo ================================================================================

set PIPELINE_STEP=3
python 05_categorize_contracts.py
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] ERRO na etapa 3 - Categorizacao falhou
    echo    Verifique logs acima e tente novamente
    pause
    exit /b 1
)

echo.
echo [SUCESSO] ETAPA 3 CONCLUIDA - Categorizacao finalizada
echo.

REM Finalizar arquivo de log unificado
echo. >> ..\logs\%PIPELINE_LOG_FILE%
echo -------------------------------------------------------------------------------- >> ..\logs\%PIPELINE_LOG_FILE%
echo PIPELINE CONCLUIDO COM SUCESSO! >> ..\logs\%PIPELINE_LOG_FILE%
echo Horario de termino: %date% %time% >> ..\logs\%PIPELINE_LOG_FILE%
echo Todas as etapas executadas: Download, Embeddings, Categorizacao >> ..\logs\%PIPELINE_LOG_FILE%
echo ================================================================================ >> ..\logs\%PIPELINE_LOG_FILE%

REM ================================================================================
REM PIPELINE CONCLUIDO
REM ================================================================================
echo ================================================================================
echo [SUCESSO] PIPELINE CONCLUIDO COM SUCESSO!
echo ================================================================================
echo.
echo Todas as etapas foram executadas:
echo   [OK] Download de contratos PNCP
echo   [OK] Geracao de embeddings  
echo   [OK] Categorizacao de contratos
echo.
echo O sistema esta atualizado e pronto para uso.
echo ================================================================================
echo.
pause

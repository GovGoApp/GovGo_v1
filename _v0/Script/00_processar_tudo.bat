@echo off
REM =======================================================================
REM PROCESSAMENTO DIÁRIO COMPLETO PNCP - SCRIPT PRINCIPAL
REM =======================================================================
REM Este script executa o fluxo completo de processamento de dados do PNCP:
REM 1. Download de contratações diárias
REM 2. Processamento de itens das contratações
REM 3. Carga de contratações para banco SQLite
REM 4. Carga de itens para banco SQLite
REM 5. Exportação de views para Excel
REM 6. Processamento de embeddings e envio para Supabase
REM 7. Migração de contratos expirados e limpeza da base principal
REM
REM Registra logs detalhados e controla tratamento de erros.
REM =======================================================================

@echo off
echo Pipeline PNCP - %date% %time%
echo.

REM Configura pasta para logs
set BASE_PATH=C:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\v0\Script\

set LOG_DIR=%BASE_PATH%LOGS
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set LOG_FILE=%LOG_DIR%\processamento_%date:~-4,4%%date:~-7,2%%date:~-10,2%.log

REM Inicia o log
echo Processamento iniciado em: %date% %time% > "%LOG_FILE%"

set PYTHON=python
set SCRIPT_DOWNLOAD="%BASE_PATH%01_pncp_download.py"
set SCRIPT_ITENS="%BASE_PATH%02_pncp_itens.py"
set SCRIPT_DB_CONTRATACOES="%BASE_PATH%03_db_contratacoes.py"
set SCRIPT_DB_ITENS="%BASE_PATH%04_db_itens.py"
set SCRIPT_EXCEL="%BASE_PATH%05_excel_export.py"
set SCRIPT_SUPABASE="%BASE_PATH%06_supabase_embeddings.py"
set SCRIPT_CLEAN_EXPIRED="%BASE_PATH%07_clean_expired.py"

echo Scripts configurados >> "%LOG_FILE%"
cd /d "%BASE_PATH%"
echo Diretorio de trabalho: %CD% >> "%LOG_FILE%"

REM ETAPA 1 - Download (sempre verifica se precisa)
echo [1/7] Download de contratacoes... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_DOWNLOAD%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha no download! >> "%LOG_FILE%"
    echo ERRO: Falha no download!
    goto erro
)

REM ETAPA 2 - Itens (só se houve download)
echo [2/7] Processamento de itens... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_ITENS%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha no processamento de itens! >> "%LOG_FILE%"
    echo ERRO: Falha no processamento de itens!
    goto erro
)

REM ETAPA 3 - BD Contratações (só se houve dados novos)
echo [3/7] Carga contratacoes SQLite... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_DB_CONTRATACOES%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha na carga de contratacoes! >> "%LOG_FILE%"
    echo ERRO: Falha na carga de contratacoes!
    goto erro
)

REM ETAPA 4 - BD Itens (só se houve dados novos)
echo [4/7] Carga itens SQLite... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_DB_ITENS%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha na carga de itens! >> "%LOG_FILE%"
    echo ERRO: Falha na carga de itens!
    goto erro
)

REM ETAPA 5 - Excel (só se BD foi atualizado)
echo [5/7] Exportacao Excel... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_EXCEL%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha na exportacao Excel! >> "%LOG_FILE%"
    echo ERRO: Falha na exportacao Excel!
    goto erro
)

REM ETAPA 6 - Embeddings (só se há Excel novo)
echo [6/7] Embeddings Supabase... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_SUPABASE%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha nos embeddings! >> "%LOG_FILE%"
    echo ERRO: Falha nos embeddings!
    goto erro
)

REM ETAPA 7 - Limpeza (só uma vez por dia)
echo [7/7] Limpeza contratos expirados... >> "%LOG_FILE%"
echo %PYTHON% %SCRIPT_CLEAN_EXPIRED%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha na limpeza! >> "%LOG_FILE%"
    echo ERRO: Falha na limpeza!
    goto erro
)

echo Processamento completo! - %time% >> "%LOG_FILE%"
goto fim

:erro
echo Processamento finalizado com ERROS! - %time% >> "%LOG_FILE%"

:fim
echo.
echo Logs salvos em: %LOG_FILE%
echo.
echo Pressione qualquer tecla para sair...
pause > nul
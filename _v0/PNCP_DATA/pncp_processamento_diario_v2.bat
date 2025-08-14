@echo off
REM filepath: c:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\PNCP_DATA\pncp_processamento_diario_v1.bat
echo ===================================================================
echo         PROCESSAMENTO DIARIO COMPLETO PNCP - %date% %time%
echo ===================================================================
echo.

REM Configura pasta para logs
set LOG_DIR=C:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\PNCP_DATA\logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set LOG_FILE=%LOG_DIR%\pncp_processamento_%date:~-4,4%%date:~-7,2%%date:~-10,2%.log

REM Inicia o log
echo Processamento iniciado em: %date% %time% > "%LOG_FILE%"

set PYTHON=python
set BASE_PATH=C:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\
set SCRIPT_CONTRATACOES="%BASE_PATH%PNCP_DATA\CONTRATACOES\pncp_api_contratacoes_diario_v0.py"
set SCRIPT_ITENS="%BASE_PATH%PNCP_DATA\ITENS\pncp_itens_contratacoes_diario_v0.py"
set SCRIPT_LOAD_CONTRATACAO="%BASE_PATH%DB\load_contratacao_v3.py"
set SCRIPT_LOAD_ITENS="%BASE_PATH%DB\load_itens_contratacao_v3.py"
set SCRIPT_EXPORT_EXCEL="%BASE_PATH%GvG\SQL\GvG_SQL_v2.py"
set SCRIPT_SUPABASE="%BASE_PATH%GvG\Supabase\GvG_SP_Integration_v0.py"

echo Usando os seguintes caminhos: >> "%LOG_FILE%"
echo Script Contratacoes: %SCRIPT_CONTRATACOES% >> "%LOG_FILE%"
echo Script Itens: %SCRIPT_ITENS% >> "%LOG_FILE%"
echo Script Exportação Excel: %SCRIPT_EXPORT_EXCEL% >> "%LOG_FILE%"
echo Script Supabase: %SCRIPT_SUPABASE% >> "%LOG_FILE%"
echo Script Load Contratacao: %SCRIPT_LOAD_CONTRATACAO% >> "%LOG_FILE%"
echo Script Load Itens: %SCRIPT_LOAD_ITENS% >> "%LOG_FILE%"

cd /d "C:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts"
echo Diretorio de trabalho: %CD% >> "%LOG_FILE%"

echo [1/6] Baixando contratacoes do dia...
echo [1/6] Baixando contratacoes do dia... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_CONTRATACOES%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao baixar contratacoes! >> "%LOG_FILE%"
    echo ERRO: Falha ao baixar contratacoes!
    goto erro
)
echo Download de contratacoes concluido com sucesso >> "%LOG_FILE%"
echo.

echo [2/6] Processando itens das contratacoes...
echo [2/6] Processando itens das contratacoes... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_ITENS%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao processar itens! >> "%LOG_FILE%"
    echo ERRO: Falha ao processar itens!
    goto erro
)
echo Processamento de itens concluido com sucesso >> "%LOG_FILE%"
echo.

echo [3/6] Carregando contratacoes para banco SQLite...
echo [3/6] Carregando contratacoes para banco SQLite... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_LOAD_CONTRATACAO%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao carregar contratacoes para SQLite! >> "%LOG_FILE%"
    echo ERRO: Falha ao carregar contratacoes para SQLite!
    goto erro
)
echo Carga de contratacoes concluida com sucesso >> "%LOG_FILE%"
echo.

echo [4/6] Carregando itens para banco SQLite...
echo [4/6] Carregando itens para banco SQLite... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_LOAD_ITENS%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao carregar itens para SQLite! >> "%LOG_FILE%"
    echo ERRO: Falha ao carregar itens para SQLite!
    goto erro
)
echo Carga de itens concluida com sucesso >> "%LOG_FILE%"
echo.

echo [5/6] Exportando view para Excel...
echo [5/6] Exportando view para Excel... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_EXPORT_EXCEL%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao exportar dados para Excel! >> "%LOG_FILE%"
    echo ERRO: Falha ao exportar dados para Excel!
    goto erro
)
echo Exportacao para Excel concluida com sucesso >> "%LOG_FILE%"
echo.

echo [6/6] Processando embeddings e enviando para Supabase...
echo [6/6] Processando embeddings e enviando para Supabase... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_SUPABASE%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao processar embeddings ou enviar para Supabase! >> "%LOG_FILE%"
    echo ERRO: Falha ao processar embeddings ou enviar para Supabase!
    goto erro
)
echo Processamento de embeddings e envio para Supabase concluidos com sucesso >> "%LOG_FILE%"
echo.

echo ===================================================================
echo          PROCESSAMENTO COMPLETO CONCLUIDO COM SUCESSO! - %time%
echo ===================================================================
echo PROCESSAMENTO COMPLETO CONCLUIDO COM SUCESSO! - %time% >> "%LOG_FILE%"
goto fim

:erro
echo ===================================================================
echo          PROCESSAMENTO FINALIZADO COM ERROS! - %time%
echo ===================================================================
echo PROCESSAMENTO FINALIZADO COM ERROS! - %time% >> "%LOG_FILE%"

:fim
echo.
echo Logs salvos em: %LOG_FILE%
echo.
echo Pressione qualquer tecla para sair...
pause > nul
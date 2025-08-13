@echo off
echo ===================================================================
echo         PROCESSAMENTO DIARIO DE DADOS PNCP - %date% %time%
echo ===================================================================
echo.

REM Configura pasta para logs
set LOG_DIR=C:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\PNCP_DATA\logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set LOG_FILE=%LOG_DIR%\pncp_processamento_%date:~-4,4%%date:~-7,2%%date:~-10,2%.log

REM Inicia o log
echo Processamento iniciado em: %date% %time% > "%LOG_FILE%"

set PYTHON=python
set SCRIPT_CONTRATACOES="C:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\PNCP_DATA\CONTRATACOES\pncp_api_contratacoes_diario_v0.py"
set SCRIPT_ITENS="C:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\PNCP_DATA\ITENS\pncp_itens_contratacoes_diario_v0.py"

echo Usando os seguintes caminhos: >> "%LOG_FILE%"
echo Script Contratacoes: %SCRIPT_CONTRATACOES% >> "%LOG_FILE%"
echo Script Itens: %SCRIPT_ITENS% >> "%LOG_FILE%"

cd /d "C:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts"
echo Diretorio de trabalho: %CD% >> "%LOG_FILE%"

echo [1/2] Baixando contratacoes do dia...
echo [1/2] Baixando contratacoes do dia... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_CONTRATACOES%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao baixar contratacoes! >> "%LOG_FILE%"
    echo ERRO: Falha ao baixar contratacoes!
    goto erro
)
echo Download de contratacoes concluido com sucesso >> "%LOG_FILE%"
echo.

echo [2/2] Processando itens das contratacoes...
echo [2/2] Processando itens das contratacoes... >> "%LOG_FILE%"
%PYTHON% %SCRIPT_ITENS%
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao processar itens! >> "%LOG_FILE%"
    echo ERRO: Falha ao processar itens!
    goto erro
)
echo Processamento de itens concluido com sucesso >> "%LOG_FILE%"
echo.

echo ===================================================================
echo          PROCESSAMENTO CONCLUIDO COM SUCESSO! - %time%
echo ===================================================================
echo PROCESSAMENTO CONCLUIDO COM SUCESSO! - %time% >> "%LOG_FILE%"
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
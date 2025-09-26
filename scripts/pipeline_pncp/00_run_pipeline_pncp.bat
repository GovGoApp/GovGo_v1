@echo off
setlocal

REM ------------------------------------------------------------------
REM Pipeline PNCP (simples) - 01 → 02 → 03
REM Usa um PIPELINE_TIMESTAMP único para log unificado
REM ------------------------------------------------------------------

cd /d "%~dp0"

for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set mydate=%%c%%b%%a
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set mytime=%%a%%b
set mytime=%mytime: =0%
set PIPELINE_TIMESTAMP=%mydate%_%mytime:~0,4%

echo ================================================================================
echo GOVGO v1 - Pipeline PNCP (novo) - %PIPELINE_TIMESTAMP%
echo ================================================================================
echo -
echo -------------------------------------------------------------------------------
echo -------------------------------------------------------------------------------
echo -------------------------------------------------------------------------------


set PIPELINE_STEP=ETAPA_1_DOWNLOAD
python 01_pipeline_pncp_download.py
if %errorlevel% neq 0 (
  echo [ERRO] Etapa 01 falhou

)

echo -------------------------------------------------------------------------------
echo -------------------------------------------------------------------------------
echo -------------------------------------------------------------------------------


set PIPELINE_STEP=ETAPA_2_EMBEDDINGS
python 02_pipeline_pncp_embeddings.py
if %errorlevel% neq 0 (
  echo [ERRO] Etapa 02 falhou
  
)

echo -------------------------------------------------------------------------------
echo -------------------------------------------------------------------------------
echo -------------------------------------------------------------------------------

set PIPELINE_STEP=ETAPA_3_CATEGORIZACAO
python 03_pipeline_pncp_categorization.py
if %errorlevel% neq 0 (
  echo [ERRO] Etapa 03 falhou

)

echo -------------------------------------------------------------------------------
echo -------------------------------------------------------------------------------
echo -------------------------------------------------------------------------------

echo [SUCESSO] Pipeline PNCP concluido: %PIPELINE_TIMESTAMP%
endlocal

echo -
echo Pressione qualquer tecla para continuar. . .
pause > nul
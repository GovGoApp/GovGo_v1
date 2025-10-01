@echo off
setlocal

REM ------------------------------------------------------------------
REM Pipeline Boletim - 01 -> 02
REM Usa um PIPELINE_TIMESTAMP unico para log unificado
REM ------------------------------------------------------------------

cd /d "%~dp0"

for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set mydate=%%c%%b%%a
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set mytime=%%a%%b
set mytime=%mytime: =0%
set PIPELINE_TIMESTAMP=%mydate%_%mytime:~0,4%

echo ================================================================================
echo GOVGO v1 - Pipeline Boletim - %PIPELINE_TIMESTAMP%
echo ================================================================================
echo -

set PIPELINE_STEP=ETAPA_1_EXECUCAO
python 01_run_scheduled_boletins.py
if %errorlevel% neq 0 (
  echo [ERRO] Etapa 01 falhou
  exit /b 1
)

echo -
echo -------------------------------------------------------------------------------
echo -

set PIPELINE_STEP=ETAPA_2_ENVIO
python 02_send_boletins_email.py
if %errorlevel% neq 0 (
  echo [ERRO] Etapa 02 falhou
  exit /b 1
)

echo -
echo -------------------------------------------------------------------------------
echo -

echo [SUCESSO] Pipeline Boletim concluido: %PIPELINE_TIMESTAMP%
endlocal

echo -
echo Pressione qualquer tecla para continuar. . .
pause > nul

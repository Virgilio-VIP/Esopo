@echo off
title Esopo - Dashboard de Pecuaria
echo.
echo  ============================================
echo     ESOPO - Pecuaria de Precisao
echo  ============================================
echo.
echo  Iniciando o dashboard...
echo.

cd /d "%~dp0"

set "PYTHON=python"
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Python nao encontrado no PATH.
    echo  Instale o Python 3 e tente novamente.
    pause
    exit /b 1
)

if not exist .venv\Scripts\python.exe (
    echo  Ambiente virtual nao encontrado. Criando .venv...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo  [ERRO] Falha ao criar o ambiente virtual.
        pause
        exit /b 1
    )
)

set "VENV_PY=.venv\Scripts\python.exe"
set "VENV_PIP=.venv\Scripts\pip.exe"

echo  Encerrando instancia antiga na porta 8501, se existir...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

echo  Verificando dependencias...
"%VENV_PY%" -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo  [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)

echo  Ambiente virtual pronto.
echo  Abrindo no navegador em 3 segundos...
echo.
echo  Acesse: http://localhost:8501
echo  Para encerrar: pressione Ctrl+C nesta janela
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8501"

"%VENV_PY%" -m streamlit run execution\dashboard.py --server.port 8501 --server.headless true

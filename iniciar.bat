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

if not exist .venv\Scripts\activate.bat (
    echo  [ERRO] Ambiente virtual nao encontrado!
    echo  Execute primeiro: python -m venv .venv
    echo  Depois: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo  Ambiente virtual ativado.
echo  Abrindo no navegador em 3 segundos...
echo.
echo  Acesse: http://localhost:8501
echo  Para encerrar: pressione Ctrl+C nesta janela
echo.

streamlit run execution\dashboard.py --server.port 8501

@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  Roda a bateria de QA na Loja Girassol
REM  Sobe o servidor, executa os testes e derruba o servidor.
REM  Basta dar dois cliques neste arquivo.
REM ============================================================

cd /d "%~dp0"

echo.
echo === Verificando o Python ===
where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo.
        echo ERRO: Python nao foi encontrado.
        echo Instale em https://python.org/downloads e marque
        echo "Add Python to PATH" durante a instalacao.
        echo.
        pause
        exit /b 1
    )
    set PY=py
) else (
    set PY=python
)
%PY% --version

echo.
echo === Verificando o Playwright ===
%PY% -c "from playwright.sync_api import sync_playwright" >nul 2>&1
if errorlevel 1 (
    echo Pacote Playwright nao instalado. Instalando agora...
    %PY% -m pip install playwright
)

REM Conferir o pacote nao basta: o navegador e baixado separado, e sem ele o
REM runner falha na primeira linha. Este teste abre o Chromium de verdade.
%PY% -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(); b.close(); p.stop()" >nul 2>&1
if errorlevel 1 (
    echo Navegador Chromium nao encontrado. Baixando (~150 MB, demora um pouco)...
    %PY% -m playwright install chromium
)

echo.
echo === Subindo a loja em http://localhost:8000 ===
start "Servidor Loja Girassol" /min %PY% -m http.server 8000
timeout /t 3 /nobreak >nul

echo.
echo === Rodando a bateria de testes ===
echo.
%PY% ..\qa-web-tester\scripts\runner.py plano-checkout.json --saida resultados --slow-mo 200

echo.
echo === Encerrando o servidor ===
taskkill /FI "WINDOWTITLE eq Servidor Loja Girassol*" /T /F >nul 2>&1

echo.
echo Resultados em: resultados\resultados.json
echo Screenshots em: resultados\evidencias\
echo.
pause

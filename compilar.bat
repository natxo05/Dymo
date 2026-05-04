@echo off
REM ============================================================
REM Compila app.py a un executable .exe per Windows
REM Busca automaticament una versio compatible de Python
REM ============================================================

echo.
echo ============================================================
echo   COMPILANT DymoEtiquetes.exe
echo ============================================================
echo.

REM Busquem una versio de Python compatible (3.12, 3.13, 3.11, 3.10)
REM evitant la 3.14 perque Pillow encara no hi es compatible.
set PYEXE=
for %%V in (3.12 3.13 3.11 3.10) do (
    if not defined PYEXE (
        py -%%V --version >nul 2>&1
        if not errorlevel 1 (
            set PYEXE=py -%%V
            echo [OK] Trobada Python %%V
        )
    )
)

if not defined PYEXE (
    echo [ERROR] No s'ha trobat cap versio compatible de Python.
    echo.
    echo Pillow encara no suporta Python 3.14 a Windows.
    echo.
    echo Solucio: instal.la Python 3.12 des d'aqui:
    echo   https://www.python.org/downloads/release/python-31210/
    echo.
    echo Durant la instal.lacio, marca "Add python.exe to PATH".
    echo Pots tenir les dues versions instal.lades alhora.
    echo.
    pause
    exit /b 1
)

echo.
echo [1/3] Instal.lant dependencies amb %PYEXE%...
%PYEXE% -m pip install --upgrade pip >nul
%PYEXE% -m pip install dymo-bluetooth pillow pyinstaller customtkinter
if errorlevel 1 (
    echo [ERROR] No s'han pogut instal.lar les dependencies.
    pause
    exit /b 1
)

echo.
echo [2/3] Compilant l'executable (pot trigar 1-2 minuts)...
echo.

%PYEXE% -m PyInstaller ^
    --onedir ^
    --windowed ^
    --name DymoEtiquetes ^
    --icon "assets/logo.ico" ^
    --collect-all bleak ^
    --collect-all dymo_bluetooth ^
    --collect-all customtkinter ^
    --hidden-import=PIL._tkinter_finder ^
    --add-data "assets;assets" ^
    --noconfirm ^
    app.py

if errorlevel 1 (
    echo.
    echo [ERROR] La compilacio ha fallat.
    pause
    exit /b 1
)

echo.
echo [3/3] Preparant carpeta final...

if not exist "dist\DymoEtiquetes\icones" mkdir "dist\DymoEtiquetes\icones"

echo.
echo ============================================================
echo   COMPILACIO COMPLETADA!
echo ============================================================
echo.
echo L'executable esta a:  dist\DymoEtiquetes\DymoEtiquetes.exe
echo.
echo Copia tota la carpeta "dist\DymoEtiquetes" on vulguis.
echo L'executable funciona directament des d'aquesta carpeta.
echo.
echo CONSELL: fes un acces directe a DymoEtiquetes.exe i posa'l
echo a l'escriptori per accedir-hi mes facilment.
echo.

explorer dist\DymoEtiquetes

pause

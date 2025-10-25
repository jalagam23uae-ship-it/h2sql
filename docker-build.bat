@echo off
echo =========================================
echo Building H2SQL Docker Image
echo =========================================
echo.

docker build -t h2sql-api:latest .

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =========================================
    echo Build successful!
    echo =========================================
    echo.
    echo Image: h2sql-api:latest
    echo.
    echo To run: docker-run.bat
    echo Or: docker-compose up
) else (
    echo.
    echo =========================================
    echo Build failed!
    echo =========================================
)

pause

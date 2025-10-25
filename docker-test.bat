@echo off
echo =========================================
echo Testing H2SQL API Endpoints
echo =========================================
echo.

REM Wait for service to be ready
echo Waiting for API to be ready...
timeout /t 5 /nobreak > nul

REM Run tests
cd tests
call test_endpoints.bat
cd ..

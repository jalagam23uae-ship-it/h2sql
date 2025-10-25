@echo off
echo =========================================
echo Starting H2SQL API with Docker Compose
echo =========================================
echo.

docker-compose up -d

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =========================================
    echo H2SQL API Started Successfully!
    echo =========================================
    echo.
    echo API is running at: http://localhost:11901
    echo API Docs: http://localhost:11901/docs
    echo Health Check: http://localhost:11901/health
    echo.
    echo To view logs: docker-compose logs -f
    echo To stop: docker-compose down
    echo.
) else (
    echo.
    echo =========================================
    echo Failed to start!
    echo =========================================
)

pause

@echo off
REM H2SQL API Test Script for Windows

SET BASE_URL=http://localhost:11901

echo =========================================
echo H2SQL API Endpoint Tests
echo =========================================
echo.

echo Starting tests...
echo.

REM Test 1: Health Check
echo Test 1: Health check...
curl -s -X GET "%BASE_URL%/health"
echo.
echo.

REM Test 2: Root endpoint
echo Test 2: Root endpoint...
curl -s -X GET "%BASE_URL%/"
echo.
echo.

REM Test 3: Execute Query
echo Test 3: Execute query endpoint...
curl -s -X POST "%BASE_URL%/h2s/data-upload/executequey" ^
    -H "Content-Type: application/json" ^
    -d "{\"project_id\": 17, \"question\": \"test query\"}"
echo.
echo.

REM Test 4: Graph endpoint
echo Test 4: Graph generation endpoint...
curl -s -X POST "%BASE_URL%/h2s/data-upload/graph" ^
    -H "Content-Type: application/json" ^
    -d "{\"project_id\": 17, \"response_id\": \"test_id\"}"
echo.
echo.

REM Test 5: Recommendations
echo Test 5: Recommendations endpoint...
curl -s -X POST "%BASE_URL%/h2s/data-upload/recommendations/question" ^
    -H "Content-Type: application/json" ^
    -d "{\"projectId\": 17}"
echo.
echo.

echo =========================================
echo Tests completed!
echo =========================================
echo Visit http://localhost:11901/docs for interactive API testing
pause

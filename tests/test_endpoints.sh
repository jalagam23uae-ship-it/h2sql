#!/bin/bash
# H2SQL API Test Script

BASE_URL="http://localhost:11901"

echo "========================================="
echo "H2SQL API Endpoint Tests"
echo "========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TOTAL=0
PASSED=0
FAILED=0

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4
    
    TOTAL=$((TOTAL + 1))
    echo -n "Test $TOTAL: $description... "
    
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X $method "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "${GREEN}PASS${NC} (HTTP $http_code)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}FAIL${NC} (HTTP $http_code)"
        echo "  Response: $body"
        FAILED=$((FAILED + 1))
    fi
}

echo "Starting tests..."
echo ""

# Test 1: Health Check
test_endpoint "GET" "/health" "Health check"

# Test 2: Root endpoint
test_endpoint "GET" "/" "Root endpoint"

# Test 3: Execute Query (will fail without valid project_id)
test_endpoint "POST" "/h2s/data-upload/executequey" "Execute query endpoint" \
    '{"project_id": 17, "question": "test query"}'

# Test 4: Graph endpoint (will fail without valid response_id)
test_endpoint "POST" "/h2s/data-upload/graph" "Graph generation endpoint" \
    '{"project_id": 17, "response_id": "test_id"}'

# Test 5: Recommendations endpoint
test_endpoint "POST" "/h2s/data-upload/recommendations/question" "Recommendations endpoint" \
    '{"projectId": 17}'

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "Total:  $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi

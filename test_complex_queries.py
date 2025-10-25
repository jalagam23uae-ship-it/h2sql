"""
Comprehensive Complex Query Testing for H2SQL
Tests both PostgreSQL and Oracle with various query types
"""
import requests
import json
import time

BASE_URL = "http://localhost:11901/h2s/data-upload"
PG_PROJECT_ID = 22  # PostgreSQL
ORACLE_PROJECT_ID = 23  # Oracle

def test_query(project_id, question, db_name, test_num):
    """Execute a query and display results"""
    print(f"\n{'='*80}")
    print(f"TEST {test_num}: {db_name.upper()}")
    print(f"{'='*80}")
    print(f"Question: {question}")

    payload = {
        "project_id": project_id,
        "question": question
    }

    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/executequey", json=payload, timeout=300)
        elapsed = time.time() - start

        print(f"\nStatus: {response.status_code} | Time: {elapsed:.2f}s")

        if response.status_code == 200:
            result = response.json()

            # Display SQL
            sql = result.get('llm_generated_sql', 'N/A')
            print(f"\n[SQL Generated]:")
            print(sql)

            # Display results
            db_results = result.get('db_result', [])
            print(f"\n[Results]: {len(db_results)} rows")

            # Show first 10 rows
            for i, row in enumerate(db_results[:10], 1):
                print(f"  {i}. {row}")

            if len(db_results) > 10:
                print(f"  ... and {len(db_results) - 10} more rows")

            # Display human readable answer if available
            answer = result.get('human_readable_answer', '')
            if answer and answer != 'Error: 401':
                print(f"\n[Answer]: {answer}")

            return True, elapsed
        else:
            print(f"\n[FAILED]")
            try:
                error = response.json()
                print(f"Error: {error.get('detail', response.text)[:300]}")
            except:
                print(f"Error: {response.text[:300]}")
            return False, elapsed

    except Exception as e:
        elapsed = time.time() - start
        print(f"\n[EXCEPTION]: {str(e)}")
        return False, elapsed


print("="*80)
print("COMPLEX QUERY TESTING - LLAMA-4-SCOUT VIA OPENROUTER")
print("="*80)
print("Model: meta-llama/llama-4-scout")
print("Provider: OpenRouter API")

results = []

# ============================================================================
# POSTGRESQL TESTS
# ============================================================================

print("\n\n" + "="*80)
print("PART 1: POSTGRESQL COMPLEX QUERIES")
print("="*80)

# Test 1: Simple Aggregation
success, time1 = test_query(
    PG_PROJECT_ID,
    "how many customers are there?",
    "PostgreSQL",
    "1A"
)
results.append(("PG - Simple Count", success, time1))

# Test 2: GROUP BY with SUM
success, time2 = test_query(
    PG_PROJECT_ID,
    "show me total sales amount for each product category",
    "PostgreSQL",
    "1B"
)
results.append(("PG - Group By Sum", success, time2))

# Test 3: GROUP BY with Multiple Aggregations
success, time3 = test_query(
    PG_PROJECT_ID,
    "for each product category, show me total sales, average price, and number of orders",
    "PostgreSQL",
    "1C"
)
results.append(("PG - Multiple Aggregations", success, time3))

# Test 4: WHERE Clause Filtering
success, time4 = test_query(
    PG_PROJECT_ID,
    "show me all orders where total amount is greater than 500",
    "PostgreSQL",
    "1D"
)
results.append(("PG - WHERE Filter", success, time4))

# Test 5: GROUP BY with HAVING
success, time5 = test_query(
    PG_PROJECT_ID,
    "which product categories have total sales greater than 1000?",
    "PostgreSQL",
    "1E"
)
results.append(("PG - HAVING Clause", success, time5))

# Test 6: ORDER BY with LIMIT
success, time6 = test_query(
    PG_PROJECT_ID,
    "show me top 5 customers by total purchase amount",
    "PostgreSQL",
    "1F"
)
results.append(("PG - TOP N Query", success, time6))

# Test 7: Date/String Functions
success, time7 = test_query(
    PG_PROJECT_ID,
    "how many orders were placed in each shipping country?",
    "PostgreSQL",
    "1G"
)
results.append(("PG - Count by Country", success, time7))

# Test 8: Multiple GROUP BY columns
success, time8 = test_query(
    PG_PROJECT_ID,
    "show me total sales by product category and payment method",
    "PostgreSQL",
    "1H"
)
results.append(("PG - Multi-column GROUP BY", success, time8))

# Test 9: DISTINCT Count
success, time9 = test_query(
    PG_PROJECT_ID,
    "how many unique customers made purchases?",
    "PostgreSQL",
    "1I"
)
results.append(("PG - DISTINCT Count", success, time9))

# Test 10: Complex WHERE with AND/OR
success, time10 = test_query(
    PG_PROJECT_ID,
    "show me electronics orders with total amount greater than 200 or clothing orders greater than 100",
    "PostgreSQL",
    "1J"
)
results.append(("PG - Complex WHERE", success, time10))

# ============================================================================
# ORACLE TESTS
# ============================================================================

print("\n\n" + "="*80)
print("PART 2: ORACLE COMPLEX QUERIES")
print("="*80)

# Test 11: Simple Aggregation (Oracle)
success, time11 = test_query(
    ORACLE_PROJECT_ID,
    "how many orders are in the database?",
    "Oracle",
    "2A"
)
results.append(("Oracle - Simple Count", success, time11))

# Test 12: GROUP BY with SUM (Oracle)
success, time12 = test_query(
    ORACLE_PROJECT_ID,
    "what is the sum of total_amount grouped by product_category?",
    "Oracle",
    "2B"
)
results.append(("Oracle - Group By Sum", success, time12))

# Test 13: GROUP BY with AVG (Oracle)
success, time13 = test_query(
    ORACLE_PROJECT_ID,
    "show me average order amount for each product category",
    "Oracle",
    "2C"
)
results.append(("Oracle - Average by Category", success, time13))

# Test 14: MAX/MIN Aggregations (Oracle)
success, time14 = test_query(
    ORACLE_PROJECT_ID,
    "what are the maximum and minimum unit prices for each product category?",
    "Oracle",
    "2D"
)
results.append(("Oracle - MAX/MIN", success, time14))

# Test 15: WHERE Filtering (Oracle)
success, time15 = test_query(
    ORACLE_PROJECT_ID,
    "show me all orders where order_status is Delivered",
    "Oracle",
    "2E"
)
results.append(("Oracle - WHERE Status", success, time15))

# Test 16: GROUP BY with COUNT (Oracle)
success, time16 = test_query(
    ORACLE_PROJECT_ID,
    "how many orders were placed using each payment method?",
    "Oracle",
    "2F"
)
results.append(("Oracle - Count by Payment", success, time16))

# Test 17: ORDER BY DESC (Oracle)
success, time17 = test_query(
    ORACLE_PROJECT_ID,
    "show me product categories ordered by total sales descending",
    "Oracle",
    "2G"
)
results.append(("Oracle - ORDER BY DESC", success, time17))

# Test 18: Multiple Aggregations (Oracle)
success, time18 = test_query(
    ORACLE_PROJECT_ID,
    "for each shipping country, show total orders, total sales, and average order value",
    "Oracle",
    "2H"
)
results.append(("Oracle - Multi Aggregation", success, time18))

# Test 19: HAVING Clause (Oracle)
success, time19 = test_query(
    ORACLE_PROJECT_ID,
    "which product categories have more than 5 orders?",
    "Oracle",
    "2I"
)
results.append(("Oracle - HAVING Count", success, time19))

# Test 20: Complex Grouping (Oracle)
success, time20 = test_query(
    ORACLE_PROJECT_ID,
    "show me total sales by product category and shipping country",
    "Oracle",
    "2J"
)
results.append(("Oracle - Multi-column GROUP BY", success, time20))

# ============================================================================
# SUMMARY
# ============================================================================

print("\n\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

pg_tests = [r for r in results if r[0].startswith("PG")]
oracle_tests = [r for r in results if r[0].startswith("Oracle")]

pg_passed = sum(1 for _, success, _ in pg_tests if success)
oracle_passed = sum(1 for _, success, _ in oracle_tests if success)

print(f"\nPOSTGRESQL TESTS:")
print(f"  Passed: {pg_passed}/{len(pg_tests)}")
print(f"  Success Rate: {pg_passed/len(pg_tests)*100:.1f}%")
pg_times = [t for _, success, t in pg_tests if success]
if pg_times:
    print(f"  Avg Time: {sum(pg_times)/len(pg_times):.2f}s")

print(f"\nORACLE TESTS:")
print(f"  Passed: {oracle_passed}/{len(oracle_tests)}")
print(f"  Success Rate: {oracle_passed/len(oracle_tests)*100:.1f}%")
oracle_times = [t for _, success, t in oracle_tests if success]
if oracle_times:
    print(f"  Avg Time: {sum(oracle_times)/len(oracle_times):.2f}s")

print(f"\nOVERALL:")
print(f"  Total Tests: {len(results)}")
print(f"  Total Passed: {pg_passed + oracle_passed}")
print(f"  Success Rate: {(pg_passed + oracle_passed)/len(results)*100:.1f}%")

print("\n" + "="*80)
print("DETAILED RESULTS")
print("="*80)

for i, (name, success, elapsed) in enumerate(results, 1):
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"{i:2d}. [{status}] {name:35s} - {elapsed:5.2f}s")

print("="*80)

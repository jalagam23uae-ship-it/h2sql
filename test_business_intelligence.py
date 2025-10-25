"""
Advanced Business Intelligence Queries Test
Testing H2SQL with real-world BI questions
"""
import requests
import json
import time

BASE_URL = "http://localhost:11901/h2s/data-upload"
ORACLE_PROJECT_ID = 23  # Oracle e-commerce database

def run_bi_query(question, test_num):
    """Execute a BI query and display results"""
    print(f"\n{'='*80}")
    print(f"BI QUERY {test_num}")
    print(f"{'='*80}")
    print(f"Question: {question}")

    payload = {
        "project_id": ORACLE_PROJECT_ID,
        "question": question
    }

    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/executequey", json=payload, timeout=300)
        elapsed = time.time() - start

        status_icon = "[OK]" if response.status_code == 200 else "[FAIL]"
        print(f"\n{status_icon} Status: {response.status_code} | Time: {elapsed:.2f}s")

        if response.status_code == 200:
            result = response.json()

            # Display SQL
            sql = result.get('llm_generated_sql', 'N/A')
            print(f"\n[SQL]:")
            # Pretty print SQL
            sql_lines = sql.split('\n')
            for line in sql_lines:
                print(f"  {line}")

            # Display results
            db_results = result.get('db_result', [])
            print(f"\n[RESULTS]: {len(db_results)} rows")

            # Show first 15 rows
            for i, row in enumerate(db_results[:15], 1):
                print(f"  {i:2d}. {row}")

            if len(db_results) > 15:
                print(f"  ... and {len(db_results) - 15} more rows")

            return True, elapsed, sql, db_results
        else:
            print(f"\n[ERROR]:")
            try:
                error = response.json()
                error_detail = error.get('detail', response.text)
                # Truncate long errors
                if len(error_detail) > 300:
                    print(f"  {error_detail[:300]}...")
                else:
                    print(f"  {error_detail}")
            except:
                print(f"  {response.text[:300]}")
            return False, elapsed, None, None

    except Exception as e:
        elapsed = time.time() - start
        print(f"\n[EXCEPTION]: {str(e)}")
        return False, elapsed, None, None


print("="*80)
print("BUSINESS INTELLIGENCE QUERIES TEST")
print("="*80)
print("Database: Oracle (TAQDB)")
print("Table: ECOM_SALES")
print("Model: meta-llama/llama-4-scout via OpenRouter")
print("="*80)

results = []

# ===========================================================================
# QUERY 1: Overall Sales Metrics by Region
# ===========================================================================

success, time1, sql1, data1 = run_bi_query(
    "What is the total sales and total orders by shipping country?",
    "1"
)
results.append(("Overall Sales by Region", success, time1))

# ===========================================================================
# QUERY 2: Revenue by Product Category
# ===========================================================================

success, time2, sql2, data2 = run_bi_query(
    "Which product categories generated the highest revenue?",
    "2"
)
results.append(("Revenue by Category", success, time2))

# ===========================================================================
# QUERY 3: Top 10 Best-Selling Products by Quantity
# ===========================================================================

success, time3, sql3, data3 = run_bi_query(
    "What are the top 10 best-selling products by quantity sold?",
    "3"
)
results.append(("Top 10 by Quantity", success, time3))

# ===========================================================================
# QUERY 4: Top 10 Products by Revenue
# ===========================================================================

success, time4, sql4, data4 = run_bi_query(
    "Show me the top 10 products by total revenue",
    "4"
)
results.append(("Top 10 by Revenue", success, time4))

# ===========================================================================
# QUERY 5: Average Order Value by Country
# ===========================================================================

success, time5, sql5, data5 = run_bi_query(
    "What is the average order value by shipping country?",
    "5"
)
results.append(("AOV by Country", success, time5))

# ===========================================================================
# QUERY 6: Payment Method Distribution
# ===========================================================================

success, time6, sql6, data6 = run_bi_query(
    "What is the distribution of payment methods showing count and percentage?",
    "6"
)
results.append(("Payment Distribution", success, time6))

# ===========================================================================
# QUERY 7: Order Status Distribution
# ===========================================================================

success, time7, sql7, data7 = run_bi_query(
    "What is the distribution of order statuses?",
    "7"
)
results.append(("Order Status Distribution", success, time7))

# ===========================================================================
# QUERY 8: Sales by Category and Country
# ===========================================================================

success, time8, sql8, data8 = run_bi_query(
    "Show me total sales broken down by product category and shipping country",
    "8"
)
results.append(("Sales by Category & Country", success, time8))

# ===========================================================================
# QUERY 9: High-Value Orders Analysis
# ===========================================================================

success, time9, sql9, data9 = run_bi_query(
    "Show me orders with total amount greater than average order value",
    "9"
)
results.append(("High-Value Orders", success, time9))

# ===========================================================================
# QUERY 10: Customer Purchase Analysis
# ===========================================================================

success, time10, sql10, data10 = run_bi_query(
    "Which customers have the highest total purchase amounts?",
    "10"
)
results.append(("Top Customers", success, time10))

# ===========================================================================
# QUERY 11: Product Performance Matrix
# ===========================================================================

success, time11, sql11, data11 = run_bi_query(
    "For each product, show total quantity sold, total revenue, and average unit price",
    "11"
)
results.append(("Product Performance", success, time11))

# ===========================================================================
# QUERY 12: Category Performance Comparison
# ===========================================================================

success, time12, sql12, data12 = run_bi_query(
    "Compare product categories by total orders, total revenue, and average order value",
    "12"
)
results.append(("Category Comparison", success, time12))

# ===========================================================================
# SUMMARY
# ===========================================================================

print("\n\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

total_tests = len(results)
passed_tests = sum(1 for _, success, _ in results if success)
failed_tests = total_tests - passed_tests

print(f"\nTotal Tests: {total_tests}")
print(f"Passed: {passed_tests}")
print(f"Failed: {failed_tests}")
print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")

successful_times = [t for _, success, t in results if success]
if successful_times:
    print(f"\nAverage Response Time: {sum(successful_times)/len(successful_times):.2f}s")
    print(f"Fastest Query: {min(successful_times):.2f}s")
    print(f"Slowest Query: {max(successful_times):.2f}s")

print("\n" + "="*80)
print("DETAILED RESULTS")
print("="*80)

for i, (name, success, elapsed) in enumerate(results, 1):
    status = "PASS" if success else "FAIL"
    print(f"{i:2d}. [{status:4s}] {name:35s} - {elapsed:5.2f}s")

print("="*80)

# Additional Analysis
print("\n" + "="*80)
print("BUSINESS INSIGHTS FROM RESULTS")
print("="*80)

if data2 and len(data2) > 0:
    print("\nTOP REVENUE CATEGORIES:")
    for i, row in enumerate(data2[:5], 1):
        cat = row.get('PRODUCT_CATEGORY', 'N/A')
        rev = row.get('TOTAL_REVENUE', row.get('SUM("TOTAL_AMOUNT")', 0))
        print(f"  {i}. {cat}: ${rev:,.0f}")

if data5 and len(data5) > 0:
    print("\nAVERAGE ORDER VALUE BY COUNTRY:")
    sorted_aov = sorted(data5, key=lambda x: float(x.get('AVERAGE_ORDER_VALUE', x.get('AVG("TOTAL_AMOUNT")', 0))), reverse=True)
    for i, row in enumerate(sorted_aov[:5], 1):
        country = row.get('SHIPPING_COUNTRY', 'N/A')
        aov = row.get('AVERAGE_ORDER_VALUE', row.get('AVG("TOTAL_AMOUNT")', 0))
        print(f"  {i}. {country}: ${float(aov):.2f}")

if data6 and len(data6) > 0:
    print("\nPAYMENT METHOD DISTRIBUTION:")
    for row in data6:
        method = row.get('PAYMENT_METHOD', 'N/A')
        count = row.get('ORDER_COUNT', row.get('COUNT("ORDER_ID")', 0))
        pct = row.get('PERCENTAGE', 0)
        if isinstance(pct, (int, float)):
            print(f"  {method}: {count} orders ({pct:.1f}%)")
        else:
            print(f"  {method}: {count} orders")

print("\n" + "="*80)

"""
LEVEL 1: DESCRIPTIVE ANALYTICS TEST
Testing "What happened?" queries with H2SQL
"""
import requests
import json
import time

BASE_URL = "http://localhost:11901/h2s/data-upload"
ORACLE_PROJECT_ID = 23

def query(question, desc):
    """Execute query and return results"""
    print(f"\n{'='*80}")
    print(f"QUERY: {desc}")
    print(f"{'='*80}")
    print(f"Question: {question}")

    start = time.time()
    response = requests.post(
        f"{BASE_URL}/executequey",
        json={"project_id": ORACLE_PROJECT_ID, "question": question},
        timeout=300
    )
    elapsed = time.time() - start

    status = "[OK]" if response.status_code == 200 else "[FAIL]"
    print(f"\n{status} Status: {response.status_code} | Time: {elapsed:.2f}s")

    if response.status_code == 200:
        result = response.json()
        sql = result.get('llm_generated_sql', '')
        data = result.get('db_result', [])

        print(f"\n[SQL]:")
        for line in sql.split('\n'):
            print(f"  {line}")

        print(f"\n[RESULTS]: {len(data)} rows")
        for i, row in enumerate(data[:15], 1):
            print(f"  {i:2d}. {row}")

        if len(data) > 15:
            print(f"  ... and {len(data) - 15} more rows")

        return True, elapsed, data
    else:
        try:
            print(f"\n[ERROR]: {response.json().get('detail', response.text)[:200]}")
        except:
            print(f"\n[ERROR]: {response.text[:200]}")
        return False, elapsed, None

print("="*80)
print("LEVEL 1: DESCRIPTIVE ANALYTICS")
print("="*80)
print("Database: Oracle TAQDB")
print("Model: Llama-4-Scout via OpenRouter")
print("Focus: 'What happened?' - totals, counts, averages")
print("="*80)

results = []

# =============================================================================
# SECTION 1: OVERALL SALES METRICS
# =============================================================================

print("\n\n" + "="*80)
print("SECTION 1: OVERALL SALES METRICS")
print("="*80)

# Q1.1: Total sales, orders, quantity overall
success, time1, data1 = query(
    "What is the total sales amount, total number of orders, and total quantity sold?",
    "Q1.1 - Overall Totals"
)
results.append(("Overall Totals", success, time1))

# Q1.2: Totals by region
success, time2, data2 = query(
    "What is the total sales, total orders, and total quantity sold by shipping country?",
    "Q1.2 - Totals by Region"
)
results.append(("Totals by Region", success, time2))

# =============================================================================
# SECTION 2: PRODUCT & CATEGORY PERFORMANCE
# =============================================================================

print("\n\n" + "="*80)
print("SECTION 2: PRODUCT & CATEGORY PERFORMANCE")
print("="*80)

# Q2.1: Revenue by category
success, time3, data3 = query(
    "Which product categories generated the highest revenue?",
    "Q2.1 - Revenue by Category"
)
results.append(("Revenue by Category", success, time3))

# Q2.2: Top 10 by quantity
success, time4, data4 = query(
    "What are the top 10 best-selling products by quantity?",
    "Q2.2 - Top 10 by Quantity"
)
results.append(("Top 10 by Quantity", success, time4))

# Q2.3: Top 10 by revenue
success, time5, data5 = query(
    "What are the top 10 best-selling products by total revenue?",
    "Q2.3 - Top 10 by Revenue"
)
results.append(("Top 10 by Revenue", success, time5))

# =============================================================================
# SECTION 3: AVERAGE ORDER VALUE ANALYSIS
# =============================================================================

print("\n\n" + "="*80)
print("SECTION 3: AVERAGE ORDER VALUE (AOV) ANALYSIS")
print("="*80)

# Q3.1: AOV by country
success, time6, data6 = query(
    "What is the average order value by shipping country?",
    "Q3.1 - AOV by Country"
)
results.append(("AOV by Country", success, time6))

# Q3.2: AOV by category
success, time7, data7 = query(
    "What is the average order value by product category?",
    "Q3.2 - AOV by Category"
)
results.append(("AOV by Category", success, time7))

# =============================================================================
# SECTION 4: PAYMENT & ORDER DISTRIBUTION
# =============================================================================

print("\n\n" + "="*80)
print("SECTION 4: PAYMENT & ORDER DISTRIBUTION")
print("="*80)

# Q4.1: Payment method distribution
success, time8, data8 = query(
    "What is the distribution of payment methods with count and percentage?",
    "Q4.1 - Payment Distribution"
)
results.append(("Payment Distribution", success, time8))

# Q4.2: Order status distribution
success, time9, data9 = query(
    "What is the count of orders by order status?",
    "Q4.2 - Order Status"
)
results.append(("Order Status", success, time9))

# =============================================================================
# SECTION 5: CUSTOMER ANALYSIS
# =============================================================================

print("\n\n" + "="*80)
print("SECTION 5: CUSTOMER ANALYSIS")
print("="*80)

# Q5.1: Top customers
success, time10, data10 = query(
    "Which customers have the highest total purchase amounts?",
    "Q5.1 - Top Customers"
)
results.append(("Top Customers", success, time10))

# Q5.2: Unique customers count
success, time11, data11 = query(
    "How many unique customers made purchases?",
    "Q5.2 - Unique Customers"
)
results.append(("Unique Customers", success, time11))

# =============================================================================
# SECTION 6: PRODUCT PERFORMANCE MATRIX
# =============================================================================

print("\n\n" + "="*80)
print("SECTION 6: DETAILED PRODUCT PERFORMANCE")
print("="*80)

# Q6.1: Product performance matrix
success, time12, data12 = query(
    "For each product, show quantity sold, revenue, and average price",
    "Q6.1 - Product Matrix"
)
results.append(("Product Matrix", success, time12))

# Q6.2: Category performance comparison
success, time13, data13 = query(
    "Compare categories by total orders, revenue, and average order value",
    "Q6.2 - Category Comparison"
)
results.append(("Category Comparison", success, time13))

# =============================================================================
# SUMMARY & REPORT GENERATION
# =============================================================================

print("\n\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

total = len(results)
passed = sum(1 for _, s, _ in results if s)
failed = total - passed

print(f"\nTotal Queries: {total}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Success Rate: {passed/total*100:.1f}%")

times = [t for _, s, t in results if s]
if times:
    print(f"\nAverage Time: {sum(times)/len(times):.2f}s")
    print(f"Fastest: {min(times):.2f}s")
    print(f"Slowest: {max(times):.2f}s")

print("\n" + "="*80)
print("DETAILED RESULTS")
print("="*80)

for i, (name, success, elapsed) in enumerate(results, 1):
    status = "PASS" if success else "FAIL"
    print(f"{i:2d}. [{status:4s}] {name:30s} - {elapsed:5.2f}s")

# =============================================================================
# BUSINESS INSIGHTS REPORT
# =============================================================================

print("\n\n" + "="*80)
print("DESCRIPTIVE ANALYTICS REPORT")
print("="*80)

if data1:
    print("\n1. OVERALL BUSINESS METRICS:")
    for row in data1:
        total_sales = row.get('TOTAL_SALES', row.get('SUM("TOTAL_AMOUNT")', 0))
        total_orders = row.get('TOTAL_ORDERS', row.get('COUNT("ORDER_ID")', 0))
        total_qty = row.get('TOTAL_QUANTITY', row.get('SUM("QUANTITY")', 0))
        print(f"   - Total Sales: ${total_sales:,}")
        print(f"   - Total Orders: {total_orders}")
        print(f"   - Total Quantity Sold: {total_qty} units")

if data2 and len(data2) > 0:
    print("\n2. REGIONAL PERFORMANCE (Top 5):")
    sorted_regions = sorted(
        data2,
        key=lambda x: x.get('TOTAL_SALES', x.get('SUM("TOTAL_AMOUNT")', 0)),
        reverse=True
    )
    for i, row in enumerate(sorted_regions[:5], 1):
        country = row.get('SHIPPING_COUNTRY', 'N/A')
        sales = row.get('TOTAL_SALES', row.get('SUM("TOTAL_AMOUNT")', 0))
        orders = row.get('TOTAL_ORDERS', row.get('COUNT("ORDER_ID")', 0))
        print(f"   {i}. {country}: ${sales:,} ({orders} orders)")

if data3:
    print("\n3. TOP REVENUE CATEGORIES:")
    for i, row in enumerate(data3[:5], 1):
        cat = row.get('PRODUCT_CATEGORY', 'N/A')
        rev = row.get('TOTAL_REVENUE', row.get('SUM("TOTAL_AMOUNT")', 0))
        print(f"   {i}. {cat}: ${rev:,}")

if data5:
    print("\n4. TOP 5 REVENUE-GENERATING PRODUCTS:")
    for i, row in enumerate(data5[:5], 1):
        product = row.get('PRODUCT_NAME', 'N/A')
        rev = row.get('TOTAL_REVENUE', row.get('SUM("TOTAL_AMOUNT")', 0))
        print(f"   {i}. {product}: ${rev:,}")

if data6 and len(data6) > 0:
    print("\n5. AVERAGE ORDER VALUE BY COUNTRY (Top 5):")
    sorted_aov = sorted(
        data6,
        key=lambda x: float(x.get('AVG_ORDER_VALUE', x.get('AVG("TOTAL_AMOUNT")', 0))),
        reverse=True
    )
    for i, row in enumerate(sorted_aov[:5], 1):
        country = row.get('SHIPPING_COUNTRY', 'N/A')
        aov = float(row.get('AVG_ORDER_VALUE', row.get('AVG("TOTAL_AMOUNT")', 0)))
        print(f"   {i}. {country}: ${aov:.2f}")

if data8:
    print("\n6. PAYMENT METHOD DISTRIBUTION:")
    total_payments = sum(
        row.get('COUNT_PAYMENT_METHOD', row.get('COUNT("PAYMENT_METHOD")', 0))
        for row in data8
    )
    for row in data8:
        method = row.get('PAYMENT_METHOD', 'N/A')
        count = row.get('COUNT_PAYMENT_METHOD', row.get('COUNT("PAYMENT_METHOD")', 0))
        pct = (count / total_payments * 100) if total_payments > 0 else 0
        print(f"   - {method}: {count} orders ({pct:.1f}%)")

print("\n" + "="*80)
print("END OF LEVEL 1 DESCRIPTIVE ANALYTICS REPORT")
print("="*80)

"""
Complex Analytical Questions - Testable with Current Data
Testing H2SQL's capability to generate advanced SQL queries
"""
import requests
import json
import time

BASE_URL = "http://localhost:11901/h2s/data-upload"
ORACLE_PROJECT_ID = 23

def test_query(question, category, test_id):
    """Execute complex query and display results"""
    print(f"\n{'='*80}")
    print(f"TEST {test_id}: {category}")
    print(f"{'='*80}")
    print(f"Question: {question}")

    start = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/executequey",
            json={"project_id": ORACLE_PROJECT_ID, "question": question},
            timeout=300
        )
        elapsed = time.time() - start

        status = "[PASS]" if response.status_code == 200 else "[FAIL]"
        print(f"\n{status} Status: {response.status_code} | Time: {elapsed:.2f}s")

        if response.status_code == 200:
            result = response.json()
            sql = result.get('llm_generated_sql', '')
            data = result.get('db_result', [])

            print(f"\n[SQL GENERATED]:")
            for line in sql.split('\n'):
                print(f"  {line}")

            print(f"\n[RESULTS]: {len(data)} rows")
            for i, row in enumerate(data[:10], 1):
                print(f"  {i:2d}. {row}")

            if len(data) > 10:
                print(f"  ... and {len(data) - 10} more rows")

            return True, elapsed, sql, data
        else:
            error_msg = response.json().get('detail', response.text) if response.status_code != 500 else response.text
            print(f"\n[ERROR]: {error_msg[:300]}")
            return False, elapsed, None, None

    except Exception as e:
        elapsed = time.time() - start
        print(f"\n[EXCEPTION]: {str(e)[:200]}")
        return False, elapsed, None, None


print("="*80)
print("COMPLEX ANALYTICAL QUERIES - H2SQL CAPABILITY TEST")
print("="*80)
print("Database: Oracle TAQDB")
print("Model: Llama-4-Scout via OpenRouter")
print("Test Data: 50 e-commerce orders")
print("="*80)

results = []

# =============================================================================
# CATEGORY 1: REVENUE & SALES ANALYSIS
# =============================================================================

print("\n\n" + "="*80)
print("CATEGORY 1: REVENUE & SALES VOLUME ANALYSIS")
print("="*80)

# Q1: Price elasticity simulation
success, t1, sql1, data1 = test_query(
    "What is the relationship between unit price and quantity sold for each product category? Show category, average price, total quantity, and total revenue.",
    "Price-Volume Relationship",
    "1.1"
)
results.append(("Price-Volume Analysis", success, t1))

# Q2: High volume low margin products (without actual margin data, use revenue/qty ratio)
success, t2, sql2, data2 = test_query(
    "Which products have high sales quantity but low revenue per unit? Show products where quantity sold is above average but average price is below category average.",
    "High Volume Low Price Products",
    "1.2"
)
results.append(("High Vol Low Price", success, t2))

# Q3: Revenue concentration
success, t3, sql3, data3 = test_query(
    "What percentage of total revenue does each product contribute? Show product name, total revenue, and percentage of overall revenue, ordered by revenue descending.",
    "Revenue Concentration",
    "1.3"
)
results.append(("Revenue Contribution %", success, t3))

# =============================================================================
# CATEGORY 2: CUSTOMER SEGMENTATION & VALUE
# =============================================================================

print("\n\n" + "="*80)
print("CATEGORY 2: CUSTOMER SEGMENTATION & LIFETIME VALUE")
print("="*80)

# Q4: RFM-style analysis (Recency, Frequency, Monetary)
success, t4, sql4, data4 = test_query(
    "For each customer, calculate total purchase amount, number of orders, and most recent order date. Order by total purchase descending.",
    "Customer RFM Analysis",
    "2.1"
)
results.append(("Customer RFM", success, t4))

# Q5: High frequency low AOV customers
success, t5, sql5, data5 = test_query(
    "Which customers have more than 2 orders but average order value below the overall average? Show customer name, order count, total spend, and average order value.",
    "High Frequency Low AOV",
    "2.2"
)
results.append(("High Freq Low AOV", success, t5))

# Q6: Pareto analysis (80/20 rule)
success, t6, sql6, data6 = test_query(
    "Show the top 20% of customers by revenue. Calculate each customer's total revenue and percentage contribution to overall revenue.",
    "Pareto 80/20 Analysis",
    "2.3"
)
results.append(("Pareto Analysis", success, t6))

# =============================================================================
# CATEGORY 3: REGIONAL & CHANNEL PERFORMANCE
# =============================================================================

print("\n\n" + "="*80)
print("CATEGORY 3: REGIONAL PERFORMANCE ANALYSIS")
print("="*80)

# Q7: Regional profitability (using revenue as proxy)
success, t7, sql7, data7 = test_query(
    "Compare regions by total revenue, number of orders, average order value, and revenue per order. Which regions show highest efficiency?",
    "Regional Efficiency",
    "3.1"
)
results.append(("Regional Efficiency", success, t7))

# Q8: Underperforming regions
success, t8, sql8, data8 = test_query(
    "Which regions have order counts above average but revenue per order below average? Show region, order count, total revenue, and AOV.",
    "Underperforming Regions",
    "3.2"
)
results.append(("Underperforming Regions", success, t8))

# Q9: City-level performance
success, t9, sql9, data9 = test_query(
    "What are the top 10 cities by total revenue? Include order count and average order value for each city.",
    "Top Cities Performance",
    "3.3"
)
results.append(("City Performance", success, t9))

# =============================================================================
# CATEGORY 4: PRODUCT & CATEGORY INSIGHTS
# =============================================================================

print("\n\n" + "="*80)
print("CATEGORY 4: PRODUCT & CATEGORY INSIGHTS")
print("="*80)

# Q10: Category concentration
success, t10, sql10, data10 = test_query(
    "For each category, show how many products contribute to 80% of category revenue. List all products with their revenue contribution percentage within their category.",
    "Category Concentration Ratio",
    "4.1"
)
results.append(("Category Concentration", success, t10))

# Q11: Cross-category purchase patterns
success, t11, sql11, data11 = test_query(
    "Show product categories purchased together. For each category, show what other categories customers also bought in the same order.",
    "Cross-Category Purchases",
    "4.2"
)
results.append(("Cross-Category", success, t11))

# Q12: Product performance matrix
success, t12, sql12, data12 = test_query(
    "Create a product performance matrix showing for each product: total orders, total quantity, total revenue, average price, and revenue per order.",
    "Product Performance Matrix",
    "4.3"
)
results.append(("Product Matrix", success, t12))

# =============================================================================
# CATEGORY 5: PAYMENT & ORDER BEHAVIOR
# =============================================================================

print("\n\n" + "="*80)
print("CATEGORY 5: PAYMENT METHOD & ORDER BEHAVIOR")
print("="*80)

# Q13: Payment method correlation with AOV
success, t13, sql13, data13 = test_query(
    "How does average order value vary by payment method? Show payment method, order count, total revenue, and average order value, ranked by AOV.",
    "Payment Method vs AOV",
    "5.1"
)
results.append(("Payment vs AOV", success, t13))

# Q14: Payment preference by region
success, t14, sql14, data14 = test_query(
    "What is the distribution of payment methods by region? Show region, payment method, order count, and percentage within each region.",
    "Regional Payment Preferences",
    "5.2"
)
results.append(("Regional Payment Pref", success, t14))

# Q15: Order status impact
success, t15, sql15, data15 = test_query(
    "Compare average order value and total revenue across different order statuses. Which status shows highest average value?",
    "Order Status Impact",
    "5.3"
)
results.append(("Order Status Analysis", success, t15))

# =============================================================================
# CATEGORY 6: ADVANCED STATISTICAL QUERIES
# =============================================================================

print("\n\n" + "="*80)
print("CATEGORY 6: STATISTICAL & CORRELATION ANALYSIS")
print("="*80)

# Q16: Price variance by category
success, t16, sql16, data16 = test_query(
    "For each category, calculate minimum, maximum, average, and standard deviation of unit prices. Which categories have highest price variance?",
    "Price Variance by Category",
    "6.1"
)
results.append(("Price Variance", success, t16))

# Q17: Quantity distribution
success, t17, sql17, data17 = test_query(
    "Show the distribution of order quantities. How many orders have 1 unit, 2 units, 3+ units? Include percentage of total orders.",
    "Quantity Distribution",
    "6.2"
)
results.append(("Quantity Distribution", success, t17))

# Q18: Outlier detection
success, t18, sql18, data18 = test_query(
    "Identify orders with total amount greater than 2 times the average order value. Show these outlier orders with customer, product, and amount details.",
    "Outlier Detection",
    "6.3"
)
results.append(("Outlier Detection", success, t18))

# =============================================================================
# CATEGORY 7: STRATEGIC INSIGHTS
# =============================================================================

print("\n\n" + "="*80)
print("CATEGORY 7: STRATEGIC BUSINESS INSIGHTS")
print("="*80)

# Q19: Region-category optimization
success, t19, sql19, data19 = test_query(
    "Which combination of region and product category generates the highest revenue? Show top 10 region-category pairs with total revenue and order count.",
    "Region-Category Optimization",
    "7.1"
)
results.append(("Region-Category Mix", success, t19))

# Q20: Customer concentration risk
success, t20, sql20, data20 = test_query(
    "Calculate revenue concentration: What percentage of revenue comes from top 10 customers? Show cumulative revenue percentage for top customers.",
    "Customer Concentration Risk",
    "7.2"
)
results.append(("Revenue Concentration", success, t20))

# =============================================================================
# SUMMARY & REPORT
# =============================================================================

print("\n\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

total = len(results)
passed = sum(1 for _, s, _ in results if s)
failed = total - passed

print(f"\nTotal Tests: {total}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Success Rate: {passed/total*100:.1f}%")

times = [t for _, s, t in results if s]
if times:
    print(f"\nAverage Time: {sum(times)/len(times):.2f}s")
    print(f"Fastest: {min(times):.2f}s")
    print(f"Slowest: {max(times):.2f}s")

print("\n" + "="*80)
print("DETAILED RESULTS BY CATEGORY")
print("="*80)

for i, (name, success, elapsed) in enumerate(results, 1):
    status = "PASS" if success else "FAIL"
    print(f"{i:2d}. [{status:4s}] {name:35s} - {elapsed:5.2f}s")

print("\n" + "="*80)
print("H2SQL COMPLEX QUERY CAPABILITY ASSESSMENT")
print("="*80)

print(f"""
TESTED CAPABILITIES:
✓ Price-volume relationship analysis
✓ Customer segmentation (RFM-style)
✓ Pareto analysis (80/20 rule)
✓ Regional performance comparison
✓ Product performance matrices
✓ Cross-category analysis
✓ Payment behavior correlation
✓ Statistical aggregations (min, max, avg, stddev)
✓ Outlier detection
✓ Multi-dimensional grouping
✓ Percentage calculations
✓ Revenue concentration analysis

SUCCESS RATE: {passed}/{total} ({passed/total*100:.1f}%)

LIMITATIONS WITH CURRENT DATA:
- No discount/profit margin data for margin analysis
- No customer demographics (age, gender) for segmentation
- No return/churn data for predictive analysis
- No delivery metrics for operational efficiency
- No campaign/channel data for attribution analysis
- Limited date range for time-series forecasting
""")

print("="*80)

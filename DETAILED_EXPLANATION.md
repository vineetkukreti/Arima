# Complete System Explanation: Product-Customer-Category Forecasting

## Table of Contents
1. [What is Time Series Forecasting?](#what-is-time-series-forecasting)
2. [The 3-Way Combination Concept](#the-3-way-combination-concept)
3. [How the Code Works Step-by-Step](#how-the-code-works-step-by-step)
4. [The 36-Month Forecast Explained](#the-36-month-forecast-explained)
5. [Understanding the Output](#understanding-the-output)

---

## What is Time Series Forecasting?

### The Basic Idea

Imagine you run a store and you've been tracking how many units of "Product_A" you sell to "Customer_001" each month for the past 3 years (36 months). The data might look like:

```
Jan 2021: 150 units
Feb 2021: 165 units
Mar 2021: 180 units
...
Dec 2023: 190 units
```

**Time series forecasting** tries to predict: *"Based on this historical pattern, how many units will I sell in the next 3 years?"*

### ARIMA Model

**ARIMA** = Auto-Regressive Integrated Moving Average

Think of it as a smart algorithm that:
1. **Looks at patterns** in your historical data
2. **Identifies trends** (is it going up? down? stable?)
3. **Detects seasonality** (does January always sell more than July?)
4. **Makes predictions** for future months

It's like having a statistician who studies your past sales and says: "Based on the pattern, next January you'll probably sell around 195 units."

---

## The 3-Way Combination Concept

### Why Combinations?

Your business has:
- **Multiple products** (Product_A, Product_B, Product_C, ...)
- **Multiple customers** (CUST_001, CUST_002, CUST_003, ...)
- **Multiple categories** (Electronics, Hardware, ...)

Different combinations behave **differently**:
- Product_A sells well to CUST_001 in Electronics
- Product_B sells poorly to CUST_002 in Hardware
- Product_C is stable with CUST_003 in Electronics

### The Multiplication

If you have:
- **5 products** (A, B, C, D, E)
- **3 customers** (001, 002, 003)
- **2 categories** (Electronics, Hardware)

**Total combinations** = 5 × 3 × 2 = **30 unique combinations**

### Each Combination is Independent

```
Combination 1: Product_A + CUST_001 + Electronics
  ↓ Has its own sales history
  ↓ Gets its own forecast model
  ↓ Produces its own 36-month prediction

Combination 2: Product_A + CUST_001 + Hardware
  ↓ Different sales history (even though same product & customer!)
  ↓ Gets its own separate model
  ↓ Produces different predictions

... and so on for all 30 combinations
```

### Real Example from Your Test Data

```
Product_A + CUST_001 + Electronics
Historical data (last 36 months):
  2021-01: 150 units
  2021-02: 165 units
  ...
  2023-12: 190 units

Forecast (next 36 months):
  2024-01: 210 units ← Predicted
  2024-02: 224 units ← Predicted
  ...
  2026-12: 254 units ← Predicted
```

---

## How the Code Works Step-by-Step

### Step 1: Data Loading

```python
df = pd.read_excel("your_data.xlsx")
```

**What happens:**
- Reads your Excel file
- Expects columns: Year, Month, Product, CustomerID, Product Category, Quantity

**Your data looks like:**
```
Year  Month  Product    CustomerID  Product Category  Quantity
2021  1      Product_A  CUST_001    Electronics       150
2021  2      Product_A  CUST_001    Electronics       165
2021  1      Product_A  CUST_001    Hardware          80
2021  2      Product_A  CUST_001    Hardware          85
...
```

### Step 2: Creating Time Series (Grouping)

```python
df.groupby(['Product', 'CustomerID', 'Product Category'])
```

**What happens:**
The code **groups** all records with the same 3-dimensional combination.

**Before grouping (raw data):**
```
Product_A, CUST_001, Electronics, 2021-01, 150
Product_A, CUST_001, Electronics, 2021-02, 165
Product_B, CUST_002, Hardware, 2021-01, 200
Product_A, CUST_001, Electronics, 2021-03, 180
...
```

**After grouping:**
```
Group 1: Product_A + CUST_001 + Electronics
  → 2021-01: 150
  → 2021-02: 165
  → 2021-03: 180
  → ... (36 data points)

Group 2: Product_A + CUST_001 + Hardware
  → 2021-01: 80
  → 2021-02: 85
  → ... (36 data points)

... (30 groups total)
```

### Step 3: Creating Time Series Objects

```python
ts_data = group.groupby('Date')['Quantity'].sum()
ts_data.set_index('Date', inplace=True)
ts_data = ts_data.asfreq('MS', fill_value=0)
```

**What happens:**
- Creates a **continuous timeline** starting from Month-Start (MS)
- Fills missing months with 0
- Ensures data is properly indexed by date

**Result:**
```
Date        Quantity
2021-01-01  150
2021-02-01  165
2021-03-01  180
...
2023-12-01  190
```

### Step 4: Training the ARIMA Model (Per Combination)

For **each of the 30 combinations**, the code:

#### 4a. Splits Data (80/20)
```python
train_size = int(len(ts_data) * 0.8)
train = ts_data[:train_size]  # First 80% (29 months)
test = ts_data[train_size:]    # Last 20% (7 months)
```

**Why?**
- **Train**: Learn the pattern from older data
- **Test**: Check if the model can predict recent months accurately

#### 4b. Finds Best ARIMA Parameters

```python
auto_model = auto_arima(
    train,
    max_p=2, max_q=2,
    seasonal=True, m=12
)
```

**What happens:**
- Tries different ARIMA configurations
- Tests which one fits the training data best
- Finds optimal parameters like (1, 0, 1) x (0, 1, 0, 12)

**What do these numbers mean?**
- `(p, d, q)` = Non-seasonal parameters (trend, differencing, error)
- `(P, D, Q, m)` = Seasonal parameters (m=12 means yearly seasonality)

#### 4c. Validates on Test Set

```python
predictions = model.forecast(steps=len(test))
rmse = sqrt(mean_squared_error(test, predictions))
```

**What happens:**
- Predicts the test months (which we already know)
- Compares predictions to actual values
- Calculates error (RMSE = how far off were we?)

**Example:**
```
Actual test data:  [185, 190, 195, 188, 192, 190, 194]
Predicted:         [183, 191, 193, 187, 190, 192, 195]
RMSE: 2.8 (pretty good!)
```

### Step 5: Generating the 36-Month Forecast

```python
model = ARIMA(full_data, order=best_order, seasonal_order=seasonal_order)
fitted_model = model.fit()
forecast_result = fitted_model.get_forecast(steps=36)
```

**What happens:**

1. **Retrain on ALL data** (all 36 historical months)
2. **Generate 36 future predictions**
3. **Calculate confidence intervals** (95% sure it'll be between X and Y)

**Result:**
```
Date        Forecast  Lower_CI  Upper_CI
2024-01-01  210       144       250
2024-02-01  224       163       264
2024-03-01  257       220       297
...
2026-12-01  254       215       287
```

### Step 6: Post-Processing (Cleaning Output)

```python
forecast_df['Forecast'] = forecast_df['Forecast'].clip(lower=0).round(0).astype(int)
```

**What happens:**

**Before:**
```
Forecast: 210.47, -5.23, 1.23e2
```

**After:**
```
Forecast: 210, 0, 123
```

Operations:
- `.clip(lower=0)` → Changes -5.23 to 0 (no negatives)
- `.round(0)` → Changes 210.47 to 210 (no decimals)
- `.astype(int)` → Changes 1.23e2 to 123 (no scientific notation)

### Step 7: Saving Results

For each combination, the code saves:

#### a. Model File (*.pkl)
```
Product_A_CUST_001_Electronics.pkl
```
- The trained ARIMA model
- Can be reloaded later for more forecasts

#### b. Metadata (*.json)
```json
{
  "product": "Product_A",
  "customer_id": "CUST_001",
  "product_category": "Electronics",
  "rmse": 2.8,
  "forecast_months": 36,
  "generated_on": "2024-12-19 00:25:00"
}
```

#### c. Forecast Data (Excel/CSV)
Combined file with all forecasts:
```
Product    CustomerID  Category     Date        Forecast
Product_A  CUST_001    Electronics  2024-01-01  210
Product_A  CUST_001    Electronics  2024-02-01  224
...
```

---

## The 36-Month Forecast Explained

### Why 36 Months (3 Years)?

**Business Planning Perspective:**
- **Short-term** (6 months): Too short for strategic planning
- **Medium-term** (1 year): Good for annual budgets
- **Long-term** (3 years): Ideal for:
  - Inventory contracts
  - Production capacity planning
  - Supplier negotiations
  - Market expansion decisions

### How It Works

**Given:**
- 36 months of historical data (Jan 2021 - Dec 2023)

**Process:**
1. Model learns pattern from 36 historical months
2. Projects pattern forward for 36 future months
3. Each future month builds on previous predictions

**Visual Timeline:**
```
<---- HISTORICAL (Training) ----><------- FORECAST (Prediction) ------->
2021  2022  2023                 2024     2025     2026
[====36 months of data====]      [====36 months to predict====]
                                 ↑
                            Start predicting here
```

### Confidence Decreases Over Time

**Important concept:**
- **Month 1 (Jan 2024)**: Very confident
- **Month 12 (Dec 2024)**: Still confident
- **Month 24 (Dec 2025)**: Moderate confidence
- **Month 36 (Dec 2026)**: Less confident

**This is shown in confidence intervals:**
```
Month 1:  Forecast: 210  CI: [144-250]  (range: 106)
Month 12: Forecast: 225  CI: [140-280]  (range: 140)
Month 36: Forecast: 254  CI: [120-350]  (range: 230)
```

The range gets wider = less certain

---

## Understanding the Output

### Excel File Structure

**Sheet 1: Summary**
```
Product    CustomerID  Category     Model   RMSE  Success
Product_A  CUST_001    Electronics  ARIMA   2.8   True
Product_A  CUST_001    Hardware     ARIMA   3.2   True
...
```
- Overview of all 30 combinations
- Model performance metrics
- Success/failure status

**Sheet 2: All_Forecasts**
```
Product    CustomerID  Category     Date        Forecast  Lower_CI  Upper_CI
Product_A  CUST_001    Electronics  2024-01-01  210       144       250
Product_A  CUST_001    Electronics  2024-02-01  224       163       264
...
```
- 30 combinations × 36 months = **1,080 forecast rows**
- Each row is one month's prediction for one combination

### How to Read the Results

**For Product_A + CUST_001 + Electronics:**

```
Historical average (2021-2023): ~175 units/month

Forecast:
  2024 average: ~220 units/month (↑25% growth trend detected)
  2025 average: ~235 units/month (↑7% continued growth)
  2026 average: ~245 units/month (↑4% slowing growth)
```

**Interpretation:**
- Model detected upward trend
- Predicts continued growth but at decreasing rate
- Consider: increasing inventory for this combination

### Total Numbers

```
30 combinations
× 36 months each
= 1,080 total forecast points

Each forecast point is a non-negative integer
representing expected quantity for that month
```

---

## Real-World Usage Example

### Scenario

You're planning for 2024-2026. You need to know:
- How much of each product to stock for each customer
- Which product-customer-category combinations are growing
- Where to allocate resources

### Using the Forecasts

**Step 1: Run the forecast**
```bash
# Parallel processing is enabled by default
uv run python -m src.models.product_customer_forecast \
  --data "data/your_actual_data.xlsx" \
  --workers 8
```

**Step 2: Analyze the output**

Open `consolidated_forecasts.xlsx`:

**Growing combinations (invest more):**
```
Product_A + CUST_001 + Electronics
  2024: 220/mo × 12 = 2,640 units
  → Increase inventory, negotiate bulk supplier deals
```

**Declining combinations (reduce):**
```
Product_C + CUST_003 + Hardware
  2024: 85/mo × 12 = 1,020 units (down from 1,200)
  → Reduce stock, don't renew expensive contracts
```

**Stable combinations (maintain):**
```
Product_B + CUST_002 + Electronics
  2024-2026: ~150/mo consistently
  → Keep current strategy
```

**Step 3: Decision Making**

For each combination, you know:
- **How much to order** (total forecast quantity)
- **When demand peaks** (monthly variation)
- **Confidence level** (wider CI = more risky)

---

## Key Takeaways

1. **3-Way Combinations**: Each unique Product + Customer + Category gets its own independent forecast

2. **36 Months**: 3 years of predictions based on 3 years of history

3. **ARIMA Magic**: Statistical model that learns from historical patterns to predict future

4. **Clean Output**: Always non-negative integers (0 or positive whole numbers)

5. **Confidence Intervals**: Upper/lower bounds show the uncertainty range

6. **Parallel Processing**: For 2000+ combinations, use `--parallel` to finish in ~30 minutes instead of 4+ hours

7. **Production Ready**: All outputs are formatted for business use (Excel, CSV, visualizations)

This system transforms raw historical sales data into actionable 3-year forecasts for every Product-Customer-Category combination in your business! 🎯

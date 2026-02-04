# 📘 Complete Code Explanation

## Overview

This document provides a detailed, line-by-line explanation of the optimizer scripts:
- **`g_optimiser_script.py`** - The main optimization engine
- **`run_optimizer_g.py`** - The runner script that uses the optimizer

---

## **1. Main Focus: `g_optimiser_script.py`**

This script uses **Gurobi** (a powerful optimization solver) to solve a **product distribution problem**. Think of it like a smart planner that decides:
- **Which batch** of products to send to which customer
- **When** to send them
- How to minimize costs (switching batches and wasting expired products)

---

### **🔹 Lines 1-8: Imports**

```python
# optimizer_calculator.py
# -*- coding: utf-8 -*-
import os
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
```

**What's happening:**
- `os`: To read environment variables (like Gurobi license credentials)
- `pandas`: To work with data in tables (Excel-like format)
- `gurobipy`: The Gurobi optimizer library
- `GRB`: Constants used by Gurobi (like `GRB.BINARY` for yes/no decisions)

---

### **🔹 Lines 9-21: Class Definition**

```python
class ProductDistribution:
```

**What's this?**
A **class** is like a blueprint. This creates an optimizer tool that you can use multiple times with different data.

The **docstring** (lines 10-20) explains:
- It uses **MILP** (Mixed Integer Linear Programming) - a math technique to find the best solution
- **WLS** = Web License Service (cloud-based Gurobi license)
- Main constraint: Satisfy exact customer demand for each product each month

---

### **🔹 Lines 22-74: `__init__` Method - Setting Up**

This is the **initialization function** - it sets up all the data when you create an optimizer.

**Parameters explained simply:**

| Parameter | What it means |
|-----------|---------------|
| `customer` | List of customer names (e.g., ["Cust_A", "Cust_B"]) |
| `product` | List of product names (e.g., ["Prod_1", "Prod_2"]) |
| `months` | How many months to plan for (e.g., 12) |
| `inventory_df` | Table showing available product batches, when they're ready, and when they expire |
| `demand_forecast` | Table showing what each customer needs each month |
| `penalty` | Cost of switching from one batch to another (default: $100) |
| `scrap_cost_per_unit` | Cost if a product expires unused (default: $1 per unit) |
| `max_switches_per_year` | Limit how many times you can switch batches in a year |
| `month_years` | Maps each month to a year (needed for yearly limits) |

**Line-by-line breakdown:**

**Lines 43-47: Convert inputs to proper data types and make copies**
```python
self.customer = list(customer)  # Store customer list
self.product = list(product)     # Store product list
self.months = int(months)        # Ensure months is an integer
self.inventory_df = inventory_df.copy()  # Make a copy of inventory data
self.demand_forecast = demand_forecast.copy()  # Make a copy of demand data
```
- `.copy()` → Make a copy of data so we don't accidentally modify the original

**Lines 48-52: Store other parameters**
```python
self.lot_sizes = lot_sizes
self.penalty = float(penalty)
self.scrap_cost_per_unit = float(scrap_cost_per_unit)
self.gurobi_params = gurobi_params or {}
self.verbose = bool(verbose)
```

**Lines 54-67: WLS (Gurobi Cloud License) settings**
```python
self.use_wls = bool(use_wls)
self.wls_access_id = (
    wls_access_id if wls_access_id is not None else os.environ.get("GUROBI_WLSACCESSID")
)
self.wls_secret = (
    wls_secret if wls_secret is not None else os.environ.get("GUROBI_WLSSECRET")
)
```
- Check if you provided WLS credentials, or read them from environment variables
- `os.environ.get()` → Gets values like passwords from your computer's environment

**Lines 69-71: Yearly switch caps**
```python
self.max_switches_per_year = max_switches_per_year
self.month_years = list(month_years) if month_years is not None else None
```
- Store the rules about how many times you can switch batches per year

**Line 74: Initialize results storage**
```python
self.best_distribution = {}
```

---

### **🔹 Lines 76-96: `_build_env` Method - Setting Up Gurobi**

```python
def _build_env(self):
```

**Purpose:** Create the Gurobi environment (like starting the optimizer engine)

**How it works:**

**1. If using WLS** (lines 77-95):
```python
if self.use_wls:
    missing = []
    if not self.wls_access_id:
        missing.append("GUROBI_WLSACCESSID / wls_access_id")
    if not self.wls_secret:
        missing.append("GUROBI_WLSSECRET / wls_secret")
    if self.wls_license_id is None:
        missing.append("GUROBI_LICENSEID / wls_license_id")
```
- Check if you have all 3 required credentials:
  - `GUROBI_WLSACCESSID` (username)
  - `GUROBI_WLSSECRET` (password)
  - `GUROBI_LICENSEID` (license number)
- If anything is missing, **throw an error**

```python
    env = gp.Env(empty=True)
    env.setParam("WLSAccessID", self.wls_access_id)
    env.setParam("WLSSecret", self.wls_secret)
    env.setParam("LicenseID", self.wls_license_id)
    env.start()
    return env
```
- Create an empty environment
- Set the WLS parameters
- Start the environment

**2. If not using WLS** (line 96):
```python
return gp.Env()
```
- Just create a regular local Gurobi environment

---

### **🔹 Lines 98-113: `_resolve_switch_cap` - Figure Out Switch Limits**

```python
def _resolve_switch_cap(self, c, y):
```

**Purpose:** For a given customer `c` and year `y`, find the maximum number of allowed batch switches.

**Logic:**
```python
cap = self.max_switches_per_year
if cap is None:
    return None
```
- If `max_switches_per_year` is `None` → No limit (return `None`)

```python
if isinstance(cap, int):
    return cap
```
- If it's an **integer** (e.g., 5) → Same limit for everyone

```python
if isinstance(cap, dict):
    v = cap.get(c, None)
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, dict):
        return v.get(y, None)
```
- If it's a **dictionary** → Can have different limits per customer or per customer-year

**Example:**
```python
max_switches_per_year = {"Cust_A": 3, "Cust_B": {"2024": 2, "2025": 4}}
```
- `Cust_A` can switch max 3 times per year
- `Cust_B` can switch 2 times in 2024, 4 times in 2025

---

### **🔹 Lines 115-340: `optimize_distribution` - THE MAIN OPTIMIZATION**

This is the **heart of the script** where all the magic happens!

---

#### **📍 Step 1: Prepare Data (Lines 116-167)**

**Lines 116-119: Define sets**
```python
C = self.customer  # List of customers
P = self.product   # List of products
M = list(range(self.months))  # [0, 1, 2, ..., months-1]
```

**Lines 121-130: Handle yearly switch caps**
```python
if self.max_switches_per_year is not None:
    if self.month_years is None or len(self.month_years) != self.months:
        raise ValueError(
            "month_years must be provided (list[int] of length `months`) "
            "when max_switches_per_year is set."
        )
    YEARS = sorted(set(self.month_years))
else:
    YEARS = []
```
- If yearly limits are set, ensure `month_years` is provided
- Extract the list of unique years

**Lines 132-135: Create batch list**
```python
inv = self.inventory_df[self.inventory_df["product"].isin(P)].copy()
B_real = sorted(inv["batch"].unique().tolist())  # Real batches from inventory
FUTURE = "FUTURE_MASTER_BATCH"  # Imaginary unlimited batch
B = B_real + [FUTURE]  # All batches (real + future)
```

**Why "FUTURE_MASTER_BATCH"?**
- It's a **backup** batch that never runs out
- Acts like ordering new inventory
- Available from month 0, never expires
- Ensures the problem always has a solution

**Lines 138-146: Build demand dictionary**
```python
df = self.demand_forecast[
    self.demand_forecast["customer"].isin(C)
    & self.demand_forecast["product"].isin(P)
    & self.demand_forecast["month_index"].isin(M)
].copy()
D = {
    (r["customer"], r["product"], int(r["month_index"])): float(r["quantity"])
    for _, r in df.iterrows()
}
```
Creates: `D = {(customer, product, month): quantity}`

Example: `D[("Cust_A", "Prod_1", 3)] = 100` means "Customer A needs 100 units of Product 1 in month 3"

**Lines 148-152: Activity flag**
```python
D_any = {(c, m): 0.0 for c in C for m in M}
for (c, p, m), q in D.items():
    D_any[(c, m)] += q
D_active = {(c, m): 1 if D_any[(c, m)] > 1e-9 else 0 for c in C for m in M}
```
`D_active[(c, m)] = 1` if customer c needs anything in month m, else 0

**Lines 155-167: Inventory maps**
```python
qty_bp, avail_bp, exp_bp, has_bp = {}, {}, {}, set()
for _, r in inv.iterrows():
    b, p = r["batch"], r["product"]
    qty_bp[(b, p)] = float(r["quantity"])
    avail_bp[(b, p)] = int(r["available_month_index"])
    exp_bp[(b, p)] = int(r["expiry_month_index"])
    has_bp.add((b, p))

# FUTURE has all products, available from 0, expires after horizon
for p in P:
    has_bp.add((FUTURE, p))
    avail_bp[(FUTURE, p)] = 0
    exp_bp[(FUTURE, p)] = self.months + 1
```

Create dictionaries:
- `qty_bp`: How many units in each batch
- `avail_bp`: When each batch becomes available
- `exp_bp`: When each batch expires
- `has_bp`: Which (batch, product) combinations exist

---

#### **📍 Step 2: Build the Optimization Model (Lines 169-176)**

```python
env = self._build_env()
try:
    m = gp.Model("product_distribution_gurobi_wls", env=env)
    if not self.verbose:
        m.Params.OutputFlag = 0
    for k, v in self.gurobi_params.items():
        setattr(m.Params, k, v)
```

Creates the mathematical model. Think of it like setting up a very complex equation.
- If not verbose, suppress Gurobi output
- Apply any custom Gurobi parameters

---

#### **📍 Step 3: Decision Variables (Lines 178-198)**

These are the **unknowns** the optimizer needs to figure out:

**1. `z[c, t, b]` - Master Batch Selection (Line 179)** 
```python
z = m.addVars(((c, t, b) for c in C for t in M for b in B), vtype=GRB.BINARY, name="z")
```
- `z` = binary variable (0 or 1)
- `z[c, t, b] = 1`  →  Customer c uses batch b in month t
- `z[c, t, b] = 0`  →  Customer c does NOT use batch b in month t

**2. `s[c, t, b]` - Switch Indicator (Line 180)**
```python
s = m.addVars(((c, t, b) for c in C for t in M for b in B), vtype=GRB.BINARY, name="s")
```
- `s[c, t, b] = 1`  →  Customer c STARTS using batch b in month t (a switch happened)
- `s[c, t, b] = 0`  →  No switch

**3. `x[c, p, t, b]` - Quantity Allocated (Lines 182-195)**
```python
x_index = []
for c in C:
    for p in P:
        for t in M:
            demand = D.get((c, p, t), 0.0)
            if demand <= 1e-9:
                continue
            for b in B:
                if (b, p) not in has_bp:
                    continue
                if not (avail_bp[(b, p)] <= t < exp_bp[(b, p)]):
                    continue
                x_index.append((c, p, t, b))
x = m.addVars(x_index, lb=0.0, vtype=GRB.CONTINUOUS, name="x")
```
- `x[c, p, t, b]` = continuous number (e.g., 50.5 units)
- How many units of product `p` from batch `b` to send to customer `c` in month `t`

**Smart indexing:** Only create variables where it makes sense:
- Only if there's demand
- Only if the batch has that product
- Only if the batch is available and not expired at that time

**4. `u[b, p]` - Scrap/Waste (Lines 197-198)**
```python
u_index = [(b, p) for (b, p) in qty_bp.keys() if exp_bp[(b, p)] <= (self.months - 1)]
u = m.addVars(u_index, lb=0.0, vtype=GRB.CONTINUOUS, name="u")
```
- `u[b, p]` = continuous number
- How many units of product `p` from batch `b` got wasted (expired before use)

---

#### **📍 Step 4: Constraints - The Rules (Lines 200-261)**

These are the **rules** the solution must follow:

**C1: Exact Demand (Lines 201-209)**
```python
for c in C:
    for p in P:
        for t in M:
            demand = D.get((c, p, t), 0.0)
            if demand <= 1e-9:
                continue
            m.addConstr(gp.quicksum(x.get((c, p, t, b), 0.0) for b in B) == demand,
                        name=f"demand_exact[{c},{p},{t}]")
```
**Formula:** `sum of x[c, p, t, b] across all batches == demand`

**Plain English:** The total amount sent must exactly match what the customer needs.

**C2: One Master Batch (Lines 211-215)**
```python
for c in C:
    for t in M:
        m.addConstr(gp.quicksum(z[c, t, b] for b in B) == D_active[(c, t)],
                    name=f"one_batch[{c},{t}]")
```
**Formula:** `sum of z[c, t, b] across all batches == 1` (if customer is active)

**Plain English:** Each customer uses exactly ONE batch per month (can't mix batches).

**C3: Link Quantity to Batch (Lines 217-221)**
```python
for (c, p, t, b) in x_index:
    demand = D[(c, p, t)]
    m.addConstr(x[c, p, t, b] <= demand * z[c, t, b],
                name=f"x_link[{c},{p},{t},{b}]")
```
**Formula:** `x[c, p, t, b] <= demand × z[c, t, b]`

**Plain English:** You can only send products from a batch if that batch is the chosen one for that month.

**C4: Capacity (Lines 223-228)**
```python
for (b, p), qty in qty_bp.items():
    if b == FUTURE:
        continue
    used = gp.quicksum(x.get((c, p, t, b), 0.0) for c in C for t in M)
    m.addConstr(used <= qty, name=f"cap[{b},{p}]")
```
**Formula:** `total used from batch <= available quantity`

**Plain English:** Can't use more than what's in the batch.

**C5: Scrap Calculation (Lines 230-236)**
```python
for (b, p) in u_index:
    qty = qty_bp[(b, p)]
    used_before_exp = gp.quicksum(
        x.get((c, p, t, b), 0.0) for c in C for t in M if t < exp_bp[(b, p)]
    )
    m.addConstr(u[(b, p)] >= qty - used_before_exp, name=f"scrap[{b},{p}]")
```
**Formula:** `u[b, p] >= quantity - used_before_expiry`

**Plain English:** Waste = what's left over after the batch expires.

**C6: Switching Logic (Lines 238-247)**
```python
for c in C:
    for b in B:
        m.addConstr(gp.quicksum(s[c, t, b] for t in M) <= 1,
                    name=f"start_le1[{c},{b}]")
        m.addConstr(s[c, 0, b] == z[c, 0, b],
                    name=f"start_t0[{c},{b}]")
        for t in M[1:]:
            m.addConstr(s[c, t, b] >= z[c, t, b] - z[c, t - 1, b],
                        name=f"start_link[{c},{b},{t}]")
```
**Formulas:**
- `sum of s[c, t, b] over all months <= 1` (can only start a batch once)
- `s[c, 0, b] == z[c, 0, b]` (first month)
- `s[c, t, b] >= z[c, t, b] - z[c, t-1, b]` (later months)

**Plain English:** 
- If month 0: starting = chosen
- If later: starting = 1 if you're using this batch now but weren't last month
- No-return constraint: once you stop using a batch, you can't go back to it

**C7: Yearly Switch Caps (Lines 249-261)**
```python
if self.max_switches_per_year is not None:
    for c in C:
        for y in YEARS:
            t_in_year = [t for t in M[1:] if self.month_years[t] == y]
            if not t_in_year:
                continue
            cap_cy = self._resolve_switch_cap(c, y)
            if cap_cy is not None:
                m.addConstr(
                    gp.quicksum(s[c, t, b] for t in t_in_year for b in B) <= cap_cy,
                    name=f"year_switch_cap[{c},{y}]"
                )
```
**Formula:** `sum of switches in a year <= max_switches_per_year`

**Plain English:** Don't switch too many times in one year.

---

#### **📍 Step 5: Objective Function (Lines 263-266)**

```python
switch_cost = gp.quicksum(self.penalty * s[c, t, b] for c in C for t in M[1:] for b in B)
scrap_cost = gp.quicksum(self.scrap_cost_per_unit * u[bp] for bp in u_index)
m.setObjective(switch_cost + scrap_cost, GRB.MINIMIZE)
```

**What does this mean?**
- Find the solution that has the **lowest total cost**
- `switch_cost` = penalty × number of switches (only count switches from month 1 onwards)
- `scrap_cost` = scrap_cost_per_unit × amount wasted

**Example:**
- 3 switches × $100 = $300
- 50 units wasted × $1 = $50
- **Total cost = $350**

---

#### **📍 Step 6: Solve (Lines 268-271)**

```python
m.optimize()
if m.SolCount == 0:
    raise RuntimeError("No feasible solution found by Gurobi (WLS).")
```

This is where Gurobi does its magic! It tries billions of combinations to find the best solution.

If no solution exists (impossible problem), throw an error.

---

#### **📍 Step 7: Extract Results (Lines 273-297)**

Now we read the solution from Gurobi:

```python
best_distribution = {c: {} for c in C}
for c in C:
    for t in M:
        if D_active[(c, t)] == 0:
            continue
        b_star = None
        for b in B:
            if z[c, t, b].X > 0.5:  # .X gets the solution value
                b_star = b
                break
        if b_star is None:
            continue
        month_alloc = {}
        for p in P:
            q_dmd = D.get((c, p, t), 0.0)
            if q_dmd <= 1e-9:
                continue
            val = x.get((c, p, t, b_star), None)
            qty = val.X if val is not None else 0.0
            if qty <= 1e-9 and b_star == "FUTURE_MASTER_BATCH":
                qty = q_dmd
            month_alloc[p] = (b_star, qty)
        best_distribution[c][t] = month_alloc
self.best_distribution = best_distribution
```

**Plain English:** For each customer and month:
1. Find which batch was selected (where `z` = 1)
2. Get the quantities allocated from that batch
3. Store in `best_distribution` dictionary

**Structure:** 
```python
best_distribution = {
    "Customer_A": {
        0: {"Product_1": ("Batch_X", 100), "Product_2": ("Batch_X", 50)},
        1: {"Product_1": ("Batch_Y", 120), "Product_2": ("Batch_Y", 60)},
    },
    ...
}
```

---

#### **📍 Step 8: Cost Report (Lines 299-333)**

Create a detailed breakdown:

**1. Switching costs (Lines 300-311):**
```python
rows = []
total_switch_cost = 0.0
for c in C:
    for t in M[1:]:
        for b in B:
            if s[c, t, b].X > 0.5:
                total_switch_cost += self.penalty
                rows.append({
                    "Customer": c, "Month": t, "BatchStarted": b,
                    "SwitchPenalty": self.penalty,
                    "Batch": "", "Product": "", "ScrapQty": 0.0, "ScrapCost": 0.0
                })
```
For each switch that happened, record:
- Customer, Month, Batch switched to, Penalty cost

**2. Scrap costs (Lines 313-323):**
```python
total_scrap_cost = 0.0
for (b, p) in u_index:
    sq = u[(b, p)].X
    if sq > 1e-9:
        sc = sq * self.scrap_cost_per_unit
        total_scrap_cost += sc
        rows.append({
            "Customer": "", "Month": "", "BatchStarted": "",
            "SwitchPenalty": 0.0, "Batch": b, "Product": p,
            "ScrapQty": sq, "ScrapCost": sc
        })
```
For each batch with waste, record:
- Batch, Product, Quantity scrapped, Cost

**3. Add totals row (Lines 326-331)**
```python
cost_details = pd.DataFrame(rows)
totals = pd.DataFrame([{
    "Customer": "TOTALS", "Month": "", "BatchStarted": "",
    "SwitchPenalty": total_switch_cost, "Batch": "", "Product": "",
    "ScrapQty": "", "ScrapCost": total_scrap_cost
}])
cost_details = pd.concat([cost_details, totals], ignore_index=True)
```

**4. Return results (Line 333)**
```python
return self.best_distribution, cost_details
```

Return both the distribution plan and cost details.

---

#### **📍 Step 9: Cleanup (Lines 335-339)**

```python
finally:
    try:
        env.dispose()
    except Exception:
        print("ERROR!")
```

**Plain English:** Close the Gurobi environment (like turning off the engine).

---

## **2. Supporting Script: `run_optimizer_g.py`**

This is the **runner script** that uses the optimizer on real data.

---

### **🔹 Lines 1-9: Imports and Setup**

```python
"""
Run the optimizer on the large 10K dataset.
"""
import pandas as pd
import sys
import os

sys.path.append(os.getcwd())
from g_optimiser_script import ProductDistribution
```

- Import necessary libraries
- Add current directory to Python path so we can import the optimizer
- Import the `ProductDistribution` class

---

### **🔹 Lines 12-39: `load_large_data` Function**

**Purpose:** Load data from Excel files

```python
def load_large_data():
    """Load the generated 10K dataset"""
    print("Loading large dataset...")
    demand_df = pd.read_excel('data/large_dataset_10k.xlsx')
    inventory_df = pd.read_excel('data/large_inventory.xlsx')
```

Load two Excel files:
1. `demand_df`: Customer demand forecast (10,000 records)
2. `inventory_df`: Available inventory batches

**Lines 18-27: Calculate month_index**
```python
min_year = demand_df['Year'].min()
min_month = demand_df['Month'].min()

demand_df['date_temp'] = pd.to_datetime(
    demand_df['Year'].astype(str) + '-' + demand_df['Month'].astype(str) + '-01'
)
min_date = demand_df['date_temp'].min()

demand_df['month_index'] = (demand_df['Year'] - min_date.year) * 12 + (demand_df['Month'] - min_date.month)
```

Convert Year/Month to a simple index (0, 1, 2, ...)

**Example:** 
- Jan 2024 = 0
- Feb 2024 = 1
- Mar 2024 = 2

**Lines 29-38: Prepare and return data**
```python
demand_forecast = demand_df[['CustomerID', 'Product', 'month_index', 'Quantity']].copy()
demand_forecast.columns = ['customer', 'product', 'month_index', 'quantity']

months_horizon = demand_forecast['month_index'].max() + 1

print(f"Loaded {len(demand_forecast)} demand records")
print(f"Loaded {len(inventory_df)} inventory batches")
print(f"Planning horizon: {months_horizon} months")

return demand_forecast, inventory_df, months_horizon
```

Rename columns to match what the optimizer expects:
- `CustomerID` → `customer`
- `Product` → `product`
- `Quantity` → `quantity`

---

### **🔹 Lines 41-164: `run_optimizer_large` Function**

**Purpose:** Actually run the optimization

**Lines 44-48: Load data**
```python
demand_forecast, inventory_df, months = load_large_data()

customers = demand_forecast['customer'].unique().tolist()
products = demand_forecast['product'].unique().tolist()
```

**Lines 50-54: Display stats**
```python
print(f"\nDataset stats:")
print(f"  Customers: {len(customers)}")
print(f"  Products: {len(products)}")
print(f"  Months: {months}")
print(f"  Total demand records: {len(demand_forecast)}")
```

**Lines 56-91: Limit problem size**
```python
# Due to Gurobi license restrictions, we'll limit the problem size
# Restricted license has ~2000 variable limit

# Reduce to fit within license: 3 customers × 4 products × 12 months = 144 demand points
# This creates approximately 144 × 30 (batches) = ~4320 variables, which should fit
MAX_MONTHS = 12
MAX_CUSTOMERS = 3
MAX_PRODUCTS = 4
```

**Why?** Free Gurobi license has a **2000 variable limit**. So we:
- Take only first 12 months
- Take only first 3 customers
- Take only first 4 products

**Lines 65-83: Apply filters**
```python
if months > MAX_MONTHS:
    print(f"\nLimiting to {MAX_MONTHS} months (from {months}) to fit license constraints...")
    demand_forecast = demand_forecast[demand_forecast['month_index'] < MAX_MONTHS]
    months = MAX_MONTHS

# Limit customers
selected_customers = customers[:MAX_CUSTOMERS]
demand_forecast = demand_forecast[demand_forecast['customer'].isin(selected_customers)]

# Limit products
selected_products = products[:MAX_PRODUCTS]
demand_forecast = demand_forecast[demand_forecast['product'].isin(selected_products)]
    
# Filter inventory
inventory_df = inventory_df[
    (inventory_df['product'].isin(selected_products)) &
    ((inventory_df['available_month_index'] < MAX_MONTHS) | 
     (inventory_df['expiry_month_index'] > 0))
]
```

**Lines 94-97: Check for WLS credentials**
```python
use_wls = 'GUROBI_WLSACCESSID' in os.environ

print(f"\nInitializing optimizer...")
print(f"  Using WLS: {use_wls}")
```

Check if WLS environment variable exists

**Lines 99-110: Create optimizer**
```python
try:
    optimizer = ProductDistribution(
        customer=customers,
        product=products,
        months=months,
        inventory_df=inventory_df,
        demand_forecast=demand_forecast,
        penalty=100.0,
        scrap_cost_per_unit=1.0,
        use_wls=use_wls,
        verbose=True
    )
```

Create an instance of the optimizer with all parameters

**Lines 112-115: Run optimization**
```python
print("\nRunning optimization...")
print("This may take a few minutes for the large dataset...\n")

best_dist, cost_details = optimizer.optimize_distribution()
```

Call the main optimization method

**Lines 117-131: Display results**
```python
print("\n" + "="*60)
print("OPTIMIZATION SUCCESSFUL!")
print("="*60)

# Display summary
totals_row = cost_details[cost_details['Customer'] == 'TOTALS']
if not totals_row.empty:
    switch_cost = totals_row['SwitchPenalty'].values[0]
    scrap_cost = totals_row['ScrapCost'].values[0]
    total_cost = switch_cost + scrap_cost
    
    print(f"\nCost Summary:")
    print(f"  Switching Cost: ${switch_cost:,.2f}")
    print(f"  Scrap Cost:     ${scrap_cost:,.2f}")
    print(f"  Total Cost:     ${total_cost:,.2f}")
```

Show switching cost, scrap cost, and total cost

**Lines 133-151: Save results**
```python
# Save results
output_file = 'optimization_results_10k.xlsx'
cost_details.to_excel(output_file, index=False)
print(f"\nDetailed results saved to: {output_file}")

# Save distribution plan
import json
with open('distribution_plan_10k.json', 'w') as f:
    # Convert to serializable format
    plan_serializable = {}
    for cust, months_data in best_dist.items():
        plan_serializable[cust] = {}
        for month, products in months_data.items():
            plan_serializable[cust][str(month)] = {
                prod: [batch, float(qty)] for prod, (batch, qty) in products.items()
            }
    json.dump(plan_serializable, f, indent=2)

print(f"Distribution plan saved to: distribution_plan_10k.json")
```

Save two files:
1. Cost details to Excel: `optimization_results_10k.xlsx`
2. Distribution plan to JSON: `distribution_plan_10k.json`

**Lines 153-163: Error handling**
```python
except Exception as e:
    print(f"\nOptimization failed: {e}")
    import traceback
    traceback.print_exc()
    
    if "Model too large" in str(e) or "size-limited" in str(e):
        print("\n⚠️  The model is too large for the free Gurobi license.")
        print("   Consider:")
        print("   - Reducing the number of months further")
        print("   - Reducing the number of customers or products")
        print("   - Getting a full Gurobi license")
```

If optimization fails, show helpful error message

---

### **🔹 Lines 165-166: Run the Script**

```python
if __name__ == "__main__":
    run_optimizer_large()
```

**Plain English:** When you run this file directly, execute the `run_optimizer_large()` function.

---

## **📊 Summary: How It All Works Together**

1. **`run_optimizer_g.py`** loads data from Excel files (`large_dataset_10k.xlsx`, `large_inventory.xlsx`)
2. Limits the problem size to fit within Gurobi license constraints
3. Passes data to **`ProductDistribution` class** in `g_optimiser_script.py`
4. The optimizer:
   - Sets up a mathematical model with Gurobi
   - Defines variables (batch choices, quantities, switches, waste)
   - Sets constraints (demand satisfaction, capacity limits, switch logic)
   - Defines objective (minimize switching + scrap costs)
5. Gurobi solves the optimization problem
6. Results are extracted and saved to Excel + JSON files

---

## **🎯 Real-World Analogy**

Imagine you run a **pharmacy** with multiple locations (customers):

- You have **batches** of medicine with expiration dates
- Each branch needs specific medicines each month
- Switching between batches costs time/money (setup costs, cleaning, quality checks)
- Expired medicine is wasted money

**The optimizer finds:**
- Which batch to use for each branch each month
- Minimizes switching costs and waste
- Ensures every branch gets exactly what it needs
- Respects batch capacity and expiration dates
- Limits how many times you switch per year

---

## **🔑 Key Concepts**

### **Decision Variables**
- `z`: Which batch to use (binary: yes/no)
- `s`: When switches occur (binary: yes/no)
- `x`: How much to allocate (continuous: any amount)
- `u`: How much gets wasted (continuous: any amount)

### **Constraints**
1. **Demand**: Must satisfy exact customer needs
2. **One batch**: One master batch per customer per month
3. **Linking**: Can only allocate from chosen batch
4. **Capacity**: Can't exceed batch quantities
5. **Scrap**: Track waste from expired batches
6. **Switching**: Detect and count batch changes
7. **Yearly caps**: Limit switches per year

### **Objective**
Minimize total cost = switching cost + scrap cost

---

## **📈 Understanding the Output**

### **Cost Details (Excel)**
| Customer | Month | BatchStarted | SwitchPenalty | Batch | Product | ScrapQty | ScrapCost |
|----------|-------|--------------|---------------|-------|---------|----------|-----------|
| Cust_A   | 1     | Batch_Y      | 100           |       |         | 0        | 0         |
| Cust_B   | 2     | Batch_Z      | 100           |       |         | 0        | 0         |
|          |       |              | 0             | Batch_X | Prod_1 | 25       | 25        |
| TOTALS   |       |              | 200           |       |         |          | 25        |

**Interpretation:**
- Customer A switched to Batch Y in month 1: Cost $100
- Customer B switched to Batch Z in month 2: Cost $100
- 25 units of Prod_1 from Batch_X expired: Cost $25
- **Total optimization cost: $225**

### **Distribution Plan (JSON)**
```json
{
  "Cust_A": {
    "0": {
      "Prod_1": ["Batch_X", 100.0],
      "Prod_2": ["Batch_X", 50.0]
    },
    "1": {
      "Prod_1": ["Batch_Y", 120.0],
      "Prod_2": ["Batch_Y", 60.0]
    }
  }
}
```

**Interpretation:**
- Month 0: Cust_A gets 100 units of Prod_1 and 50 units of Prod_2 from Batch_X
- Month 1: Cust_A gets 120 units of Prod_1 and 60 units of Prod_2 from Batch_Y (switched!)

---

## **🛠️ Common Customizations**

### **Adjust Costs**
```python
optimizer = ProductDistribution(
    penalty=200.0,           # Higher switching penalty
    scrap_cost_per_unit=5.0  # Higher waste penalty
)
```

### **Set Yearly Switch Limits**
```python
# Same limit for all customers
optimizer = ProductDistribution(
    max_switches_per_year=4,
    month_years=[2024]*12 + [2025]*12  # 24 months total
)

# Different limits per customer
optimizer = ProductDistribution(
    max_switches_per_year={
        "Cust_A": 2,
        "Cust_B": {"2024": 3, "2025": 2}
    },
    month_years=[2024]*12 + [2025]*12
)
```

### **Gurobi Parameters**
```python
optimizer = ProductDistribution(
    gurobi_params={
        "TimeLimit": 300,      # Stop after 5 minutes
        "MIPGap": 0.01,        # Accept 1% from optimal
        "Threads": 4           # Use 4 CPU cores
    }
)
```

---

**Document created:** 2026-01-08  
**Version:** 1.0

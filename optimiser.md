# Gurobi Optimizer Explanation (`confi.py`)

This document provides a detailed explanation of the `confi.py` script, which implements a **Product Distribution Optimizer** using Gurobi.

## 1. What does this script do?

The goal of this optimizer is to decide **which inventory batch** to use to fulfill customer demand for each month, while minimizing costs.

It balances two competing costs:
1.  **Switching Cost**: It costs money (penalty) to switch a customer from one batch to another. You want to keep a customer on the same batch as long as possible.
2.  **Scrap Cost**: Inventory has an expiry date. If you don't use it, you lose money. You want to use up old inventory before it expires.

## 2. Key Concepts

| Concept | Description |
| :--- | :--- |
| **Master Batch** | A customer must be assigned exactly **one** "Master Batch" per month. All products they receive in that month must come from this single batch (or be unavailable). |
| **Future Batch** | A virtual, infinite batch (`FUTURE_MASTER_BATCH`) representing future procurement. It is always available but usually reserved for when real inventory runs out. |
| **Switching** | Changing the Master Batch from Month $t$ to Month $t+1$. This incurs a `penalty` cost. |
| **Scrap** | Any inventory remaining in a batch after its `expiry_month_index` is considered "scrapped" and incurs a `scrap_cost_per_unit`. |

## 3. The Logic (Constraints)

The optimizer solves a mathematical problem with these rules:

1.  **Meet Demand**: If a customer needs Product A in Month 1, you MUST supply it from the assigned Master Batch.
2.  **One Master Batch**: You cannot mix batches for a single customer in a single month. You can't give them Product A from Batch 1 and Product B from Batch 2.
3.  **Inventory Limits**: You cannot sell more than you have.
    *   *Exception*: The `FUTURE_MASTER_BATCH` has infinite quantity.
4.  **Expiry**: You cannot sell a batch after it expires.
5.  **No Returns**: Once you stop using a batch for a customer, you generally move forward. (The code tracks "starts" to calculate penalties).

## 4. Concrete Example

Imagine this scenario (similar to the one we just ran):

*   **Demand**: Customer 1 needs 10 units/month of Product A for 12 months.
*   **Inventory**:
    *   **Batch OLD**: 20 units, Expires Month 3.
    *   **Batch MAIN**: 100 units, Expires Month 12.

### Scenario A: Ignore Expiry (Bad Plan)
*   Use **Batch MAIN** from Month 1 to 10.
*   **Result**:
    *   Switches: 0 (Great!)
    *   Scrap: **Batch OLD** expires unused (20 units * Cost).
    *   **Total Cost**: High Scrap Cost.

### Scenario B: The Optimizer's Plan (Optimal)
1.  **Month 1-2**: Use **Batch OLD**. (Consumes 20 units).
2.  **Month 3**: **Switch** to **Batch MAIN**.
3.  **Month 3-12**: Use **Batch MAIN**.

*   **Result**:
    *   Switches: 1 (Penalty cost).
    *   Scrap: 0 (Batch OLD was fully used).
    *   **Total Cost**: Just 1 Penalty.

**Conclusion**: If (Scrap Cost of 20 units) > (1 Switch Penalty), the optimizer chooses **Scenario B**. This is exactly what the script calculates.

## 5. How to Run It

You can use the `run_optimizer.py` script we created:

```python
from confi import ProductDistribution

# 1. Load your data
demand, months = load_data(...)
inventory = generate_inventory(...)

# 2. Initialize
opt = ProductDistribution(
    customer=customers,
    product=products,
    months=months,
    inventory_df=inventory,
    demand_forecast=demand
)

# 3. Run
distribution, costs = opt.optimize_distribution()
```

---

# Detailed Line-by-Line Code Explanation

## Import Section (Lines 1-6)

```python
import os
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
```

- **os**: Access environment variables for Gurobi WLS credentials
- **pandas**: Handle dataframes for inventory and demand forecast
- **gurobipy**: Gurobi optimization library
- **GRB**: Gurobi constants (e.g., `GRB.BINARY`, `GRB.CONTINUOUS`)

---

## Class Definition (Lines 9-340)

### `ProductDistribution` Class

Main optimizer class that uses Gurobi Web License Service (WLS) to solve the distribution problem.

---

## Constructor `__init__` (Lines 22-74)

### Key Parameters:

**Lines 23-28: Core Data Inputs**
```python
customer        # List of customer IDs
product         # List of product IDs
months          # Number of months in planning horizon
inventory_df    # DataFrame: batch inventory (batch, product, quantity, available_month, expiry_month)
demand_forecast # DataFrame: forecasted demand (customer, product, month_index, quantity)
```

**Lines 29-33: Cost Parameters**
```python
lot_sizes            # Optional lot size constraints (not used in current version)
penalty=100.0        # Cost per batch switch (default: 100)
scrap_cost_per_unit=1.0  # Cost per unit scrapped due to expiry
```

**Lines 34-38: Gurobi WLS Configuration**
```python
wls_access_id    # WLS Access ID (or from GUROBI_WLSACCESSID env var)
wls_secret       # WLS Secret (or from GUROBI_WLSSECRET env var)
wls_license_id   # WLS License ID (or from GUROBI_LICENSEID env var)
use_wls=True     # Whether to use WLS (cloud) or local license
```

**Lines 39-41: Yearly Switch Caps**
```python
max_switches_per_year  # Optional: limit switches per customer per year
                       # Can be: int, dict[customer, int], or dict[customer, dict[year, int]]
month_years            # List mapping each month index to calendar year
```

**Lines 43-52: Data Storage**
```python
self.customer = list(customer)          # Store customer list
self.product = list(product)            # Store product list
self.months = int(months)               # Store number of months
self.inventory_df = inventory_df.copy() # COPY inventory DataFrame
self.demand_forecast = demand_forecast.copy()  # COPY demand forecast DataFrame
```

> 🔑 **Important**: Lines 46-47 create COPIES of the input DataFrames to avoid modifying original data.

**Lines 54-67: WLS Credential Setup**
- Read from parameters first, then fall back to environment variables
- Handles license ID conversion to integer

**Lines 69-74: Results Storage**
```python
self.best_distribution = {}  # Will store optimal distribution plan
```

---

## WLS Environment Setup `_build_env` (Lines 76-96)

**Purpose**: Create Gurobi environment with WLS credentials (cloud-based) or local license.

**Lines 77-89**: Validation
- Check if all required WLS credentials are provided
- Raise error if any are missing when `use_wls=True`

**Lines 90-94**: WLS Environment
```python
env = gp.Env(empty=True)               # Create empty environment
env.setParam("WLSAccessID", ...)       # Set access ID
env.setParam("WLSSecret", ...)         # Set secret key
env.setParam("LicenseID", ...)         # Set license ID
env.start()                            # Start environment
```

**Line 96**: Local License
```python
return gp.Env()  # Use local Gurobi license if use_wls=False
```

---

## Switch Cap Resolution `_resolve_switch_cap` (Lines 98-113)

**Purpose**: Determine switch limit for a specific customer/year combination.

**Logic**:
1. If `max_switches_per_year` is `None` → return `None` (no limit)
2. If it's an `int` → apply same limit to all customers/years
3. If it's a `dict`:
   - `dict[customer, int]` → customer-specific limit
   - `dict[customer, dict[year, int]]` → customer AND year-specific limit

---

## Main Optimization `optimize_distribution` (Lines 115-339)

### Data Preparation (Lines 116-167)

**Lines 117-119: Sets**
```python
C = self.customer           # Customer set
P = self.product            # Product set
M = list(range(self.months)) # Month indices [0, 1, ..., months-1]
```

**Lines 121-130: Yearly Caps Validation**
- If yearly caps are specified, `month_years` must be provided
- Extract unique years from `month_years`

**Lines 132-135: Batch Setup**
```python
inv = self.inventory_df[...]              # Filter inventory for relevant products
B_real = sorted(inv["batch"].unique())    # Get real batches
FUTURE = "FUTURE_MASTER_BATCH"            # Virtual batch for procurement
B = B_real + [FUTURE]                     # Combined batch list
```

> 💡 **Key Concept**: `FUTURE_MASTER_BATCH` is a virtual infinite-capacity batch representing future procurement.

**Lines 137-146: Demand Dictionary**
```python
D[c, p, m] = quantity  # Demand for customer c, product p, month m
```

**Lines 148-152: Activity Flags**
```python
D_active[c, m] = 1 if any demand for customer c in month m, else 0
```
- Used to ensure exactly ONE master batch is assigned per active customer-month

**Lines 155-167: Inventory Maps**
```python
qty_bp[b, p]    # Quantity of product p in batch b
avail_bp[b, p]  # Month when batch b of product p becomes available
exp_bp[b, p]    # Month when batch b of product p expires
has_bp          # Set of valid (batch, product) pairs
```

- **FUTURE batch**: Available from month 0, expires after horizon (month `months + 1`)

---

### Model Building (Lines 169-176)

**Lines 170-172: Create Model**
```python
env = self._build_env()                          # Get Gurobi environment
m = gp.Model("product_distribution_gurobi_wls", env=env)  # Create model
```

**Lines 173-176: Configure**
```python
if not self.verbose:
    m.Params.OutputFlag = 0  # Suppress Gurobi output if not verbose
for k, v in self.gurobi_params.items():
    setattr(m.Params, k, v)  # Apply custom Gurobi parameters
```

---

### Decision Variables (Lines 178-198)

**Lines 179-180: Binary Variables**
```python
z[c, t, b]  # = 1 if customer c uses batch b as MASTER in month t
s[c, t, b]  # = 1 if customer c STARTS using batch b in month t
```

**Lines 182-195: Continuous Variables**
```python
x[c, p, t, b]  # Quantity of product p from batch b allocated to customer c in month t
```
- Only created for valid combinations (demand exists, batch available & not expired)

**Lines 197-198: Scrap Variables**
```python
u[b, p]  # Quantity of product p in batch b that gets scrapped
```
- Only for batches that expire before the planning horizon ends

---

### Constraints (Lines 200-261)

**C1: Exact Demand (Lines 202-209)**
```python
∑_b x[c, p, t, b] = D[c, p, t]  ∀ c, p, t with demand > 0
```
- **Purpose**: Meet exact demand for each customer-product-month

**C2: One Master Batch (Lines 211-215)**
```python
∑_b z[c, t, b] = D_active[c, t]  ∀ c, t
```
- **Purpose**: Each customer uses exactly ONE master batch per active month

**C3: Link Allocation to Master (Lines 217-221)**
```python
x[c, p, t, b] ≤ D[c, p, t] × z[c, t, b]  ∀ c, p, t, b
```
- **Purpose**: Can only allocate from batch b if it's the master batch

**C4: Capacity (Lines 223-228)**
```python
∑_{c,t} x[c, p, t, b] ≤ qty_bp[b, p]  ∀ real batches b, p
```
- **Purpose**: Don't exceed available inventory
- **Note**: FUTURE batch has no capacity constraint (infinite)

**C5: Scrap Calculation (Lines 230-236)**
```python
u[b, p] ≥ qty_bp[b, p] - ∑_{c,t<exp} x[c, p, t, b]  ∀ b, p expiring before horizon
```
- **Purpose**: Calculate scrapped quantity (unused before expiry)

**C6: Switching Logic (Lines 238-247)**
```python
∑_t s[c, t, b] ≤ 1                    # Can start batch b at most once per customer
s[c, 0, b] = z[c, 0, b]               # If using b in month 0, it's a start
s[c, t, b] ≥ z[c, t, b] - z[c, t-1, b]  # Detect switch from non-use to use
```
- **Purpose**: Track batch switches and enforce no-return policy

**C7: Yearly Switch Caps (Lines 249-261)**
```python
∑_{t in year y, t≥1} ∑_b s[c, t, b] ≤ max_switches_per_year[c, y]  ∀ c, y
```
- **Purpose**: Limit number of switches per customer per year
- **Note**: Only counts true switches (t ≥ 1), not initial batch selection

---

### Objective Function (Lines 263-266)

```python
Minimize: switch_cost + scrap_cost

where:
  switch_cost = ∑_{c,t≥1,b} penalty × s[c, t, b]
  scrap_cost  = ∑_{b,p} scrap_cost_per_unit × u[b, p]
```

- **Goal**: Minimize total cost of switching batches and scrapping expired inventory

---

### Solve and Extract (Lines 268-297)

**Lines 268-271: Solve**
```python
m.optimize()                                      # Run optimizer
if m.SolCount == 0:
    raise RuntimeError("No feasible solution")    # Check if solution found
```

**Lines 273-297: Extract Solution**
```python
best_distribution[c][t][p] = (batch, quantity)
```
- For each customer-month-product: which batch and how much quantity
- Special handling for FUTURE batch to ensure demand is met

---

### Cost Reporting (Lines 299-332)

**Lines 300-311: Switch Costs**
- Record each switch event with customer, month, batch, and penalty cost

**Lines 313-323: Scrap Costs**
- Record each scrapped batch with product, quantity, and scrap cost

**Lines 325-331: Summary DataFrame**
```python
cost_details = pd.DataFrame(rows)    # Detailed cost breakdown
totals = pd.DataFrame([...])         # Total costs row
```

**Line 333: Return**
```python
return self.best_distribution, cost_details
```

---

### Cleanup (Lines 335-339)

```python
finally:
    try:
        env.dispose()  # Release Gurobi environment resources
    except Exception:
        print("ERROR!")
```

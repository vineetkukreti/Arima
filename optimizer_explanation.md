# Optimizer Scripts Explained

This document walks through the two main scripts related to the large-scale product/customer optimizer. The emphasis is on `g_optimiser_script.py`, with a brief companion explanation for `run_optimizer_g.py`. Line numbers are approximate and based on the current repository version.

## `g_optimiser_script.py`

### Imports and Class Definition (lines 1-22)
- `import os`, `pandas as pd`, and `gurobipy` bring in operating-system helpers, data manipulation, and the Gurobi solver API.
- `ProductDistribution` is the single class that encapsulates the entire mixed-integer linear program (MILP). The docstring sets expectations: it solves a weekly/monthly plan with exact demand satisfaction and optional yearly switch caps.

### Constructor / `__init__` (lines 24-77)
- Accepts the core data (`customer`, `product`, `months`, `inventory_df`, `demand_forecast`) plus optional knobs (`lot_sizes`, penalties, scrap costs, custom Gurobi parameters, verbosity, WLS credentials, and yearly switch caps).
- Each argument is sanitized: customers/products become lists, months cast to `int`, numeric penalties force `float`, and data frames are copied so upstream callers stay untouched.
- WLS (Gurobi Web License Service) credentials default to environment variables if not explicitly passed. The license ID is also read from `GUROBI_LICENSEID` when not supplied.
- Yearly switch tracking is only activated if `max_switches_per_year` is not `None`; when it is supplied, `month_years` must describe which calendar year each model month belongs to.
- A placeholder `best_distribution` dictionary is prepared to store the solution once the model runs.

### `_build_env` Helper (lines 79-106)
- Responsible for constructing a Gurobi `Env` object, which is the context the solver uses.
- When `use_wls` is `True`, it verifies that all WLS credentials are present; missing pieces raise `RuntimeError` before any model work happens.
- It configures the environment with the WLS keys and starts it. If WLS is disabled, it falls back to a local environment via `gp.Env()`.

### `_resolve_switch_cap` Helper (lines 108-126)
- Interprets the `max_switches_per_year` input, which can be:
  1. A single integer that applies everywhere.
  2. A dict mapping customer → cap.
  3. A nested dict mapping customer → year → cap.
- Returns the correct cap for a given customer/year pair, or `None` if no cap applies.

### `optimize_distribution` Method
This is where the MILP is assembled and solved. Steps follow the order in the code.

#### Set Construction (lines 128-164)
- Defines short aliases: `C` (customers), `P` (products), `M` (list of month indices 0..months-1).
- If yearly caps are active, it validates that `month_years` exists and matches the horizon length, then enumerates the unique calendar years involved.
- Filters the inventory down to the relevant products and builds batch identifiers. A special placeholder batch `FUTURE_MASTER_BATCH` covers any supply beyond listed inventory.

#### Demand Preparation (lines 166-189)
- Filters the demand forecast to the exact `(customer, product, month)` combinations the model will consider.
- Builds `D`, a dictionary keyed by `(customer, product, month)` holding required quantity.
- Creates `D_active`, a helper map that marks whether a customer needs anything in a given month (used later to enforce "one batch per active month").

#### Inventory Maps (lines 191-214)
- Builds dictionaries describing each real batch: quantity, first available month, expiry month, plus a `has_bp` set for quick membership checks.
- Adds `FUTURE_MASTER_BATCH` entries for every product so the solver can pull from infinite fallback supply (subject to penalties via switching/scrap, not explicit cost here).

#### Environment and Model Setup (lines 216-242)
- Calls `_build_env()` and feeds it into a `gp.Model` instance named `product_distribution_gurobi_wls`.
- Silences solver output unless `verbose` is `True`.
- Applies any custom Gurobi parameters stored in `self.gurobi_params`.

#### Decision Variables (lines 244-279)
- `z[c,t,b]` (binary): equals 1 if customer `c` uses batch `b` in month `t`. This enforces single master batch per customer-month.
- `s[c,t,b]` (binary): equals 1 if customer `c` starts using batch `b` in month `t`. Used for switch penalties and yearly caps.
- `x[c,p,t,b]` (continuous, ≥0): quantity of product `p` shipped to customer `c` in month `t` from batch `b`. Only created for feasible combinations (non-zero demand, batch has the product, and it is within availability/expiry range).
- `u[b,p]` (continuous, ≥0): scrap quantity left for each expiring batch/product pair, but only if the batch expires within the modeling horizon.

#### Constraints
- **C1 Demand Balance (lines 284-293):** For every demand entry, the sum of allocations from all batches equals the required quantity exactly.
- **One Batch Per Active Month (lines 295-300):** If a customer needs something in month `t`, exactly one `z` variable must be 1, meaning they choose a single batch to serve all demanded products that month.
- **Linking `x` to `z` (lines 302-307):** Prevents shipping from a batch unless that batch is selected (`x <= demand * z`).
- **Inventory Capacity (lines 309-314):** Ensures total shipped units from each real batch/product do not exceed on-hand quantity.
- **Scrap Definition (lines 316-322):** Forces `u[b,p]` to be at least the leftover stock when the horizon ends (quantity minus what was shipped before expiry).
- **Switch Tracking (lines 324-342):**
  - At most one start (`s`) per `(customer, batch)` overall.
  - Month 0 start equals whether the batch is used immediately.
  - Later months detect true switches via `s >= z_t - z_{t-1}`.
- **Yearly Switch Caps (lines 344-356):** If caps exist, sum of starts in each calendar year for a customer cannot exceed the resolved cap.

#### Objective Function (lines 358-366)
- Minimizes total penalty cost: `switch_cost = penalty × sum of switch starts from month 1 onward`, plus `scrap_cost = scrap_cost_per_unit × sum of scrap quantities`.

#### Solve and Feasibility Check (lines 368-373)
- Calls `m.optimize()` to let Gurobi solve the MILP.
- Raises an error if no solution exists.

#### Extracting the Best Distribution (lines 375-404)
- Initializes a nested dictionary `[customer][month] -> {product: (batch, qty)}`.
- For each active customer-month, finds the batch with `z = 1` and records how each product’s demand is allocated from that batch.
- Special handling for the future batch: if `x` variables are missing (because future batch is implicit), fill in the full demand.
- Stores the result on `self.best_distribution` for reuse.

#### Cost Reporting (lines 406-449)
- Builds a `rows` list summarizing every switch event and scrap outcome, then converts it to a `pandas` DataFrame.
- Accumulates total switch cost and scrap cost; adds a `TOTALS` row.
- Returns `(best_distribution, cost_details)` to the caller.

#### Cleanup (lines 451-456)
- Always attempts to dispose the Gurobi environment in a `finally` block so resources free even if an exception occurs.

## `run_optimizer_g.py`

### Purpose and Structure (lines 1-15)
- Designed as a runnable helper that loads a "large" synthetic dataset and feeds it into `ProductDistribution`.
- Imports pandas for I/O, adjusts `sys.path` so the local module is discoverable, and pulls in `ProductDistribution`.

### `load_large_data()` (lines 17-55)
- Reads demand and inventory Excel files located under `data/`.
- Builds a continuous `month_index` by converting year/month columns to real dates and counting months from the earliest entry.
- Renames demand columns to match what `ProductDistribution` expects and computes the planning horizon (`max month_index + 1`).
- Prints basic dataset diagnostics, then returns `(demand_forecast, inventory_df, months)`.

### `run_optimizer_large()` (lines 57-159)
- Loads the data and derives unique customer/product lists.
- Applies size limits (max months/customers/products) to stay within the free Gurobi license limits (~2000 variables). This may reduce the dataset by slicing demand rows and inventory batches.
- Filters inventory so only the selected products remain and only batches relevant to the reduced horizon are kept.
- Checks whether WLS credentials exist in the environment and toggles `use_wls` accordingly.
- Instantiates `ProductDistribution` with verbose logging enabled, then calls `optimize_distribution()`.
- After a successful solve:
  - Prints a cost summary (switching, scrap, total).
  - Saves `cost_details` to `optimization_results_10k.xlsx`.
  - Converts `best_distribution` into JSON-friendly form and writes `distribution_plan_10k.json`.
- If anything fails, it prints the traceback and hints about reducing problem size when the license limit is hit.

### Script Entry Point (lines 161-165)
- Running the file directly executes `run_optimizer_large()`.

---
This explanation should make it easier to trace each step of the optimizer, understand how it prepares data, builds the MILP, and processes results.

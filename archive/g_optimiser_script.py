# optimizer_calculator.py
# -*- coding: utf-8 -*-
import os
import pandas as pd
import gurobipy as gp
from gurobipy import GRB


class ProductDistribution:
    """
    Gurobi MILP optimizer (WLS-enabled).

    Constraints:
      - C1: Exact demand per (customer, product, month)
      

    Yearly switches:
      - max_switches_per_year: int | dict[str,int] | dict[str,dict[int,int]] | None
      - month_years: list[int] of length `months` mapping each month index to calendar year.
    """

    def __init__(
        self,
        customer,
        product,
        months,
        inventory_df,
        demand_forecast,
        lot_sizes=None,
        penalty=100.0,
        scrap_cost_per_unit=1.0,
        gurobi_params=None,
        verbose=False,
        # --- WLS parameters (optional; defaults read from env) ---
        wls_access_id=None,
        wls_secret=None,
        wls_license_id=None,
        use_wls=True,
        # --- Yearly switch cap (new) ---
        max_switches_per_year=None,
        month_years=None,
    ):
        self.customer = list(customer)
        self.product = list(product)
        self.months = int(months)
        self.inventory_df = inventory_df.copy()
        self.demand_forecast = demand_forecast.copy()
        self.lot_sizes = lot_sizes
        self.penalty = float(penalty)
        self.scrap_cost_per_unit = float(scrap_cost_per_unit)
        self.gurobi_params = gurobi_params or {}
        self.verbose = bool(verbose)

        # WLS settings
        self.use_wls = bool(use_wls)
        self.wls_access_id = (
            wls_access_id if wls_access_id is not None else os.environ.get("GUROBI_WLSACCESSID")
        )
        self.wls_secret = (
            wls_secret if wls_secret is not None else os.environ.get("GUROBI_WLSSECRET")
        )
        lic_env = os.environ.get("GUROBI_LICENSEID")
        self.wls_license_id = (
            int(wls_license_id)
            if wls_license_id is not None
            else (int(lic_env) if lic_env not in (None, "", "None") else None)
        )

        # Yearly switch caps
        self.max_switches_per_year = max_switches_per_year
        self.month_years = list(month_years) if month_years is not None else None

        # results
        self.best_distribution = {}

    def _build_env(self):
        if self.use_wls:
            missing = []
            if not self.wls_access_id:
                missing.append("GUROBI_WLSACCESSID / wls_access_id")
            if not self.wls_secret:
                missing.append("GUROBI_WLSSECRET / wls_secret")
            if self.wls_license_id is None:
                missing.append("GUROBI_LICENSEID / wls_license_id")
            if missing:
                details = ", ".join(missing)
                raise RuntimeError(
                    f"WLS is enabled but the following settings are missing: {details}"
                )
            env = gp.Env(empty=True)
            env.setParam("WLSAccessID", self.wls_access_id)
            env.setParam("WLSSecret", self.wls_secret)
            env.setParam("LicenseID", self.wls_license_id)
            env.start()
            return env
        return gp.Env()

    # Resolve per-customer/year switch cap
    def _resolve_switch_cap(self, c, y):
        cap = self.max_switches_per_year
        if cap is None:
            return None
        if isinstance(cap, int):
            return cap
        if isinstance(cap, dict):
            v = cap.get(c, None)
            if v is None:
                return None
            if isinstance(v, int):
                return v
            if isinstance(v, dict):
                return v.get(y, None)
        return None

    def optimize_distribution(self):
        # ----- Sets and derived parameters -----
        C = self.customer
        P = self.product
        M = list(range(self.months))

        # If using yearly caps, month_years is required
        if self.max_switches_per_year is not None:
            if self.month_years is None or len(self.month_years) != self.months:
                raise ValueError(
                    "month_years must be provided (list[int] of length `months`) "
                    "when max_switches_per_year is set."
                )
            YEARS = sorted(set(self.month_years))
        else:
            YEARS = []

        inv = self.inventory_df[self.inventory_df["product"].isin(P)].copy()
        B_real = sorted(inv["batch"].unique().tolist())
        FUTURE = "FUTURE_MASTER_BATCH"
        B = B_real + [FUTURE]

        # Demand dict D[c,p,m]
        df = self.demand_forecast[
            self.demand_forecast["customer"].isin(C)
            & self.demand_forecast["product"].isin(P)
            & self.demand_forecast["month_index"].isin(M)
        ].copy()
        D = {
            (r["customer"], r["product"], int(r["month_index"])): float(r["quantity"])
            for _, r in df.iterrows()
        }

        # Activity flag per customer-month (any product demand?)
        D_any = {(c, m): 0.0 for c in C for m in M}
        for (c, p, m), q in D.items():
            D_any[(c, m)] += q
        D_active = {(c, m): 1 if D_any[(c, m)] > 1e-9 else 0 for c in C for m in M}

        # Inventory maps
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

        # ----- Build model -----
        env = self._build_env()
        try:
            m = gp.Model("product_distribution_gurobi_wls", env=env)
            if not self.verbose:
                m.Params.OutputFlag = 0
            for k, v in self.gurobi_params.items():
                setattr(m.Params, k, v)

            # Decision variables
            z = m.addVars(((c, t, b) for c in C for t in M for b in B), vtype=GRB.BINARY, name="z")
            s = m.addVars(((c, t, b) for c in C for t in M for b in B), vtype=GRB.BINARY, name="s")

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

            u_index = [(b, p) for (b, p) in qty_bp.keys() if exp_bp[(b, p)] <= (self.months - 1)]
            u = m.addVars(u_index, lb=0.0, vtype=GRB.CONTINUOUS, name="u")

            # Constraints
            # C1 demand
            for c in C:
                for p in P:
                    for t in M:
                        demand = D.get((c, p, t), 0.0)
                        if demand <= 1e-9:
                            continue
                        m.addConstr(gp.quicksum(x.get((c, p, t, b), 0.0) for b in B) == demand,
                                    name=f"demand_exact[{c},{p},{t}]")

            # one master batch per active (c,t)
            for c in C:
                for t in M:
                    m.addConstr(gp.quicksum(z[c, t, b] for b in B) == D_active[(c, t)],
                                name=f"one_batch[{c},{t}]")

            # link x to z
            for (c, p, t, b) in x_index:
                demand = D[(c, p, t)]
                m.addConstr(x[c, p, t, b] <= demand * z[c, t, b],
                            name=f"x_link[{c},{p},{t},{b}]")

            # capacity
            for (b, p), qty in qty_bp.items():
                if b == FUTURE:
                    continue
                used = gp.quicksum(x.get((c, p, t, b), 0.0) for c in C for t in M)
                m.addConstr(used <= qty, name=f"cap[{b},{p}]")

            # scrap
            for (b, p) in u_index:
                qty = qty_bp[(b, p)]
                used_before_exp = gp.quicksum(
                    x.get((c, p, t, b), 0.0) for c in C for t in M if t < exp_bp[(b, p)]
                )
                m.addConstr(u[(b, p)] >= qty - used_before_exp, name=f"scrap[{b},{p}]")

            # switching + no-return
            for c in C:
                for b in B:
                    m.addConstr(gp.quicksum(s[c, t, b] for t in M) <= 1,
                                name=f"start_le1[{c},{b}]")
                    m.addConstr(s[c, 0, b] == z[c, 0, b],
                                name=f"start_t0[{c},{b}]")
                    for t in M[1:]:
                        m.addConstr(s[c, t, b] >= z[c, t, b] - z[c, t - 1, b],
                                    name=f"start_link[{c},{b},{t}]")

            # Yearly switch caps (C6) — count only t >= 1 (true switches)
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

            # Objective
            switch_cost = gp.quicksum(self.penalty * s[c, t, b] for c in C for t in M[1:] for b in B)
            scrap_cost = gp.quicksum(self.scrap_cost_per_unit * u[bp] for bp in u_index)
            m.setObjective(switch_cost + scrap_cost, GRB.MINIMIZE)

            # Solve
            m.optimize()
            if m.SolCount == 0:
                raise RuntimeError("No feasible solution found by Gurobi (WLS).")

            # Extract
            best_distribution = {c: {} for c in C}
            for c in C:
                for t in M:
                    if D_active[(c, t)] == 0:
                        continue
                    b_star = None
                    for b in B:
                        if z[c, t, b].X > 0.5:
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

            # Cost report
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

            cost_details = pd.DataFrame(rows)
            totals = pd.DataFrame([{
                "Customer": "TOTALS", "Month": "", "BatchStarted": "",
                "SwitchPenalty": total_switch_cost, "Batch": "", "Product": "",
                "ScrapQty": "", "ScrapCost": total_scrap_cost
            }])
            cost_details = pd.concat([cost_details, totals], ignore_index=True)

            return self.best_distribution, cost_details

        finally:
            try:
                env.dispose()
            except Exception:
                print("ERROR!")

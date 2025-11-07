import pyomo.environ as pyo
import pandas as pd
import math


def optimization(AllInputs):
    """
    ======================================================================
    EV-only optimization (V2G test version)
    ======================================================================
    - Reads real buy/sell prices from external Excel file
    - Works with multiple EVs (from AllInputs.EV.smart)
    - Tests Vehicle-to-Grid arbitrage behavior
    ======================================================================
    """

    # ───────────────────────────────────────────────────────────────
    # Model and sets
    # ───────────────────────────────────────────────────────────────
    l_t = AllInputs.System.l_t
    l_Mev = AllInputs.EV.smart.l_Mev

    model = pyo.AbstractModel()
    model.t = pyo.Set(initialize=l_t)
    model.Mev = pyo.Set(initialize=l_Mev)
    model.inc_t = pyo.Param(initialize=AllInputs.System.inc_t)

    # ───────────────────────────────────────────────────────────────
    # Load external buy/sell prices
    # ───────────────────────────────────────────────────────────────
    price_path = r"D:\Users\Varun\Downloads\Buy_Sell.xlsx"
    price_data = pd.read_excel(price_path)

    if not {"buy_price", "sell_price"}.issubset(price_data.columns):
        raise ValueError(
            f"Excel file must contain columns 'buy_price' and 'sell_price'. "
            f"Found: {list(price_data.columns)}"
        )

    buy_prices = dict(enumerate(price_data["buy_price"].values))
    sell_prices = dict(enumerate(price_data["sell_price"].values))

    # Match simulation time horizon
    buy_prices = {t: buy_prices[t] for t in l_t if t in buy_prices}
    sell_prices = {t: sell_prices[t] for t in l_t if t in sell_prices}

    model.price_buy = pyo.Param(model.t, initialize=buy_prices)
    model.price_sell = pyo.Param(model.t, initialize=sell_prices)

    print(f"Loaded {len(price_data)} hourly prices from Excel.")
    print(f"Example prices: buy={price_data['buy_price'].iloc[0]:.3f} €/kWh, "
          f"sell={price_data['sell_price'].iloc[0]:.3f} €/kWh")

    # ───────────────────────────────────────────────────────────────
    # EV parameters
    # ───────────────────────────────────────────────────────────────
    model.Pmax = pyo.Param(model.Mev, initialize=AllInputs.EV.smart.Pmax_evMev)
    model.E_ev = pyo.Param(model.Mev, initialize=AllInputs.EV.smart.E_evMev)
    model.K_evMev_t = pyo.Param(model.Mev, model.t,
                                initialize=AllInputs.EV.smart.K_evMev_t,
                                within=pyo.Binary)
    model.Pbaseline = pyo.Param(model.Mev, model.t,
                                initialize=AllInputs.EV.smart.Pbaseline_evMev_t)
    model.flex_price = pyo.Param(model.Mev,
                                 initialize=AllInputs.EV.smart.Cost_evMev)
    model.eta_ch = pyo.Param(initialize=0.95)
    model.eta_dis = pyo.Param(initialize=0.95)

    # ───────────────────────────────────────────────────────────────
    # Decision variables
    # ───────────────────────────────────────────────────────────────
    model.Pch = pyo.Var(model.Mev, model.t, within=pyo.NonNegativeReals)
    model.Pdis = pyo.Var(model.Mev, model.t, within=pyo.NonNegativeReals)
    model.Pnet = pyo.Var(model.Mev, model.t, within=pyo.Reals)  # +ve=charge, −ve=discharge
    model.flex_cost = pyo.Var(model.Mev, within=pyo.NonNegativeReals)
    model.mode = pyo.Var(model.Mev, model.t, within=pyo.Binary)  # 1=charging, 0=discharging

    # ───────────────────────────────────────────────────────────────
    # Constraints
    # ───────────────────────────────────────────────────────────────

    # (1) Power balance
    def net_power(m, Mev, t):
        return m.Pnet[Mev, t] == m.Pch[Mev, t] - m.Pdis[Mev, t]
    model.constr_power_balance = pyo.Constraint(model.Mev, model.t, rule=net_power)

    # (2) Power limits + availability
    def ch_limit(m, Mev, t):
        return m.Pch[Mev, t] <= m.K_evMev_t[Mev, t] * m.Pmax[Mev]
    def dis_limit(m, Mev, t):
        return m.Pdis[Mev, t] <= m.K_evMev_t[Mev, t] * m.Pmax[Mev]
    model.constr_ch_limit = pyo.Constraint(model.Mev, model.t, rule=ch_limit)
    model.constr_dis_limit = pyo.Constraint(model.Mev, model.t, rule=dis_limit)

    # (3) No simultaneous charging/discharging
    def no_simul_charge(m, Mev, t):
        return m.Pch[Mev, t] <= m.Pmax[Mev] * m.mode[Mev, t]
    def no_simul_discharge(m, Mev, t):
        return m.Pdis[Mev, t] <= m.Pmax[Mev] * (1 - m.mode[Mev, t])
    model.no_simul_charge = pyo.Constraint(model.Mev, model.t, rule=no_simul_charge)
    model.no_simul_discharge = pyo.Constraint(model.Mev, model.t, rule=no_simul_discharge)

    # (4) Energy balance considering efficiency
    def energy_balance(m, Mev):
        return sum(m.eta_ch * m.Pch[Mev, t] - (1 / m.eta_dis) * m.Pdis[Mev, t]
                   for t in l_t) * m.inc_t == m.E_ev[Mev]
    model.energy_balance = pyo.Constraint(model.Mev, rule=energy_balance)

    EXTRA_CHARGE_HEADROOM = 0.2

    def charge_cap(m, Mev):
        return sum(m.Pch[Mev, t] for t in l_t) * m.inc_t <= (1 + EXTRA_CHARGE_HEADROOM) * m.E_ev[Mev] / m.eta_ch

    model.charge_cap = pyo.Constraint(model.Mev, rule=charge_cap)


    # (5) Energy neutrality (cannot discharge more than charged)
    def energy_neutrality(m, Mev):
        return sum(m.Pch[Mev, t] * 0.95 for t in m.t) * m.inc_t >= \
               sum(m.Pdis[Mev, t] / 0.95 for t in m.t) * m.inc_t
    model.energy_neutrality = pyo.Constraint(model.Mev, rule=energy_neutrality)

    # ───────────────────────────────────────────────────────────────
    # Objective: minimize total net energy cost
    # ───────────────────────────────────────────────────────────────
    def objective_rule(m):
        cost_buy = sum(m.price_buy[t] * sum(m.Pch[Mev, t] for Mev in l_Mev) * m.inc_t for t in l_t)
        income_sell = sum(m.price_sell[t] * sum(m.Pdis[Mev, t] for Mev in l_Mev) * m.inc_t for t in l_t)
        reward = 0.01 * sum(m.Pdis[Mev, t] for Mev in l_Mev for t in l_t) * m.inc_t
        return cost_buy - income_sell - reward

    model.obj = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

    # ───────────────────────────────────────────────────────────────
    # Instantiate and return instance
    # ───────────────────────────────────────────────────────────────
    instance = model.create_instance()

    # Quick diagnostic print
    print(f"Model ready with {len(l_Mev)} EV(s) and {len(l_t)} timesteps.")
    print(f"Total price points: {len(buy_prices)} buy / {len(sell_prices)} sell.")

    return instance

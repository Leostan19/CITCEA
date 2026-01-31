import pyomo.environ as pyo
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =====================================================
# 1. 数据读取（Excel / CSV）
# =====================================================
def read_load_csv(path):
    df = pd.read_csv(path, comment="#", sep=",")
    return df["total_demand"].astype(float).values  # MWh

def read_pv_csv(path):
    df = pd.read_csv(path, comment="#", sep=",")
    return df["electricity"].astype(float).values   # MWh

def read_price_excel(path):
    df = pd.read_excel(path, header=None, decimal=",")
    return df.iloc[:, 1].astype(float).values       # €/kWh

# =====================================================
# 2. 数据 & 单位转换：MWh → kWh
# =====================================================
Load = {
    1: read_load_csv("Load_Haotian.csv") * 1000,
    2: read_price_excel("load.xlsx") * 1000
}

PV = {
    1: read_pv_csv("PV_Haotian.csv") * 1000,
    2: read_pv_csv("PV_Travis.csv") * 1000
}

Price_buy_raw = {
    1: read_price_excel("Priceoctopus.xlsx"),
    2: read_price_excel("Pricesomenergia.xlsx")
}

# =====================================================
# 3. 时间集合（168 小时）
# =====================================================
T = range(168)
hours = np.array(list(T))

# =====================================================
# 4. Pyomo 模型
# =====================================================
model = pyo.ConcreteModel()
model.M = pyo.Set(initialize=[1, 2])
model.T = pyo.Set(initialize=T)

model.Price_buy = pyo.Param(
    model.M, model.T,
    initialize=lambda model, m, t: Price_buy_raw[m][t],
    within=pyo.NonNegativeReals
)

# =====================================================
# 5. 决策变量（kWh per hour）
# =====================================================
model.E_grid_buy  = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)
model.E_grid_sell = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)
model.E_ex_12 = pyo.Var(model.T, within=pyo.NonNegativeReals)
model.E_ex_21 = pyo.Var(model.T, within=pyo.NonNegativeReals)

# =====================================================
# 6. 能量平衡
# =====================================================
def balance_m1(model, t):
    return (
        PV[1][t]
        + model.E_grid_buy[1, t]
        + model.E_ex_21[t]
        ==
        Load[1][t]
        + model.E_grid_sell[1, t]
        + model.E_ex_12[t]
    )

def balance_m2(model, t):
    return (
        PV[2][t]
        + model.E_grid_buy[2, t]
        + model.E_ex_12[t]
        ==
        Load[2][t]
        + model.E_grid_sell[2, t]
        + model.E_ex_21[t]
    )

model.balance_m1 = pyo.Constraint(model.T, rule=balance_m1)
model.balance_m2 = pyo.Constraint(model.T, rule=balance_m2)

# =====================================================
# 7. 目标函数（€）
# =====================================================
def total_cost(model):
    return sum(
        model.Price_buy[m, t] * model.E_grid_buy[m, t]
        - 0.5 * model.Price_buy[m, t] * model.E_grid_sell[m, t]
        for m in model.M
        for t in model.T
    )

model.obj = pyo.Objective(rule=total_cost, sense=pyo.minimize)

# =====================================================
# 8. 求解
# =====================================================
solver = pyo.SolverFactory("gurobi")
solver.solve(model, tee=True)

# =====================================================
# POST-PROCESSING（无 smoothing）
# =====================================================

price_1 = np.array([Price_buy_raw[1][t] for t in T])
price_2 = np.array([Price_buy_raw[2][t] for t in T])
price_diff = price_1 - price_2

net_trade = np.array([
    pyo.value(model.E_ex_12[t]) - pyo.value(model.E_ex_21[t])
    for t in T
])

netload_1 = Load[1][:168] - PV[1][:168]
netload_2 = Load[2][:168] - PV[2][:168]



# =====================================================
# Fig.3+ Price (3 subplots): Net load (+exchange) + price diff + two prices
# =====================================================
fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True)

# (1) Net load + Net energy exchange (叠加到同一张图)
axes[0].plot(hours, netload_1, label="Net Load M1", color="#d62728")
axes[0].plot(hours, netload_2, label="Net Load M2", color="#1f77b4")
axes[0].plot(hours, net_trade, color="black", linestyle="--", linewidth=2,
             label="Net Energy Exchange (1 → 2)")
axes[0].axhline(0, linestyle="--", color="gray")
axes[0].set_ylabel("Energy (kWh)")
axes[0].legend(frameon=False)
axes[0].set_title("Hourly Physical–Economic–Trading Relationship")

# (2) Price difference
axes[1].plot(hours, price_diff, color="purple", label="Price Difference (P1 − P2)")
axes[1].axhline(0, linestyle="--", color="gray")
axes[1].set_ylabel("Price Diff (€/kWh)")
axes[1].legend(frameon=False)

# (3) Two locations' prices
axes[2].step(hours, price_1, where="post", label="Price Area 1", color="#d62728")
axes[2].step(hours, price_2, where="post", label="Price Area 2", color="#1f77b4")
axes[2].set_ylabel("Price (€/kWh)")
axes[2].set_xlabel("Hour")
axes[2].legend(frameon=False, ncol=2)

plt.tight_layout()

for ax in axes:
    ax.grid(axis="y", linestyle="--", alpha=0.3)

plt.tight_layout()
plt.savefig("Fig3_hourly_price_netload_exchange.png", dpi=300, bbox_inches="tight")
plt.close()
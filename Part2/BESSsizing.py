import pyomo.environ as pyo
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =====================================================
# 1. 数据读取
# =====================================================
def read_load_csv(path):
    df = pd.read_csv(path, comment="#", sep=",")
    return df["total_demand"].astype(float).values * 1000  # kWh

def read_pv_csv(path):
    df = pd.read_csv(path, comment="#", sep=",")
    return df["electricity"].astype(float).values * 1000   # kWh

def read_price_excel(path):
    df = pd.read_excel(path, header=None, decimal=",")
    return df.iloc[:, 1].astype(float).values              # €/kWh


# =====================================================
# 2. 数据
# =====================================================
T = range(168)
hours = np.arange(168)

Load = {
    1: read_load_csv("Load_Haotian.csv"),
    2: read_price_excel("load.xlsx")   # NOTE: 这里沿用你原代码；若 load.xlsx 是负荷表，请改成正确读取方式
}

PV = {
    1: read_pv_csv("PV_Haotian.csv"),
    2: read_pv_csv("PV_Travis.csv")
}

Price = {
    1: read_price_excel("Priceoctopus.xlsx"),
    2: read_price_excel("Pricesomenergia.xlsx")
}

# =====================================================
# 3. BESS 参数（容量在优化中决定）
# =====================================================
P_CAP = {1: 500,  2: 500}    # kW (用每小时kWh表示，等价kW)
ETA_CH = 0.95
ETA_DIS = 0.95
SOC_INIT_FRAC = 0.5          # 初始SOC占比（50%）

E_CAP_MAX = {1: 10000, 2: 10000}  # kWh，可自行调整（例如 10MWh）

# 电池容量成本（每周成本）
c_E_week = 0.2   # €/kWh-week

# =====================================================
# ✅ 新增：交换上限（线路容量）
# 单位：kWh/h（因为每个时间步是1小时，所以也等价 kW）
# =====================================================
EX_CAP = 300.0   # 例如 300 kWh/h，可自行调整


# =====================================================
# 4. Pyomo 模型
# =====================================================
model = pyo.ConcreteModel()
model.M = pyo.Set(initialize=[1, 2])
model.T = pyo.Set(initialize=T)

model.Price = pyo.Param(
    model.M, model.T,
    initialize=lambda m, i, t: Price[i][t],
    within=pyo.NonNegativeReals
)

model.E_cap = pyo.Var(model.M, within=pyo.NonNegativeReals)

model.E_grid_buy  = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)
model.E_grid_sell = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)
model.E_ex_12 = pyo.Var(model.T, within=pyo.NonNegativeReals)
model.E_ex_21 = pyo.Var(model.T, within=pyo.NonNegativeReals)

model.E_ch  = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)
model.E_dis = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)
model.SOC   = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)

# =====================================================
# 5. 约束
# =====================================================
model.cap_upper = pyo.Constraint(model.M, rule=lambda m, i: m.E_cap[i] <= E_CAP_MAX[i])

def soc_balance(m, i, t):
    if t == 0:
        return m.SOC[i, t] == SOC_INIT_FRAC * m.E_cap[i]
    return (
        m.SOC[i, t]
        == m.SOC[i, t-1]
        + ETA_CH * m.E_ch[i, t]
        - (1 / ETA_DIS) * m.E_dis[i, t]
    )

model.soc_balance = pyo.Constraint(model.M, model.T, rule=soc_balance)

model.soc_limit = pyo.Constraint(
    model.M, model.T,
    rule=lambda m, i, t: m.SOC[i, t] <= m.E_cap[i]
)

model.p_ch = pyo.Constraint(
    model.M, model.T,
    rule=lambda m, i, t: m.E_ch[i, t] <= P_CAP[i]
)

model.p_dis = pyo.Constraint(
    model.M, model.T,
    rule=lambda m, i, t: m.E_dis[i, t] <= P_CAP[i]
)

# =====================================================
# ✅ 新增：交换上限约束（1->2 与 2->1 都受限）
# =====================================================
model.ex12_cap = pyo.Constraint(model.T, rule=lambda m, t: m.E_ex_12[t] <= EX_CAP)
model.ex21_cap = pyo.Constraint(model.T, rule=lambda m, t: m.E_ex_21[t] <= EX_CAP)

def balance_m1(m, t):
    return (
        PV[1][t]
        + m.E_grid_buy[1, t]
        + m.E_ex_21[t]
        + m.E_dis[1, t]
        ==
        Load[1][t]
        + m.E_grid_sell[1, t]
        + m.E_ex_12[t]
        + m.E_ch[1, t]
    )

def balance_m2(m, t):
    return (
        PV[2][t]
        + m.E_grid_buy[2, t]
        + m.E_ex_12[t]
        + m.E_dis[2, t]
        ==
        Load[2][t]
        + m.E_grid_sell[2, t]
        + m.E_ex_21[t]
        + m.E_ch[2, t]
    )

model.balance_m1 = pyo.Constraint(model.T, rule=balance_m1)
model.balance_m2 = pyo.Constraint(model.T, rule=balance_m2)

# （可选）期末SOC回到初始SOC：需要时取消注释
model.soc_terminal = pyo.Constraint(
    model.M,
     rule=lambda m, i: m.SOC[i, 167] == SOC_INIT_FRAC * m.E_cap[i]
)

# =====================================================
# 6. 目标函数（能量成本 + 电池容量成本）
# =====================================================
def total_cost(m):
    energy_cost = sum(
        m.Price[i, t] * m.E_grid_buy[i, t]
        - 0.5 * m.Price[i, t] * m.E_grid_sell[i, t]
        for i in m.M for t in m.T
    )
    cap_cost = sum(c_E_week * m.E_cap[i] for i in m.M)
    return energy_cost + cap_cost

model.obj = pyo.Objective(rule=total_cost, sense=pyo.minimize)

# =====================================================
# 7. 求解
# =====================================================
solver = pyo.SolverFactory("gurobi")
solver.solve(model, tee=True)

print("Model solved successfully.")
print("Optimized E_cap (kWh):", {i: float(pyo.value(model.E_cap[i])) for i in model.M})

# =====================================================
# 8. 后处理
# =====================================================
Load_1 = Load[1][:168]
Load_2 = Load[2][:168]
PV_1 = PV[1][:168]
PV_2 = PV[2][:168]

netload_1 = Load_1 - PV_1 + np.array([
    pyo.value(model.E_ch[1, t]) - pyo.value(model.E_dis[1, t])
    for t in T
])

netload_2 = Load_2 - PV_2 + np.array([
    pyo.value(model.E_ch[2, t]) - pyo.value(model.E_dis[2, t])
    for t in T
])

bess_power_1 = np.array([
    pyo.value(model.E_dis[1, t]) - pyo.value(model.E_ch[1, t])
    for t in T
])

bess_power_2 = np.array([
    pyo.value(model.E_dis[2, t]) - pyo.value(model.E_ch[2, t])
    for t in T
])

soc_1 = np.array([pyo.value(model.SOC[1, t]) for t in T])
soc_2 = np.array([pyo.value(model.SOC[2, t]) for t in T])

price_1 = np.array([Price[1][t] for t in T])
price_2 = np.array([Price[2][t] for t in T])
price_diff = price_1 - price_2

net_trade = np.array([
    pyo.value(model.E_ex_12[t]) - pyo.value(model.E_ex_21[t])
    for t in T
])

Ecap1 = float(pyo.value(model.E_cap[1]))
Ecap2 = float(pyo.value(model.E_cap[2]))

# =====================================================
# 9. 因果链图（把 net_trade 放到 netload 图里）
# =====================================================
fig, axes = plt.subplots(
    5, 1,
    figsize=(15, 13),
    sharex=True,
    gridspec_kw={"height_ratios": [1.2, 1.0, 1.0, 1.0, 1.2]}
)

# (0) Net load + Net energy exchange（叠加）
axes[0].plot(hours, netload_1, label="Net Load Area 1", color="#d62728", linewidth=1.8)
axes[0].plot(hours, netload_2, label="Net Load Area 2", color="#1f77b4", linewidth=1.8)
axes[0].plot(hours, net_trade, color="black", linewidth=2.0, linestyle="--",
             label="Net Energy Exchange (1 → 2)")
axes[0].axhline(0, color="gray", linestyle="--")
axes[0].set_ylabel("Energy (kWh)")
axes[0].legend(frameon=False)
axes[0].set_title("Price – BESS – Net Load – Trading Causal Chain (E_cap optimized, EX capped)")

# (1) BESS power
axes[1].plot(hours, bess_power_1, label="BESS Power Area 1", color="#d62728")
axes[1].plot(hours, bess_power_2, label="BESS Power Area 2", color="#1f77b4")
axes[1].axhline(0, color="gray", linestyle="--")
axes[1].set_ylabel("Battery Power (kW)")
axes[1].legend(frameon=False)

# (2) SOC
axes[2].plot(hours, soc_1, label="SOC Area 1", color="#d62728", linewidth=1.6)
axes[2].plot(hours, soc_2, label="SOC Area 2", color="#1f77b4", linewidth=1.6)
axes[2].axhline(Ecap1, color="#d62728", linestyle=":", alpha=0.8, label="E_cap Area 1")
axes[2].axhline(Ecap2, color="#1f77b4", linestyle=":", alpha=0.8, label="E_cap Area 2")
axes[2].axhline(0, color="gray", linestyle="--", alpha=0.6)
axes[2].set_ylabel("SOC (kWh)")
axes[2].legend(frameon=False, ncol=2)

# (3) Price diff
axes[3].plot(hours, price_diff, color="purple", linewidth=1.6,
             label="Price Difference (P1 − P2)")
axes[3].axhline(0, color="gray", linestyle="--")
axes[3].set_ylabel("€/kWh")
axes[3].legend(frameon=False)

# (4) Two prices
axes[4].step(hours, price_1, where="post", label="Price Area 1", color="#d62728")
axes[4].step(hours, price_2, where="post", label="Price Area 2", color="#1f77b4")
axes[4].set_ylabel("Price (€/kWh)")
axes[4].set_xlabel("Hour")
axes[4].legend(frameon=False, ncol=2)

for ax in axes:
    ax.grid(axis="y", linestyle="--", alpha=0.25)

plt.tight_layout()
plt.show()


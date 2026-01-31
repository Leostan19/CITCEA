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
    2: read_price_excel("load.xlsx")
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
# 3. BESS 参数
# =====================================================
E_CAP = {1: 1000, 2: 500}   # kWh
P_CAP = {1: 400,  2: 200}    # kW (用每小时kWh表示，等价kW)
ETA_CH = 0.95
ETA_DIS = 0.95
SOC_INIT_FRAC = 0.5          # 初始SOC占比（50%）


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

# 决策变量
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
def soc_balance(m, i, t):
    # 初始SOC = 50% * 容量
    if t == 0:
        return m.SOC[i, t] == SOC_INIT_FRAC * E_CAP[i]
    return (
        m.SOC[i, t]
        == m.SOC[i, t-1]
        + ETA_CH * m.E_ch[i, t]
        - (1 / ETA_DIS) * m.E_dis[i, t]
    )

model.soc_balance = pyo.Constraint(model.M, model.T, rule=soc_balance)

model.soc_limit = pyo.Constraint(
    model.M, model.T,
    rule=lambda m, i, t: m.SOC[i, t] <= E_CAP[i]
)

model.p_ch = pyo.Constraint(
    model.M, model.T,
    rule=lambda m, i, t: m.E_ch[i, t] <= P_CAP[i]
)

model.p_dis = pyo.Constraint(
    model.M, model.T,
    rule=lambda m, i, t: m.E_dis[i, t] <= P_CAP[i]
)

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

# -----------------------------------------------------
# （可选）期末SOC回到初始SOC：如果以后需要，取消注释即可
# -----------------------------------------------------
model.soc_terminal = pyo.Constraint(
      model.M,
      rule=lambda m, i: m.SOC[i, 167] == SOC_INIT_FRAC * E_CAP[i]
)

# =====================================================
# 6. 目标函数
# =====================================================
def total_cost(m):
    return sum(
        m.Price[i, t] * m.E_grid_buy[i, t]
        - 0.5 * m.Price[i, t] * m.E_grid_sell[i, t]
        for i in m.M for t in m.T
    )

model.obj = pyo.Objective(rule=total_cost, sense=pyo.minimize)

# =====================================================
# 7. 求解
# =====================================================
solver = pyo.SolverFactory("gurobi")
solver.solve(model, tee=True)

print("Model solved successfully.")

# =====================================================
# 8. 后处理
# =====================================================
Load_1 = Load[1][:168]
Load_2 = Load[2][:168]
PV_1 = PV[1][:168]
PV_2 = PV[2][:168]

# 电池调度后的等效净负荷：Load - PV + (充电 - 放电)
netload_1 = Load_1 - PV_1 + np.array([
    pyo.value(model.E_ch[1, t]) - pyo.value(model.E_dis[1, t])
    for t in T
])

netload_2 = Load_2 - PV_2 + np.array([
    pyo.value(model.E_ch[2, t]) - pyo.value(model.E_dis[2, t])
    for t in T
])

# 电池功率：放电为正、充电为负（每小时kWh等价kW）
bess_power_1 = np.array([
    pyo.value(model.E_dis[1, t]) - pyo.value(model.E_ch[1, t])
    for t in T
])

bess_power_2 = np.array([
    pyo.value(model.E_dis[2, t]) - pyo.value(model.E_ch[2, t])
    for t in T
])

# SOC
soc_1 = np.array([pyo.value(model.SOC[1, t]) for t in T])
soc_2 = np.array([pyo.value(model.SOC[2, t]) for t in T])

# 价格与价差
price_1 = np.array([Price[1][t] for t in T])
price_2 = np.array([Price[2][t] for t in T])
price_diff = price_1 - price_2

# 净交易（1->2为正）
net_trade = np.array([
    pyo.value(model.E_ex_12[t]) - pyo.value(model.E_ex_21[t])
    for t in T
])

# =====================================================
# 9. 因果链图（把 net_trade 放到 Net load 图里，删掉 exchange 子图）
# =====================================================
fig, axes = plt.subplots(
    5, 1,
    figsize=(15, 13),
    sharex=True,
    gridspec_kw={"height_ratios": [1.2, 1.0, 1.0, 1.0, 1.2]}
)

# (1) Net load + Net energy exchange（叠加）
axes[0].plot(hours, netload_1, label="Net Load Area 1", color="#d62728", linewidth=1.8)
axes[0].plot(hours, netload_2, label="Net Load Area 2", color="#1f77b4", linewidth=1.8)
axes[0].plot(hours, net_trade, color="black", linewidth=2.0, linestyle="--",
             label="Net Energy Exchange (1 → 2)")
axes[0].axhline(0, color="gray", linestyle="--")
axes[0].set_ylabel("Energy (kWh)")
axes[0].legend(frameon=False)
axes[0].set_title("Price – BESS – Net Load – Trading Causal Chain")

# (2) Battery power
axes[1].plot(hours, bess_power_1, label="BESS Power Area 1", color="#d62728")
axes[1].plot(hours, bess_power_2, label="BESS Power Area 2", color="#1f77b4")
axes[1].axhline(0, color="gray", linestyle="--")
axes[1].set_ylabel("Battery Power (kW)")
axes[1].legend(frameon=False)

# (3) SOC
axes[2].plot(hours, soc_1, label="SOC Area 1", color="#d62728", linewidth=1.6)
axes[2].plot(hours, soc_2, label="SOC Area 2", color="#1f77b4", linewidth=1.6)
axes[2].axhline(0, color="gray", linestyle="--", alpha=0.6)
axes[2].set_ylabel("SOC (kWh)")
axes[2].legend(frameon=False)

# (4) Price difference
axes[3].plot(hours, price_diff, color="purple", linewidth=1.6,
             label="Price Difference (P1 − P2)")
axes[3].axhline(0, color="gray", linestyle="--")
axes[3].set_ylabel("€/kWh")
axes[3].legend(frameon=False)

# (5) Two locations' prices
axes[4].step(hours, price_1, where="post", label="Price Area 1", color="#d62728")
axes[4].step(hours, price_2, where="post", label="Price Area 2", color="#1f77b4")
axes[4].set_ylabel("Price (€/kWh)")
axes[4].set_xlabel("Hour")
axes[4].legend(frameon=False, ncol=2)

for ax in axes:
    ax.grid(axis="y", linestyle="--", alpha=0.25)

plt.tight_layout()
plt.show()

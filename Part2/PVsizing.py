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
    # PV输入是每小时能量 MWh -> kWh
    return df["electricity"].astype(float).values * 1000   # kWh

def read_series_excel_col2(path):
    # 读取excel第2列数值（你用来读load.xlsx和price.xlsx都行）
    df = pd.read_excel(path, header=None, decimal=",")
    return df.iloc[:, 1].astype(float).values

# =====================================================
# 2. 数据
# =====================================================
T = range(168)
hours = np.arange(168)

Load = {
    1: read_load_csv("Load_Haotian.csv"),
    2: read_series_excel_col2("load.xlsx")*1000  # 你确认这里是负荷序列（单位需与你的模型一致：kWh/小时）
}

PV_base = {
    1: read_pv_csv("PV_Haotian.csv"),
    2: read_pv_csv("PV_Travis.csv")
}

Price_buy_raw = {
    1: read_series_excel_col2("Priceoctopus.xlsx"),
    2: read_series_excel_col2("Pricesomenergia.xlsx")
}

# 显式切片到168
Load_1 = Load[1][:168]
Load_2 = Load[2][:168]
PVb_1 = PV_base[1][:168]
PVb_2 = PV_base[2][:168]

# 仅用于 big-M（卖电门控上界）
pv_energy_peak_1 = float(np.max(PVb_1))  # kWh/h
pv_energy_peak_2 = float(np.max(PVb_2))  # kWh/h

# =====================================================
# 3. 参数设置
# =====================================================
PV_SCALE_MAX = {1: 5.0, 2: 5.0}     # 最大安装比例=1
c_PV_kw_week = 0.2                 # €/kW-week（你可调）
EX_CAP = 300.0                     # kWh/h (=kW)

# ✅ 安装容量基准（kW）：你的PV时序对应的“基准装机容量”
# 如果你的PV序列是 1MW 装机对应的时序：填 1000
PV_CAP_BASE_KW = {1: 1000.0, 2: 1000.0}

# ✅ 安装容量阈值：>700 kW 禁止卖电
PV_SELL_THRESHOLD_KW = 700.0

# big-M：卖电门控上界（当允许卖电时，每小时卖电最多不超过该小时PV发电）
M_sell = {1: pv_energy_peak_1 * PV_SCALE_MAX[1], 2: pv_energy_peak_2 * PV_SCALE_MAX[2]}

# big-M：容量门控上界（最大可能安装容量）
M_cap = {i: PV_CAP_BASE_KW[i] * PV_SCALE_MAX[i] for i in [1, 2]}

# =====================================================
# 4. Pyomo 模型（无 BESS）
# =====================================================
model = pyo.ConcreteModel()
model.M = pyo.Set(initialize=[1, 2])
model.T = pyo.Set(initialize=T)

model.Price_buy = pyo.Param(
    model.M, model.T,
    initialize=lambda m, i, t: float(Price_buy_raw[i][t]),
    within=pyo.NonNegativeReals
)

# =====================================================
# 5. 决策变量
# =====================================================
model.E_grid_buy  = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)
model.E_grid_sell = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)
model.E_ex_12     = pyo.Var(model.T, within=pyo.NonNegativeReals)
model.E_ex_21     = pyo.Var(model.T, within=pyo.NonNegativeReals)

# PV sizing：装机比例（无单位）
model.PV_scale = pyo.Var(model.M, within=pyo.NonNegativeReals)

# 是否允许卖电（二进制）：1允许卖电；0禁止卖电
model.sell_allowed = pyo.Var(model.M, within=pyo.Binary)

# =====================================================
# 6. PV scale 上限
# =====================================================
model.pv_scale_limit = pyo.Constraint(
    model.M,
    rule=lambda m, i: m.PV_scale[i] <= PV_SCALE_MAX[i]
)

# PV发电（kWh）：PV_gen = PV_scale * PV_base
def pv_gen_expr(m, i, t):
    if i == 1:
        return m.PV_scale[i] * float(PVb_1[t])
    else:
        return m.PV_scale[i] * float(PVb_2[t])

model.PV_gen = pyo.Expression(model.M, model.T, rule=pv_gen_expr)

# ✅ 安装容量（kW）：PV_cap_installed = PV_scale * PV_CAP_BASE_KW
def pv_cap_installed_expr(m, i):
    return m.PV_scale[i] * PV_CAP_BASE_KW[i]

model.PV_cap_installed = pyo.Expression(model.M, rule=pv_cap_installed_expr)

# =====================================================
# 7. exchange 上限约束（300）
# =====================================================
model.ex12_cap = pyo.Constraint(model.T, rule=lambda m, t: m.E_ex_12[t] <= EX_CAP)
model.ex21_cap = pyo.Constraint(model.T, rule=lambda m, t: m.E_ex_21[t] <= EX_CAP)

# =====================================================
# 8. “安装容量>700kW 禁止卖电”逻辑约束
# 若 sell_allowed=1，则 installed_cap <= 700；
# 若 installed_cap > 700，则 sell_allowed 必须=0
# =====================================================
def sell_rule(m, i):
    return m.PV_cap_installed[i] <= PV_SELL_THRESHOLD_KW + M_cap[i] * (1 - m.sell_allowed[i])

model.sell_threshold = pyo.Constraint(model.M, rule=sell_rule)

# 卖电受控：
# - 永远不能卖超过当小时PV发电量
# - sell_allowed=0 时 E_grid_sell=0
model.sell_from_pv = pyo.Constraint(model.M, model.T, rule=lambda m, i, t: m.E_grid_sell[i, t] <= m.PV_gen[i, t])
model.sell_gate    = pyo.Constraint(model.M, model.T, rule=lambda m, i, t: m.E_grid_sell[i, t] <= M_sell[i] * m.sell_allowed[i])

# =====================================================
# 9. 能量平衡（无BESS）
# =====================================================
def balance_m1(m, t):
    return (
        m.PV_gen[1, t]
        + m.E_grid_buy[1, t]
        + m.E_ex_21[t]
        ==
        Load_1[t]
        + m.E_grid_sell[1, t]
        + m.E_ex_12[t]
    )

def balance_m2(m, t):
    return (
        m.PV_gen[2, t]
        + m.E_grid_buy[2, t]
        + m.E_ex_12[t]
        ==
        Load_2[t]
        + m.E_grid_sell[2, t]
        + m.E_ex_21[t]
    )

model.balance_m1 = pyo.Constraint(model.T, rule=balance_m1)
model.balance_m2 = pyo.Constraint(model.T, rule=balance_m2)

# =====================================================
# 10. 目标函数（电费成本 + PV容量成本(按安装容量kW计费)）
# =====================================================
def total_cost(m):
    energy_cost = sum(
        m.Price_buy[i, t] * m.E_grid_buy[i, t]
        - 0.5 * m.Price_buy[i, t] * m.E_grid_sell[i, t]
        for i in m.M for t in m.T
    )
    pv_cost = c_PV_kw_week * sum(m.PV_cap_installed[i] for i in m.M)
    return energy_cost + pv_cost

model.obj = pyo.Objective(rule=total_cost, sense=pyo.minimize)

# =====================================================
# 11. 求解
# =====================================================
solver = pyo.SolverFactory("gurobi")
solver.solve(model, tee=True)

pv_scale_sol = {i: float(pyo.value(model.PV_scale[i])) for i in model.M}
pv_cap_inst_sol = {i: float(pyo.value(model.PV_cap_installed[i])) for i in model.M}
sell_allowed_sol = {i: int(round(pyo.value(model.sell_allowed[i]))) for i in model.M}

print("Model solved successfully.")
print("Optimized PV_scale:", pv_scale_sol)
print("Installed PV capacity (kW):", pv_cap_inst_sol)
print("sell_allowed (1=can sell, 0=cannot):", sell_allowed_sol)
print(f"Exchange cap EX_CAP = {EX_CAP} kWh/h; Sell forbidden if Installed PV > {PV_SELL_THRESHOLD_KW} kW")
print(f"PV_CAP_BASE_KW = {PV_CAP_BASE_KW}, PV_SCALE_MAX = {PV_SCALE_MAX}")

# =====================================================
# 12. 后处理 & 画图（保留你之前三张图）
# =====================================================
price_1 = np.array([Price_buy_raw[1][t] for t in T])
price_2 = np.array([Price_buy_raw[2][t] for t in T])
price_diff = price_1 - price_2

PV_1_opt = np.array([pyo.value(model.PV_gen[1, t]) for t in T])
PV_2_opt = np.array([pyo.value(model.PV_gen[2, t]) for t in T])

net_trade = np.array([
    pyo.value(model.E_ex_12[t]) - pyo.value(model.E_ex_21[t])
    for t in T
])

netload_1 = Load_1 - PV_1_opt
netload_2 = Load_2 - PV_2_opt



fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True)

# (0) Net load + Net energy exchange
axes[0].plot(hours, netload_1, label="Net Load Area 1 (Load - PV)", color="#d62728")
axes[0].plot(hours, netload_2, label="Net Load Area 2 (Load - PV)", color="#1f77b4")
axes[0].plot(hours, net_trade, color="black", lw=2.0, ls="--",
             label="Net Energy Exchange (1 → 2)")
axes[0].axhline(0, linestyle="--", color="gray")
axes[0].set_ylabel("Energy (kWh)")
axes[0].legend(frameon=False)
axes[0].set_title("Hourly Physical–Economic–Trading Relationship (PV sizing + installed-cap rule)")

# (1) Price difference
axes[1].plot(hours, price_diff, color="purple", label="Price Difference (P1 − P2)")
axes[1].axhline(0, linestyle="--", color="gray")
axes[1].set_ylabel("€/kWh")
axes[1].legend(frameon=False)

# (2) Two locations' prices
axes[2].step(hours, price_1, where="post", color="#d62728", label="Price Area 1")
axes[2].step(hours, price_2, where="post", color="#1f77b4", label="Price Area 2")
axes[2].set_ylabel("Price (€/kWh)")
axes[2].set_xlabel("Hour")
axes[2].legend(frameon=False, ncol=2)

for ax in axes:
    ax.grid(axis="y", linestyle="--", alpha=0.3)

plt.tight_layout()
plt.savefig("Fig3_hourly_netload_price_exchange_PVsizing_instcap_rule.png", dpi=300, bbox_inches="tight")
plt.show()

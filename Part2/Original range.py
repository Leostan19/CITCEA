import pyomo.environ as pyo
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =========================
# 1) 读取数据
# =========================
def read_load_csv_mwh(path):
    df = pd.read_csv(path, comment="#", sep=",")
    return df["total_demand"].astype(float).values  # MWh per hour

def read_pv_csv_mwh(path):
    df = pd.read_csv(path, comment="#", sep=",")
    return df["electricity"].astype(float).values   # MWh per hour

def read_excel_col2(path):
    df = pd.read_excel(path, header=None, decimal=",")
    return df.iloc[:, 1].astype(float).values

T = range(168)
hours = np.arange(168)

# 统一成 kWh/h
Load = {
    1: read_load_csv_mwh("Load_Haotian.csv") * 1000,
    2: read_excel_col2("load.xlsx") * 1000
}
PV = {
    1: read_pv_csv_mwh("PV_Haotian.csv") * 1000,
    2: read_pv_csv_mwh("PV_Travis.csv") * 1000
}
Price_buy_raw = {
    1: read_excel_col2("Priceoctopus.xlsx"),      # €/kWh
    2: read_excel_col2("Pricesomenergia.xlsx")    # €/kWh
}

alpha_sell = 0.5  # grid sell price = alpha_sell * grid buy price

# Big-M（合理上界）
max_energy = float(max(np.max(Load[1][:168]), np.max(Load[2][:168]), np.max(PV[1][:168]), np.max(PV[2][:168])))
M_flow = 2.0 * max_energy + 1.0
M_price = 10.0  # 足够大即可

# =========================
# 2) Pyomo 模型
# =========================
m = pyo.ConcreteModel()
m.M = pyo.Set(initialize=[1, 2])
m.T = pyo.Set(initialize=T)

m.Pbuy = pyo.Param(m.M, m.T, initialize=lambda mm, i, t: float(Price_buy_raw[i][t]), within=pyo.NonNegativeReals)

# 决策变量
m.E_grid_buy  = pyo.Var(m.M, m.T, within=pyo.NonNegativeReals)
m.E_grid_sell = pyo.Var(m.M, m.T, within=pyo.NonNegativeReals)
m.E_ex_12     = pyo.Var(m.T, within=pyo.NonNegativeReals)
m.E_ex_21     = pyo.Var(m.T, within=pyo.NonNegativeReals)

# 交换价 + 方向（二进制）
m.p_ex = pyo.Var(m.T, within=pyo.NonNegativeReals)
m.y12  = pyo.Var(m.T, within=pyo.Binary)
m.y21  = pyo.Var(m.T, within=pyo.Binary)

# 能量平衡
def balance_1(mm, t):
    return PV[1][t] + mm.E_grid_buy[1, t] + mm.E_ex_21[t] == Load[1][t] + mm.E_grid_sell[1, t] + mm.E_ex_12[t]
def balance_2(mm, t):
    return PV[2][t] + mm.E_grid_buy[2, t] + mm.E_ex_12[t] == Load[2][t] + mm.E_grid_sell[2, t] + mm.E_ex_21[t]

m.balance1 = pyo.Constraint(m.T, rule=balance_1)
m.balance2 = pyo.Constraint(m.T, rule=balance_2)

# 互换：同一小时最多一个方向 + 流量门控
m.one_dir = pyo.Constraint(m.T, rule=lambda mm, t: mm.y12[t] + mm.y21[t] <= 1)
m.gate12  = pyo.Constraint(m.T, rule=lambda mm, t: mm.E_ex_12[t] <= M_flow * mm.y12[t])
m.gate21  = pyo.Constraint(m.T, rule=lambda mm, t: mm.E_ex_21[t] <= M_flow * mm.y21[t])

# “双方同意”的价格区间（individual rationality）
# 1->2: 0.5*P1 <= p_ex <= P2
m.p12_low  = pyo.Constraint(m.T, rule=lambda mm, t: mm.p_ex[t] >= alpha_sell*mm.Pbuy[1, t] - M_price*(1-mm.y12[t]))
m.p12_high = pyo.Constraint(m.T, rule=lambda mm, t: mm.p_ex[t] <=              mm.Pbuy[2, t] + M_price*(1-mm.y12[t]))
# 2->1: 0.5*P2 <= p_ex <= P1
m.p21_low  = pyo.Constraint(m.T, rule=lambda mm, t: mm.p_ex[t] >= alpha_sell*mm.Pbuy[2, t] - M_price*(1-mm.y21[t]))
m.p21_high = pyo.Constraint(m.T, rule=lambda mm, t: mm.p_ex[t] <=              mm.Pbuy[1, t] + M_price*(1-mm.y21[t]))

# 目标：系统总电网成本（内部交易不计入系统成本）
def obj(mm):
    return sum(
        mm.Pbuy[i, t] * mm.E_grid_buy[i, t] - alpha_sell * mm.Pbuy[i, t] * mm.E_grid_sell[i, t]
        for i in mm.M for t in mm.T
    )
m.obj = pyo.Objective(rule=obj, sense=pyo.minimize)

# =========================
# 3) 求解
# =========================
pyo.SolverFactory("gurobi").solve(m, tee=True)

# =========================
# 4) 后处理 + 画“唯一一张图”
# =========================
price_1 = np.array([Price_buy_raw[1][t] for t in T], float)
price_2 = np.array([Price_buy_raw[2][t] for t in T], float)
sell_1  = alpha_sell * price_1
sell_2  = alpha_sell * price_2

ex12 = np.array([pyo.value(m.E_ex_12[t]) for t in T], float)
ex21 = np.array([pyo.value(m.E_ex_21[t]) for t in T], float)
net_trade = ex12 - ex21

p_ex = np.array([pyo.value(m.p_ex[t]) for t in T], float)
mask_trade = (ex12 > 1e-6) | (ex21 > 1e-6)

netload_1 = Load[1][:168] - PV[1][:168]
netload_2 = Load[2][:168] - PV[2][:168]
price_diff = price_1 - price_2

# ✅ 理论可行区间（只要区间非空就画）
low_12, high_12 = alpha_sell*price_1, price_2
low_21, high_21 = alpha_sell*price_2, price_1
mask_12_band = high_12 >= low_12
mask_21_band = high_21 >= low_21

# —— 从 4 行改成 3 行（删掉 exchange 的独立子图）——
fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True)

# (1) Net load + Net energy exchange（叠加进来）
axes[0].plot(hours, netload_1, label="Net Load M1 (Load - PV)", color="#d62728")
axes[0].plot(hours, netload_2, label="Net Load M2 (Load - PV)", color="#1f77b4")
axes[0].plot(hours, net_trade, color="black", lw=1.8, ls="--",
             label="Net Energy Exchange (1 -> 2)")
axes[0].axhline(0, ls="--", c="gray")
axes[0].set_ylabel("Energy (kWh)")
axes[0].legend(frameon=False)
axes[0].set_title("Mutual-consent exchange (clean version)")

# (2) Price difference
axes[1].plot(hours, price_diff, color="purple", label="Price Difference (P1 - P2)")
axes[1].axhline(0, ls="--", c="gray")
axes[1].set_ylabel("€/kWh")
axes[1].legend(frameon=False)

# (3) Prices + feasible bands
axes[2].step(hours, price_1, where="post", label="Price Area 1 (buy)", color="#d62728", lw=1.2)
axes[2].step(hours, price_2, where="post", label="Price Area 2 (buy)", color="#1f77b4", lw=1.2)
axes[2].step(hours, sell_1,  where="post", ls="--", label="Price Area 1 (sell)", color="#d62728", alpha=0.85)
axes[2].step(hours, sell_2,  where="post", ls="--", label="Price Area 2 (sell)", color="#1f77b4", alpha=0.85)

axes[2].fill_between(hours, low_12, high_12, where=mask_12_band, step="post",
                     alpha=0.25, label="Feasible 1→2 (0.5·P1 .. P2)")
axes[2].fill_between(hours, low_21, high_21, where=mask_21_band, step="post",
                     alpha=0.25, label="Feasible 2→1 (0.5·P2 .. P1)")

axes[2].set_ylabel("Price (€/kWh)")
axes[2].set_xlabel("Hour")
axes[2].legend(frameon=False, ncol=2)
axes[2].grid(axis="y", ls="--", alpha=0.3)

# grid
for ax in axes[:2]:
    ax.grid(axis="y", ls="--", alpha=0.3)

plt.tight_layout()
plt.savefig("Fig_clean_mutual_consent.png", dpi=300, bbox_inches="tight")
plt.show()

print("Saved: Fig_clean_mutual_consent.png")

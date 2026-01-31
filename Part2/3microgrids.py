import pyomo.environ as pyo
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =====================================================
# 1. 数据读取（Excel / CSV）
# =====================================================
def read_load_csv(path: str) -> np.ndarray:
    df = pd.read_csv(path, comment="#", sep=",")
    return df.iloc[:, 1].astype(float).values  # MWh or (your column unit)

def read_pv_csv(path: str) -> np.ndarray:
    df = pd.read_csv(path, comment="#", sep=",")
    return df["electricity"].astype(float).values  # MWh

def read_price_excel(path: str) -> np.ndarray:
    df = pd.read_excel(path, header=None, decimal=",")
    return df.iloc[:, 1].astype(float).values  # €/kWh

# =====================================================
# 2. 数据 & 单位转换：MWh → kWh
# ✅ 第三个地点的 load 需要 /40
# =====================================================
Load = {
    1: read_load_csv("Load_Haotian.csv") * 1000,           # -> kWh
    2: read_price_excel("load.xlsx") * 1000,               # -> kWh (注意：这里你用的是 read_price_excel 读 load.xlsx，确认没写错)
    3: read_load_csv("LoadMadrid.csv") / 40.0,             # ✅ 这里按你的需求 /40（是否还要 *1000 取决于原始单位）
}

PV = {
    1: read_pv_csv("PV_Haotian.csv") * 1000,               # -> kWh
    2: read_pv_csv("PV_Travis.csv") * 1000,                # -> kWh
    3: read_pv_csv("MadridPV.csv") * 1000,                 # -> kWh
}

Price_buy_raw = {
    1: read_price_excel("Priceoctopus.xlsx"),
    2: read_price_excel("Pricesomenergia.xlsx"),
    3: read_price_excel("price_list_168.xlsx"),            # 168小时价格
}

# =====================================================
# 3. 时间集合（168 小时）
# =====================================================
T = range(168)
hours = np.array(list(T))

# =====================================================
# 4. Pyomo 模型（三方）
# =====================================================
model = pyo.ConcreteModel()

model.M = pyo.Set(initialize=[1, 2, 3])
model.T = pyo.Set(initialize=T)

# 方向弧集合：所有 i->j (i!=j)
model.A = pyo.Set(
    dimen=2,
    initialize=[(i, j) for i in model.M for j in model.M if i != j]
)

# 购电价参数
def price_init(m, i, t):
    return float(Price_buy_raw[i][t])

model.Price_buy = pyo.Param(
    model.M, model.T,
    initialize=price_init,
    within=pyo.NonNegativeReals
)

# =====================================================
# 5. 决策变量（kWh per hour）
# =====================================================
model.E_grid_buy = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)
model.E_grid_sell = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)

# 三方互换：E_ex[i,j,t] 表示 i -> j 的交换能量（非负）
model.E_ex = pyo.Var(model.A, model.T, within=pyo.NonNegativeReals)

# =====================================================
# 5.1 交换容量上限（可选）
# =====================================================
EX_CAP = 300.0  # kWh/h (=kW)

if EX_CAP is not None:
    def ex_cap_rule(m, i, j, t):
        return m.E_ex[i, j, t] <= EX_CAP

    model.ex_cap = pyo.Constraint(model.A, model.T, rule=ex_cap_rule)

# =====================================================
# 6. 能量平衡（三方）
# PV + grid_buy + sum_in = Load + grid_sell + sum_out
# =====================================================
def balance_rule(m, i, t):
    inflow = sum(m.E_ex[j, i, t] for j in m.M if j != i)
    outflow = sum(m.E_ex[i, j, t] for j in m.M if j != i)
    return PV[i][t] + m.E_grid_buy[i, t] + inflow == Load[i][t] + m.E_grid_sell[i, t] + outflow

model.balance = pyo.Constraint(model.M, model.T, rule=balance_rule)

# =====================================================
# 7. 目标函数（€）：购电成本 - 卖电收益(按0.5*买价)
# =====================================================
def total_cost(m):
    return sum(
        m.Price_buy[i, t] * m.E_grid_buy[i, t]
        - 0.5 * m.Price_buy[i, t] * m.E_grid_sell[i, t]
        for i in m.M for t in m.T
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
price = {i: np.array([Price_buy_raw[i][t] for t in T], dtype=float) for i in model.M}

# netload（物理净负荷，不包含交易）
netload = {i: Load[i][:168] - PV[i][:168] for i in model.M}

# 每个地点净交换：net_ex[i,t] = sum_out - sum_in （正=净出口）
net_ex = {}
for i in model.M:
    net_ex[i] = np.array(
        [
            sum(pyo.value(model.E_ex[i, j, t]) for j in model.M if j != i)
            - sum(pyo.value(model.E_ex[j, i, t]) for j in model.M if j != i)
            for t in T
        ],
        dtype=float
    )

# 价差（3条）
price_diff_12 = price[1] - price[2]
price_diff_13 = price[1] - price[3]
price_diff_23 = price[2] - price[3]

# =====================================================
# Fig. 3-party (3 subplots)
# 1) netload(3地) + net exchange(3地, 虚线)
# 2) price differences (3条)
# 3) three prices
# =====================================================
fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True)

# (1) Net load + Net exchange
axes[0].plot(hours, netload[1], label="Net Load M1", color="#d62728")
axes[0].plot(hours, netload[2], label="Net Load M2", color="#1f77b4")
axes[0].plot(hours, netload[3], label="Net Load M3", color="#2ca02c")

axes[0].plot(hours, net_ex[1], label="Net Exchange M1 (out-in)", color="#d62728", ls="--", lw=2.0, alpha=0.9)
axes[0].plot(hours, net_ex[2], label="Net Exchange M2 (out-in)", color="#1f77b4", ls="--", lw=2.0, alpha=0.9)
axes[0].plot(hours, net_ex[3], label="Net Exchange M3 (out-in)", color="#2ca02c", ls="--", lw=2.0, alpha=0.9)

axes[0].axhline(0, linestyle="--", color="gray")
axes[0].set_ylabel("Energy (kWh)")
axes[0].legend(frameon=False, ncol=2)
axes[0].set_title("3-party Physical–Economic–Trading Relationship")

# (2) Price differences
axes[1].plot(hours, price_diff_12, color="purple", label="P1 − P2")
axes[1].plot(hours, price_diff_13, color="brown", label="P1 − P3")
axes[1].plot(hours, price_diff_23, color="teal", label="P2 − P3")

axes[1].axhline(0, linestyle="--", color="gray")
axes[1].set_ylabel("Price Diff (€/kWh)")
axes[1].legend(frameon=False, ncol=3)

# (3) Three prices
axes[2].step(hours, price[1], where="post", label="Price Area 1", color="#d62728")
axes[2].step(hours, price[2], where="post", label="Price Area 2", color="#1f77b4")
axes[2].step(hours, price[3], where="post", label="Price Area 3", color="#2ca02c")

axes[2].set_ylabel("Price (€/kWh)")
axes[2].set_xlabel("Hour")
axes[2].legend(frameon=False, ncol=3)

for ax in axes:
    ax.grid(axis="y", linestyle="--", alpha=0.3)

plt.tight_layout()
plt.savefig("Fig3_hourly_price_netload_exchange_3party.png", dpi=300, bbox_inches="tight")
plt.show()

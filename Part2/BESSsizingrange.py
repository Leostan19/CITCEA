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
    2: read_price_excel("load.xlsx")   # NOTE: 沿用你原代码；你确认这里是负荷序列(并且单位与PV一致：kWh/h)
}

PV = {
    1: read_pv_csv("PV_Haotian.csv"),
    2: read_pv_csv("PV_Travis.csv")
}

Price = {
    1: read_price_excel("Priceoctopus.xlsx"),
    2: read_price_excel("Pricesomenergia.xlsx")
}

# 显式切片
Load_1 = Load[1][:168]
Load_2 = Load[2][:168]
PV_1 = PV[1][:168]
PV_2 = PV[2][:168]

# =====================================================
# 3. BESS 参数（容量在优化中决定）
# =====================================================
P_CAP = {1: 500,  2: 500}    # kW (每小时kWh等价kW)
ETA_CH = 0.95
ETA_DIS = 0.95
SOC_INIT_FRAC = 0.5          # 初始SOC占比（50%）

E_CAP_MAX = {1: 10000, 2: 10000}  # kWh，可调整

# 电池容量成本（每周成本）
c_E_week = 0.2   # €/kWh-week

# =====================================================
# 4. 交换参数
# =====================================================
EX_CAP = 300.0        # kWh/h (=kW) 线路容量上限
alpha_sell = 0.5      # 卖电给电网的折价系数（你目标函数里是0.5）
M_price = 10.0        # €/kWh big-M，电价一般不会超过这个数量级

# =====================================================
# 5. Pyomo 模型
# =====================================================
model = pyo.ConcreteModel()
model.M = pyo.Set(initialize=[1, 2])
model.T = pyo.Set(initialize=T)

model.Price = pyo.Param(
    model.M, model.T,
    initialize=lambda m, i, t: float(Price[i][t]),
    within=pyo.NonNegativeReals
)

# 决策：电池容量
model.E_cap = pyo.Var(model.M, within=pyo.NonNegativeReals)

# 能量变量
model.E_grid_buy  = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)
model.E_grid_sell = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)
model.E_ex_12 = pyo.Var(model.T, within=pyo.NonNegativeReals)
model.E_ex_21 = pyo.Var(model.T, within=pyo.NonNegativeReals)

# 电池变量
model.E_ch  = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)
model.E_dis = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)
model.SOC   = pyo.Var(model.M, model.T, within=pyo.NonNegativeReals)

# =====================================================
# ✅ 新增：交换必须双方同意（交换电价 + 方向开关）
# =====================================================
model.p_ex = pyo.Var(model.T, within=pyo.NonNegativeReals)  # €/kWh
model.y12  = pyo.Var(model.T, within=pyo.Binary)            # 1->2 是否启用
model.y21  = pyo.Var(model.T, within=pyo.Binary)            # 2->1 是否启用

# =====================================================
# 6. 约束
# =====================================================
# 电池容量上限
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

# SOC 上下限
model.soc_limit = pyo.Constraint(model.M, model.T, rule=lambda m, i, t: m.SOC[i, t] <= m.E_cap[i])

# 充放功率上限
model.p_ch  = pyo.Constraint(model.M, model.T, rule=lambda m, i, t: m.E_ch[i, t] <= P_CAP[i])
model.p_dis = pyo.Constraint(model.M, model.T, rule=lambda m, i, t: m.E_dis[i, t] <= P_CAP[i])

# =====================================================
# ✅ 交换物理上限（线路容量）
# =====================================================
model.ex12_cap = pyo.Constraint(model.T, rule=lambda m, t: m.E_ex_12[t] <= EX_CAP)
model.ex21_cap = pyo.Constraint(model.T, rule=lambda m, t: m.E_ex_21[t] <= EX_CAP)

# =====================================================
# ✅ 双方同意：同一小时最多一个方向 + 方向门控 + 价格区间门控
# =====================================================
# 同一小时最多一个方向
model.one_dir = pyo.Constraint(model.T, rule=lambda m, t: m.y12[t] + m.y21[t] <= 1)

# 流量门控（用 EX_CAP 做 big-M 更紧）
model.flow_gate12 = pyo.Constraint(model.T, rule=lambda m, t: m.E_ex_12[t] <= EX_CAP * m.y12[t])
model.flow_gate21 = pyo.Constraint(model.T, rule=lambda m, t: m.E_ex_21[t] <= EX_CAP * m.y21[t])

# 价格区间门控：
# 1->2：0.5*P1 <= p_ex <= P2
model.p12_low  = pyo.Constraint(model.T, rule=lambda m, t: m.p_ex[t] >= alpha_sell*m.Price[1, t] - M_price*(1 - m.y12[t]))
model.p12_high = pyo.Constraint(model.T, rule=lambda m, t: m.p_ex[t] <=              m.Price[2, t] + M_price*(1 - m.y12[t]))

# 2->1：0.5*P2 <= p_ex <= P1
model.p21_low  = pyo.Constraint(model.T, rule=lambda m, t: m.p_ex[t] >= alpha_sell*m.Price[2, t] - M_price*(1 - m.y21[t]))
model.p21_high = pyo.Constraint(model.T, rule=lambda m, t: m.p_ex[t] <=              m.Price[1, t] + M_price*(1 - m.y21[t]))

# 能量平衡
def balance_m1(m, t):
    return (
        PV_1[t]
        + m.E_grid_buy[1, t]
        + m.E_ex_21[t]
        + m.E_dis[1, t]
        ==
        Load_1[t]
        + m.E_grid_sell[1, t]
        + m.E_ex_12[t]
        + m.E_ch[1, t]
    )

def balance_m2(m, t):
    return (
        PV_2[t]
        + m.E_grid_buy[2, t]
        + m.E_ex_12[t]
        + m.E_dis[2, t]
        ==
        Load_2[t]
        + m.E_grid_sell[2, t]
        + m.E_ex_21[t]
        + m.E_ch[2, t]
    )

model.balance_m1 = pyo.Constraint(model.T, rule=balance_m1)
model.balance_m2 = pyo.Constraint(model.T, rule=balance_m2)

# （可选）期末SOC回到初始SOC：需要时取消注释
# model.soc_terminal = pyo.Constraint(
#     model.M,
#     rule=lambda m, i: m.SOC[i, 167] == SOC_INIT_FRAC * m.E_cap[i]
# )

# =====================================================
# 7. 目标函数（能量成本 + 电池容量成本）
# =====================================================
def total_cost(m):
    energy_cost = sum(
        m.Price[i, t] * m.E_grid_buy[i, t]
        - alpha_sell * m.Price[i, t] * m.E_grid_sell[i, t]
        for i in m.M for t in m.T
    )
    cap_cost = sum(c_E_week * m.E_cap[i] for i in m.M)

    # 极小 tie-break（不影响主目标，只在等价解时起作用）
    eps = 1e-6
    tie_break = eps * (
        sum(m.E_ex_12[t] + m.E_ex_21[t] for t in m.T) +  # 尽量少“无意义交换”
        sum(m.p_ex[t] for t in m.T)                      # 防止 p_ex 漂移
    )
    return energy_cost + cap_cost + tie_break

model.obj = pyo.Objective(rule=total_cost, sense=pyo.minimize)

# =====================================================
# 8. 求解
# =====================================================
solver = pyo.SolverFactory("gurobi")
solver.solve(model, tee=True)

print("Model solved successfully.")
print("Optimized E_cap (kWh):", {i: float(pyo.value(model.E_cap[i])) for i in model.M})

# =====================================================
# 9. 后处理
# =====================================================
netload_1 = Load_1 - PV_1 + np.array([pyo.value(model.E_ch[1, t]) - pyo.value(model.E_dis[1, t]) for t in T])
netload_2 = Load_2 - PV_2 + np.array([pyo.value(model.E_ch[2, t]) - pyo.value(model.E_dis[2, t]) for t in T])

bess_power_1 = np.array([pyo.value(model.E_dis[1, t]) - pyo.value(model.E_ch[1, t]) for t in T])
bess_power_2 = np.array([pyo.value(model.E_dis[2, t]) - pyo.value(model.E_ch[2, t]) for t in T])

soc_1 = np.array([pyo.value(model.SOC[1, t]) for t in T])
soc_2 = np.array([pyo.value(model.SOC[2, t]) for t in T])

price_1 = np.array([Price[1][t] for t in T], dtype=float)
price_2 = np.array([Price[2][t] for t in T], dtype=float)
price_diff = price_1 - price_2

ex12 = np.array([pyo.value(model.E_ex_12[t]) for t in T], dtype=float)
ex21 = np.array([pyo.value(model.E_ex_21[t]) for t in T], dtype=float)
net_trade = ex12 - ex21

p_ex = np.array([pyo.value(model.p_ex[t]) for t in T], dtype=float)

Ecap1 = float(pyo.value(model.E_cap[1]))
Ecap2 = float(pyo.value(model.E_cap[2]))

# ✅ 双方同意的价格区间（outside option）
low_12  = alpha_sell * price_1
high_12 = price_2
low_21  = alpha_sell * price_2
high_21 = price_1

mask_12 = ex12 > 1e-6
mask_21 = ex21 > 1e-6

# =====================================================
# 10. 最后一张图（仅保留这一张）
# =====================================================
fig, axes = plt.subplots(
    6, 1,
    figsize=(15, 13),
    sharex=True,
    gridspec_kw={"height_ratios": [1.2, 1.0, 1.0, 1.0, 1.2, 1.2]}
)

axes[0].plot(hours, netload_1, label="Net Load Area 1", color="#d62728", linewidth=1.8)
axes[0].plot(hours, netload_2, label="Net Load Area 2", color="#1f77b4", linewidth=1.8)
axes[0].axhline(0, color="gray", linestyle="--")
axes[0].set_ylabel("Net Load (kWh)")
axes[0].legend(frameon=False)
axes[0].set_title("Price – BESS – Net Load – Trading (E_cap optimized, EX capped, Mutual-consent exchange)")

axes[1].plot(hours, bess_power_1, label="BESS Power Area 1", color="#d62728")
axes[1].plot(hours, bess_power_2, label="BESS Power Area 2", color="#1f77b4")
axes[1].axhline(0, color="gray", linestyle="--")
axes[1].set_ylabel("Battery Power (kW)")
axes[1].legend(frameon=False)

axes[2].plot(hours, soc_1, label="SOC Area 1", color="#d62728", linewidth=1.6)
axes[2].plot(hours, soc_2, label="SOC Area 2", color="#1f77b4", linewidth=1.6)
axes[2].axhline(Ecap1, color="#d62728", linestyle=":", alpha=0.8, label="E_cap Area 1")
axes[2].axhline(Ecap2, color="#1f77b4", linestyle=":", alpha=0.8, label="E_cap Area 2")
axes[2].axhline(0, color="gray", linestyle="--", alpha=0.6)
axes[2].set_ylabel("SOC (kWh)")
axes[2].legend(frameon=False, ncol=2)

axes[3].plot(hours, price_diff, color="purple", linewidth=1.6, label="Price Difference (P1 − P2)")
axes[3].axhline(0, color="gray", linestyle="--")
axes[3].set_ylabel("€/kWh")
axes[3].legend(frameon=False)

# ✅ 价格 + 双方同意区间 band + 成交价 p_ex
axes[4].step(hours, price_1, where="post", label="Price Area 1 (grid buy)", color="#d62728", zorder=3)
axes[4].step(hours, price_2, where="post", label="Price Area 2 (grid buy)", color="#1f77b4", zorder=3)

axes[4].fill_between(hours, low_12, high_12, where=mask_12, step="post",
                     alpha=0.30, zorder=1, label="Feasible range 1→2 (0.5·P1 to P2)")
axes[4].fill_between(hours, low_21, high_21, where=mask_21, step="post",
                     alpha=0.30, zorder=1, label="Feasible range 2→1 (0.5·P2 to P1)")

axes[4].scatter(hours[mask_12 | mask_21], p_ex[mask_12 | mask_21],
                s=18, color="black", zorder=4, label="Exchange price p_ex (when trade occurs)")

axes[4].set_ylabel("Price (€/kWh)")
axes[4].legend(frameon=False, ncol=2)
# ✅ 价格 + 买/卖电价 + 双方同意区间 band + 成交价 p_ex
axes[4].step(hours, price_1, where="post", label="Price Area 1 (grid buy)",  color="#d62728", zorder=4)
axes[4].step(hours, price_2, where="post", label="Price Area 2 (grid buy)",  color="#1f77b4", zorder=4)

# 新增：grid sell price = alpha_sell * grid buy price
sell_1 = alpha_sell * price_1
sell_2 = alpha_sell * price_2
axes[4].step(hours, sell_1, where="post", linestyle="--", label="Price Area 1 (grid sell)", color="#d62728", alpha=0.8, zorder=3)
axes[4].step(hours, sell_2, where="post", linestyle="--", label="Price Area 2 (grid sell)", color="#1f77b4", alpha=0.8, zorder=3)

# 交换可行区间（只在实际发生交换时画 band）
axes[4].fill_between(hours, low_12, high_12, where=mask_12, step="post",
                     alpha=0.30, zorder=1, label="Feasible range 1→2 (0.5·P1 to P2)")
axes[4].fill_between(hours, low_21, high_21, where=mask_21, step="post",
                     alpha=0.30, zorder=1, label="Feasible range 2→1 (0.5·P2 to P1)")

# 成交价（只在有交易时画点）
axes[4].scatter(hours[mask_12 | mask_21], p_ex[mask_12 | mask_21],
                s=18, color="black", zorder=5, label="Exchange price p_ex (when trade occurs)")

axes[4].set_ylabel("Price (€/kWh)")
axes[4].legend(frameon=False, ncol=2)

axes[5].plot(hours, net_trade, color="black", linewidth=2.2, label="Net Energy Exchange (1 → 2)")
axes[5].axhline(0, color="gray", linestyle="--")
axes[5].set_ylabel("Energy Exchange (kWh)")
axes[5].set_xlabel("Hour")
axes[5].legend(frameon=False)

for ax in axes:
    ax.grid(axis="y", linestyle="--", alpha=0.25)

plt.tight_layout()
plt.savefig("Fig_BESS_mutual_consent.png", dpi=300, bbox_inches="tight")
plt.show()

print("Saved: Fig_BESS_mutual_consent.png")

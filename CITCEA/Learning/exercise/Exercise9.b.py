import pyomo.environ as pyo
import pandas

model = pyo.ConcreteModel()

l_t=list(range(4))


data=pandas.read_excel('9.b.xlsx', sheet_name="Sheet1", header=None, index_col=0)
consumption={t:float(data[1][t+1]) for t in l_t}
PVmax={t:float(data[2][t+1]) for t in l_t}
Purchaseprice={t:float(data[3][t+1]) for t in l_t}
Sellprice={t:float(data[4][t+1]) for t in l_t}


model.t=pyo.Set(initialize=l_t)
model.PVG=pyo.Var(model.t,bounds=lambda m,t: (0,PVmax[t]))
model.purchasedelectricity=pyo.Var(model.t,within=pyo.NonNegativeReals)
model.soldelectricity=pyo.Var(model.t,within=pyo.NonNegativeReals)

def Constraint1(m,t):
    return m.PVG[t] + m.purchasedelectricity[t] -m.soldelectricity[t] >= consumption[t]
model.demand_constraint = pyo.Constraint(model.t, rule=Constraint1)



def func_obj(m):
    return sum(Purchaseprice[t]*m.purchasedelectricity[t] - Sellprice[t]*m.soldelectricity[t] for t in m.t)


model.goal=pyo.Objective(rule=func_obj, sense=pyo.minimize)
# Select solver
opt = pyo.SolverFactory('ampl', solver='highs',executable=r"C:\Users\18410\AMPL\highs.exe")
results = opt.solve(model)
for t in model.t:
    print(f"Hour {t}: PV = {model.PVG[t]():.2f}, Grid Purchase = {model.purchasedelectricity[t]():.2f}, Grid Sell = {model.soldelectricity[t]():.2f}")

print("Total cost / benefit =", pyo.value(model.goal))

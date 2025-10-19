import pyomo.environ as pyo
import pandas

model = pyo.ConcreteModel()

l_t=list(range(4))


data=pandas.read_excel('8.2.xlsx', sheet_name="Sheet1", header=None, index_col=0)
consumption={t:float(data[1][t+1]) for t in l_t}
PVmax={t:float(data[2][t+1]) for t in l_t}


model.t=pyo.Set(initialize=l_t)
model.PVG=pyo.Var(model.t,bounds=lambda m,t: (0,PVmax[t]))
model.purchasedelectricity=pyo.Var(model.t,within=pyo.NonNegativeReals)

def Constraint1(m,t):
    return m.PVG[t] + m.purchasedelectricity[t] == consumption[t]
model.demand_constraint = pyo.Constraint(model.t, rule=Constraint1)



def func_obj(m,t):
    return sum(0.05*m.purchasedelectricity[t] for t in m.t)


model.goal=pyo.Objective(rule=func_obj, sense=pyo.minimize)
# Select solver
opt = pyo.SolverFactory('ampl', solver='highs',executable=r"C:\Users\18410\AMPL\highs.exe")
results = opt.solve(model)
for t in model.t:
    print(f"Hour {t}: PV = {model.PVG[t]():.2f}, Grid = {model.purchasedelectricity[t]():.2f}")
print("Total cost =", pyo.value(model.goal))

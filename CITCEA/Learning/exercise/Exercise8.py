import pyomo.environ as pyo
import pandas

model = pyo.ConcreteModel()

l_t=list(range(4))
model.t=pyo.Set(initialize=l_t)
consumption={0:1,1:2,2:2,3:1}
PVmax={0:0,1:1,2:2,3:3}

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
print("Total cost =", model.goal())

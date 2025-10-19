import pyomo.environ as pyo
import pandas

model = pyo.ConcreteModel()

consumption=1
model.t=pyo.Set(initialize=['PVG','EFG'])
model.PVG=pyo.Var(bounds=(0,2))
model.EFG=pyo.Var(within=pyo.NonNegativeReals)

def Constraint1(m):
    return m.PVG + m.EFG == consumption
model.demand_constraint = pyo.Constraint(rule=Constraint1)

def func_obj(m):
    return m.EFG*0.05


model.goal=pyo.Objective(rule=func_obj, sense=pyo.minimize)
# Select solver
opt = pyo.SolverFactory('ampl', solver='highs',executable=r"C:\Users\18410\AMPL\highs.exe")
results = opt.solve(model)
print("PV generation =", model.PVG(),"kWh")
print("Purchase =", model.EFG(),"kWh")
print("total cost =", model.EFG()*0.05)

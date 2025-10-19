import pyomo.environ as pyo
import pandas

model = pyo.ConcreteModel()

consumption=1

model.PVG=pyo.Var(bounds=(0,2))
model.soldelectricity=pyo.Var(within=pyo.NonNegativeReals)
model.purchasedelectricity=pyo.Var(within=pyo.NonNegativeReals)

def Constraint1(m):
    return m.PVG + m.purchasedelectricity-m.soldelectricity >= consumption
model.demand_constraint = pyo.Constraint(rule=Constraint1)



def func_obj(m):
    return m.PVG*0.01+m.purchasedelectricity*0.05-0.005*(m.soldelectricity)


model.goal=pyo.Objective(rule=func_obj, sense=pyo.minimize)
# Select solver
opt = pyo.SolverFactory('ampl', solver='highs',executable=r"C:\Users\18410\AMPL\highs.exe")
results = opt.solve(model)
print("PV generation =", model.PVG(),"kWh")
print("Purchase =", model.purchasedelectricity(),"kWh")
print("Sold Electricity =",model.soldelectricity(),"kWh")
print("total cost =", model.PVG()*0.01+model.purchasedelectricity()*0.05-0.005*(model.soldelectricity()))

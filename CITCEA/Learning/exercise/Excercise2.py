import pyomo.environ as pyo
import pandas

model = pyo.ConcreteModel()
#Define Loads
model.loads=pyo.Set(initialize=['L1','L2'])
loads={'L1':30, 'L2':10}
price=0.05
model.grid_energy = pyo.Var(model.loads, within=pyo.NonNegativeReals)
def constraint1(m, l):
    return m.grid_energy[l] >= loads[l]
model.constraint1 = pyo.Constraint(model.loads, rule=constraint1)
def func_obj(m):
    return sum(price*m.grid_energy[l] for l in m.loads)
model.goal=pyo.Objective(rule=func_obj, sense=pyo.minimize)
# Select solver
opt = pyo.SolverFactory('ampl', solver='highs',executable=r"C:\Users\18410\AMPL\highs.exe")
# Solve model
results = opt.solve(model)
for l in model.loads:
    print(f"Energy from grid for {l} = {model.grid_energy[l]()} kWh")
total_cost = sum(price * model.grid_energy[l]() for l in model.loads)
print(f"Total cost = {total_cost} €")
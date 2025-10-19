import pyomo.environ as pyo
import pandas

model = pyo.ConcreteModel()

model.t=pyo.Set(initialize=['x','y'])
model.x=pyo.Var(within=pyo.NonNegativeReals)
model.y=pyo.Var(within=pyo.NonNegativeReals)

def Constraint1(m):
    return m.x+2*m.y <=4
def Constraint2(m):
    return 2*m.x+m.y <=4

model.constraint1 = pyo.Constraint(rule=Constraint1)
model.constraint2 = pyo.Constraint(rule=Constraint2)

def func_obj(m):
    return m.x + m.y


model.goal=pyo.Objective(rule=func_obj, sense=pyo.maximize)
# Select solver
opt = pyo.SolverFactory('ampl', solver='highs',executable=r"C:\Users\18410\AMPL\highs.exe")
# Solve model
results = opt.solve(model)
print("x =", model.x())
print("y =", model.y())
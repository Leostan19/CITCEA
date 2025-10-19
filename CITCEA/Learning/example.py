import pyomo.environ as pyo  # requires to have Pyomo installed
import pandas  # requires to have pandas and openpyxl installed

# Timeframe
l_t = list(range(8760))  # 1 day = 24 h, 1 year = 8760 h

# Import data from excel
load = pandas.read_excel('data.xlsx', sheet_name="dem_cat", header=None, index_col=0)  # hourly demand from Catalunya in column B [MW]
PVforecast = pandas.read_excel('data.xlsx', sheet_name="PV_forecast", header=None, index_col=0)  # hourly PV forecast from ETSEIB in column B [kW]
# change format from DaraFrame to dictionary
Pload = {t: float(load[1][t+1])*1000 for t in l_t}  # [kW]            --> position as: var[column][row]
P_PVforecast = {t: float(PVforecast.iloc[t][1]) for t in l_t}     # --> position as: var.iloc[row][column]

# Initialize Pyomo model
model = pyo.ConcreteModel()

# Sets
model.t = pyo.Set(initialize=l_t)

# Variables
model.Ppnuc = pyo.Var(within=pyo.NonNegativeReals)  # size of the nuclear power plant [kW]
model.Pnuc_t = pyo.Var(model.t, within=pyo.NonNegativeReals)  # hourly generation of the nuclear power plant [kW]
model.Ppgas = pyo.Var(within=pyo.NonNegativeReals)  # size of the gas power plant [kW]
model.Pgas_t = pyo.Var(model.t, within=pyo.NonNegativeReals)  # hourly generation of the gas power plant [kW]
model.Ppv = pyo.Var(within=pyo.NonNegativeReals)  # size of the PV system [kW]
model.Ppv_t = pyo.Var(model.t, within=pyo.NonNegativeReals)  # hourly generation of the PV system [kW]

# Constraints
def Constraint_balance(m, t):
    return m.Pnuc_t[t] + m.Pgas_t[t] + m.Ppv_t[t] == Pload[t]  # total generation = demand
model.Constr_balance = pyo.Constraint(model.t, rule=Constraint_balance)

def Constraint_nuclear_size(m, t):
    return m.Pnuc_t[t] == m.Ppnuc  # nuclear power is constant
model.Constr_nuclear_size = pyo.Constraint(model.t, rule=Constraint_nuclear_size)

def Constraint_gas_size(m, t):
    return m.Pgas_t[t] <= m.Ppgas  # gas power can change each hour
model.Constr_gas_size = pyo.Constraint(model.t, rule=Constraint_gas_size)

def Constraint_PV_size(m, t):
    return m.Ppv_t[t] <= m.Ppv * P_PVforecast[t]  # PV generation depends on availability and can be curtailed
model.Constr_PV_size = pyo.Constraint(model.t, rule=Constraint_PV_size)

# Objective function
def func_obj(m):
    years = 40
    CAPEX_nuc = m.Ppnuc * 3600
    OPEX_nuc = m.Ppnuc * 0.02 * 8760
    CAPEX_gas = m.Ppgas * 823
    OPEX_gas = sum(m.Pgas_t[t] * 1 for t in l_t) * 0.15  # for 1 day
    CAPEX_PV = m.Ppv * 650
    OPEX_PV = m.Ppv * 0.13
    replacement_PV = m.Ppv * 325 * 1  # PV lifetime is 20 years, so it must be replaced once
    return CAPEX_nuc + OPEX_nuc * years + CAPEX_gas + OPEX_gas * 365 * years + CAPEX_PV + OPEX_PV * years + replacement_PV
model.goal = pyo.Objective(rule=func_obj, sense=pyo.minimize)

# Select solver
opt = pyo.SolverFactory('ampl', solver='highs',executable=r"C:\Users\18410\AMPL\highs.exe")
# Solve model
results = opt.solve(model)

# Extract results
print('Nuclar plant: ', model.Ppnuc.get_values()[None]/1000, 'MW')
print('Gas power plant: ', model.Ppgas.get_values()[None]/1000, 'MW')
print('PV system: ', model.Ppv.get_values()[None]/1000, 'MW')
# Write results to excel
dict_results= {}
dict_results['P nuclear [kW]'] = list({t: model.Pnuc_t.get_values()[t] for t in l_t}.values())
dict_results['P PV [kW]'] = list({t: model.Ppv_t.get_values()[t] for t in l_t}.values())
dict_results['P gas [kW]'] = list({t: model.Pgas_t.get_values()[t] for t in l_t}.values())
table_results = pandas.DataFrame(dict_results, index=l_t)
sizing = [['Nuclar plant', model.Ppnuc.get_values()[None]/1000, 'MW'],
        ['Gas power plant', model.Ppgas.get_values()[None]/1000, 'MW'],
        ['PV system', model.Ppv.get_values()[None]/1000, 'MW']]
table_sizing = pandas.DataFrame(sizing, columns=['Variable', 'Value', 'Units'])
with pandas.ExcelWriter('Results.xlsx') as writer:
    table_results.to_excel(writer, sheet_name='Operation', float_format="%.2f")
    table_sizing.to_excel(writer, sheet_name='Sizing', float_format="%.2f")

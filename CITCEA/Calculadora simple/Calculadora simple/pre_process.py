import pandas


####################   Read input data from excel (get_inputs_form_excel)   ####################

folder_data = 'CSV/DATA/'
l_t = list(range(24*365))
bisiesto = 0
inc_t = 1  # time-step magnitude [h]
#
general_client = pandas.read_excel(folder_data+'client.xlsx', sheet_name='General', header=None, index_col=0)
#
name_days = pandas.read_excel(folder_data + 'Time_data.xlsx', sheet_name='data', header=0,
                              usecols=['id', 'datetime', 'mes', 'dia', 'festivo'])  # import database with time names
#
load_data = pandas.read_excel(folder_data + 'client.xlsx', sheet_name='Load', header=1,
                              index_col=None)  # si queremos llamar por id --> index_col=0
load_P_TS = pandas.read_excel(folder_data + 'client.xlsx', sheet_name='Load TS', header=1, index_col=None)
#
PV_database = pandas.read_excel(folder_data+'client.xlsx', sheet_name='PV database', header=0, index_col=0)  # import PV database
PV_client = pandas.read_excel(folder_data+'client.xlsx', sheet_name='PV', header=1, index_col=None)  # importa PV client data
PV_TS = pandas.read_excel(folder_data + 'client.xlsx', sheet_name='PV TS', header=1, index_col=None)
#
BESS_database = pandas.read_excel(folder_data+'client.xlsx', sheet_name='Battery database', header=0, index_col=0)  # import battery database
BESS_client = pandas.read_excel(folder_data+'client.xlsx', sheet_name='BESS', header=1, index_col=None)  # import BESS client data
#
economic_constraints_DataFrame = pandas.read_excel(folder_data+'client.xlsx', sheet_name='Economic Constraints', header=0, index_col=None)  # import economic constraints
#
client_EV = pandas.read_excel(folder_data+'client.xlsx', sheet_name='EV', header=None,
                              index_col=0)  # import EV characteristics defined by the client
#
ev_df = pandas.read_excel(folder_data + 'EV_stations.xlsx')

station_cols = [c for c in ev_df.columns if c.startswith('EV station')]
assert len(station_cols) == 4, f"Expected 4 EV station columns, found {len(station_cols)}"
T = len(l_t)  # 8760 hours
ev_df = ev_df.iloc[:T].reset_index(drop=True)
EV_profiles = {s: ev_df[s].to_numpy(dtype=float) for s in station_cols}

# Editable
Pmax_station = {s: 22.0 for s in station_cols}   # kW rated power per station
eta_ch  = {s: 0.95 for s in station_cols}        # charging efficiency
eta_dis = {s: 0.95 for s in station_cols}        # discharging efficiency

EV_Stations = {
    "id_list": station_cols,
    "profile": EV_profiles,
    "Pmax": Pmax_station,
    "eta_ch": eta_ch,
    "eta_dis": eta_dis,
}
#
Grid_client = pandas.read_excel(folder_data + 'client.xlsx', sheet_name='Grid', header=1, index_col=None)  # import Grid client data
hired_power_periods = pandas.read_excel(folder_data + 'client.xlsx', sheet_name='hired_power Periods', header=1, index_col=None)
buy_price_periods = pandas.read_excel(folder_data + 'client.xlsx', sheet_name='buy_price Periods', header=1, index_col=None)
sell_price_periods = pandas.read_excel(folder_data + 'client.xlsx', sheet_name='sell_price Periods', header=1, index_col=None)
buy_price_TS = pandas.read_excel(folder_data + 'client.xlsx', sheet_name='buy_price TS', header=1, index_col=None)
sell_price_TS = pandas.read_excel(folder_data + 'client.xlsx', sheet_name='sell_price TS', header=1, index_col=None)
grid_emissions_TS = pandas.read_excel(folder_data + 'client.xlsx', sheet_name='Grid_emissions TS', header=1, index_col=None)  # emission factor [tCO2/MWh]
grid_renewables_TS = pandas.read_excel(folder_data + 'client.xlsx', sheet_name='Grid_renewables TS', header=1, index_col=None)  # renewables share [pu]
market_cost = pandas.read_csv(folder_data + 'export_PrecioMercadoSPOTDiario_buy.csv', delimiter=';',
                              header=0, usecols=['datetime', 'value'])  # import market prices [€/MWh]
market_income = pandas.read_csv(folder_data + 'export_PrecioMercadoSPOTDiario_sell.csv', delimiter=';',
                              header=0, usecols=['datetime', 'value'])  # import market prices [€/MWh]
BOE_cost_power = pandas.read_excel(folder_data + 'peajes.xlsx', sheet_name='Power Cost', header=0,
                                   index_col=0)  # import hired power costs at each tariff period (BOE)
BOE_cost_energy = pandas.read_excel(folder_data + 'peajes.xlsx', sheet_name='Energy Cost', header=0,
                                    index_col=0)  # import energy access costs at each tariff period (BOE)
BOE_penalisations = pandas.read_excel(folder_data + 'peajes.xlsx', sheet_name='Power Penalizations', header=0,
                                      index_col=0)  # import costs and coefficients of excess power penalisation (BOE)
# start_date = '01-01-2023'
# end_date = '31-12-2023'
# url_precio = 'https://www.esios.ree.es/es/analisis/600?vis=1&start_date=' + start_date + 'T00%3A00&end_date=' + end_date + 'T23%3A55&geoids=3&compare_start_date=22-07-2024T00%3A00&groupby=hour'  # €/MWh
# url_emisiones = 'https://www.esios.ree.es/es/analisis/10355?vis=1&start_date=' + start_date + 'T00%3A00&end_date=' + end_date + 'T23%3A55&compare_start_date=30-06-2024T00%3A00&groupby=hour'  # tCO2/MW
# url_demanda_nacional = 'https://www.esios.ree.es/es/analisis/1293?compare_indicators=&start_date=' + start_date + 'T00%3A00&geoids=&vis=1&end_date=' + end_date + 'T23%3A55&compare_start_date=22-07-2024T00%3A00&groupby=hour'  # MW
# url_generacion_renovable = 'https://www.esios.ree.es/es/analisis/10351?vis=1&start_date=' + start_date + 'T00%3A00&end_date=' + end_date + 'T23%3A55&compare_start_date=22-07-2024T00%3A00&groupby=hour'  # MW
national_grid_emissions_DataFrame = pandas.read_csv(folder_data + 'export_CO2AsociadoGeneracionTReal_2024-07-23_10_21.csv',
                                                    delimiter=';',
                                                    header=0,
                                                    usecols=['datetime', 'value'])  # emission factor [tCO2/MWh=kgCO2/kWh]
national_demand_DataFrame = pandas.read_csv(folder_data + 'export_DemandaReal_2024-07-23_10_30.csv', delimiter=';',
                                            header=0, usecols=['datetime', 'value'])  # total demand [MWh]
national_renewable_generation_DataFrame = pandas.read_csv(
    folder_data + 'export_GeneracionTRealRenovable_2024-07-23_10_35.csv', delimiter=';',
    header=0, usecols=['datetime', 'value'])  # total renewable generation [MWh]
#
import_buses = pandas.read_excel(folder_data + 'client.xlsx', sheet_name='Bus', header=1, index_col=None)
import_lines = pandas.read_excel(folder_data + 'client.xlsx', sheet_name='Lines', header=1, index_col=None)

####################   Pre-process   ####################

# General system --> mejorable
from pre_processing.System import *
System = SystemClass()
System.full(general_client, l_t, inc_t, name_days, general_client[1]['CO2 emissions cost'])
cambio_moneda = general_client[1]['Cash change'] # €/$

# Network
from pre_processing.Network import *
Sb = 100 * 1000  # Sb = 100 MVA
PF_type = general_client[1]['Electric network power flow']  # economic_dispatch / DC-OPF
#
Buses = BusClass()
for i_bus in range(import_buses['Num'].size):  # i_bus is the row of the Excel
    Buses.add(import_buses['Num'][i_bus], import_buses['name'][i_bus], import_buses['type'][i_bus],
              import_buses['vn_kv'][i_bus], import_buses['slack'][i_bus],
              import_buses['v_pu_min'][i_bus], import_buses['v_pu_max'][i_bus])
#
Lines = LinesClass(Buses.id_list) # LinesClass(Buses.id)
for i_line in range(import_lines['id'].size):  # i_line is the row of the Excel
    to_bus = import_lines['to_bus'][i_line]
    Vb = Buses.Vn[to_bus]
    Zb = (Vb*10**3)**2 / (Sb*10**3)
    Ib = (Sb*10**3) / (Vb*10**3)
    Lines.add(import_lines['id'][i_line], import_lines['name'][i_line], import_lines['from_bus'][i_line],
              import_lines['to_bus'][i_line],
              import_lines['P_max (kW)'][i_line], import_lines['I_max (A)'][i_line],
              import_lines['R (Ω)'][i_line], import_lines['X (Ω)'][i_line], import_lines['B (S)'][i_line],
              Zb, Sb, Ib)
Lines.global_system(Buses.id_list)
#
Network = NetworkClass(PF_type, Sb, Buses, Lines)

# Demand
from pre_processing.Loads import *
Loads = DemandClass()
for i_load in range(load_data['id'].size):  # i_load is the row of the Excel
    id = load_data['id'][i_load]
    Loads.add(id, load_data['name'][i_load], load_data['type'][i_load], load_data['Bus'][i_load], Buses.id_list,
              System.l_t, load_data['Installed_power'][i_load], load_P_TS[id])
Loads.total_buses(Buses.id_list, System.l_t)

# PV
from pre_processing.PV import *
surface = general_client[1]['PV available surface']
PV = PVClass(surface)
for i_PV in range(PV_client['id'].size):
    id = PV_client['id'][i_PV]
    forecast_type = PV_client['forecast'][i_PV]
    PVGIS_data = PV_client.drop(['id','name','model','Bus','sizing','existent','fix','incentives','forecast'],axis=1).loc[i_PV]
    PV.add(id, PV_client['name'][i_PV], PV_client['Bus'][i_PV], Buses.id_list,
           PV_client['model'][i_PV], PV_client['sizing'][i_PV],
           PV_client['existent'][i_PV], PV_client['fix'][i_PV], PV_client['incentives'][i_PV], forecast_type,
           PVGIS_data, bisiesto, PV_TS[id], PV_database, cambio_moneda, l_t)

# BESS
from pre_processing.Battery import *
BESS = BatteryClass()
for i_BESS in range(BESS_client['id'].size):
    id = BESS_client['id'][i_BESS]
    BESS.add(id, BESS_client['name'][i_BESS], BESS_client['Bus'][i_BESS], Buses.id_list,
             BESS_client['model'][i_BESS], BESS_client['sizing'][i_BESS],
             BESS_client['existent'][i_BESS], BESS_client['fix'][i_BESS], BESS_client['incentives'][i_BESS],
             BESS_database, cambio_moneda, l_t, System.inc_t)

# Economic constraints --> mejorable (ahora está igual que antes)
from pre_processing.Economic_constraints import *
economic_constraints = economic_constraints_list(economic_constraints_DataFrame)

# Grid --> muy mejorable (está igual que antes) (solo puede tener 1 punto de conexión) (falta traducir)
from pre_processing.Grid import *
if Grid_client['id'].size == 0:
    conected1_islanded0 = 0
else:
    conected1_islanded0 = 1
Grid = GridClass(conected1_islanded0)
for i_Grid in range(Grid_client['id'].size):
    id = Grid_client['id'][i_Grid]
    Grid.add(id, Grid_client['name'][i_Grid], Grid_client['Bus'][i_Grid], Buses.id_list,
              Grid_client['Territory'][i_Grid], Grid_client['Tariff'][i_Grid], Grid_client['Meter type'][i_Grid],
              Grid_client['Inyection to the grid'][i_Grid], Grid_client['PV power limit to inject'][i_Grid],
              BOE_penalisations, BOE_cost_power,
              l_t, System.inc_t, name_days,
              hired_power_periods[id], Grid_client['Hard power limit'][i_Grid], Grid_client['Fix hired power'][i_Grid],
              Grid_client['Buy energy price type'][i_Grid],
              Grid_client['Fix buy energy price'][i_Grid], Grid_client['Buy energy price fee'][i_Grid],
              buy_price_periods[id], buy_price_TS[id],
              Grid_client['Sell energy price type'][i_Grid],
              Grid_client['Fix sell energy price'][i_Grid], Grid_client['Sell energy price fee'][i_Grid],
              sell_price_periods[id], sell_price_TS[id],
              market_cost, market_income, BOE_cost_energy,
              Grid_client['Emissions/renewables share source type'][i_Grid], grid_emissions_TS[id], grid_renewables_TS[id],
              national_grid_emissions_DataFrame, national_renewable_generation_DataFrame, national_demand_DataFrame)

# EV --> muy mejorable (está igual que antes)
from pre_processing.EV import *
EV = EVClass(client_EV.loc['EV (1: yes, 0: no)'][1], l_t)
total_EV_immediate_load = {t: 0 for t in System.l_t}
for i_load in Loads.id_list:
    if Loads.type[i_load] == 'EV':
        for t in System.l_t:
            total_EV_immediate_load[t] = total_EV_immediate_load[t] + Loads.Pd[i_load,t]
EV.add(l_t, inc_t, client_EV, total_EV_immediate_load, name_days, Buses.id_list)
# save inputs of flexibility in excels
directory_Flexibility = folder_data + 'Flexibilidad_pre-process/'
save_EV_inputs(directory_Flexibility, EV.smart, l_t)




from pre_processing.System import AllInputsClass

AllInputs = AllInputsClass(System, Loads, PV, BESS, Grid,
                           EV, economic_constraints,
                           Network, EV_Stations)

print("\n--- Checking AllInputs data ---")
print("EV station IDs:", AllInputs.EV_Stations["id_list"])
print("First 5 values for EV station 1:", AllInputs.EV_Stations["profile"]["EV station 1 [kWh]"][:5])
print("Pmax for station 1:", AllInputs.EV_Stations["Pmax"]["EV station 1 [kWh]"])
print("--------------------------------\n")



####################   ...   ####################



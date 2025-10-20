import pandas as pd
ev_df = pd.read_excel(folder_data + 'EV_stations.xlsx')

station_cols = [c for c in ev_df.columns if c.startswith('EV station')]
assert len(station_cols) == 4, f"Expected 4 EV station columns, found {len(station_cols)}"
T = len(l_t)  # 8760 hours
ev_df = ev_df.iloc[:T].reset_index(drop=True)
EV_profiles = {s: ev_df[s].to_numpy(dtype=float) for s in station_cols}

price_buy  = ev_df['buy price [€/kWh]'].to_numpy(dtype=float)
price_sell = ev_df['sell price [€/kWh]'].to_numpy(dtype=float)

# Editable
Pmax_station = {s: 22.0 for s in station_cols}   # kW rated power per station
eta_ch  = {s: 0.95 for s in station_cols}        # charging efficiency
eta_dis = {s: 0.95 for s in station_cols}        # discharging efficiency

EV_stations = {
    "id_list": station_cols,
    "profile": EV_profiles,
    "Pmax": Pmax_station,
    "eta_ch": eta_ch,
    "eta_dis": eta_dis,
}


print(f"Loaded {len(station_cols)} EV stations and price data for {T} hours.")

# in system.py, we need to define the class for accomodating these variables
# so we add the EV_stations and Prices classes to it
class AllInputsClass:
    def __init__(self, System, Loads, PV, BESS, Grid, EV, economic_constraints, Network, EV_stations=None, Prices=None):
        self.System = System
        self.Load = Loads
        self.PV = PV
        self.BESS = BESS
        self.Grid = Grid
        self.EV = EV
        self.economic_constraints = economic_constraints
        self.Network = Network
        self.EV_stations = EV_stations
        self.Prices = Prices


import pandas
'''
Comentarios:
    - podemos introducir tantos modelos de BESS como queramos
    - podemos hacer sizing y/o existente para un mismo modelo
    - alternativamente a realizar el sizing se puede fijar el numero de BESS a añadir. Si esto no se fija, debe de ser nan --> math.isnan(BESS.fix_u[id]) = True
    - si no se introduce ningun modelo, no se considera
'''


class BatteryClass:
    '''Class with all the inputs of the Battery system'''

    def __init__(self):
        '''
        Class with all the inputs of the Battery system
        '''
        self.id = 0  # number of the Battery system
        self.id_list = []  # list with all Battery system numbers
        self.name = {}  # name of the Battery system
        self.pos_bus = {}  # binary that indicates the bus to which the load is connected --> [id_load,id_bus]=1

        # General data
        self.model = {}  # model of the Battery, from the database
        self.sizing = {}  # binary that indicates if Battery should be sized (to add). 1: yes, 0: no
        self.existent_u = {}  # battery installed [units] already in the system. This will have operation and replacement costs
        self.fix_u = {}  # if the sizing is fixed, Battery installed [units]. This will have investment, operation and replacement costs
        self.capex_incentives = {}  # economic incentives on the capex for Battery [€/kWh]

        # Costs of the selected model
        self.capital = {}  # investment cost --> [€/kW] for PV and genset and converter, [€/u] for battery
        self.replacement = {}  # replacement cost --> [€/kW] for PV and genset and converter, [€/u] for battery
        self.om = {}  # operation and maintenance cost --> [€/kW/year] for PV and converter, [€/kW/h] for genset, [€/u/year] for battery
        self.lifetime = {}  # lifetime [years]
        self.degradation_cost = {}  # cost of cycle aging [€/kWh carged and discharged]

        # Performance characteristics of the selected model
        self.capacity_kWh = {}  # storage capacity of 1 battery [kWh]
        self.maxCharge_kW = {}  # maximum charging power of 1 battery [kW]
        self.maxDischarge_kW = {}  # maximum discharging power of 1 battery [kW]
        self.SOCmin = {}  # minimum state of charge [pu]
        self.SOCmax = {}  # maximum state of charge [pu]
        self.tau = {}  # Energy loss ratio of the storage or self-discharge rate [pu]
        self.charEff = {}  # Charging efficiency [pu]
        self.dischEff = {}  # Discharging efficiency [pu]
        self.throughput = {}  # throughput of 1 battery [kWh]
        self.calendar_aging_anual = {}  # annual degradation due to calendar aging [% of the storage capacity]
        self.SOCmax_hourly = {}  # maximum SOC at each time-step considering calendar aging [pu]
        # self.roundtripEff = component_DataFrame.loc['Roudtrip eff.']  # roundtrip efficiency [%]
        #
        self.existent_C = {}  # storage capacity [kWh] of the battery already in the system
        self.existent_Pn_char = {}  # maximum charging power [kW] of the battery already in the system
        self.existent_Pn_disch = {}  # maximum discharging power [kW] of the battery already in the system
        #
        self.SOCini = {}  # state of charge at the start of an islanded period for the islandable analysis

    def add(self, id, name, bus, l_bus, model, sizing, existent, fix, incentives, database_DataFrame, cash_exchange, l_t, inc_t):
        '''
        Add a Battery system
        :param id: number of the Battery system
        :param name: name of the Battery system
        :param bus: bus id to which the Battery is connected
        :param l_bus: list with the id of all the buses
        :param model: model of the Battery, from the database
        :param sizing: binary that indicates if Battery should be sized (to add). 1: yes, 0: no
        :param existent: battery installed [units] already in the system. This will have operation and replacement costs
        :param fix: if the sizing is fixed, Battery installed [units]. This will have investment, operation and replacement costs
        :param incentives: economic incentives on the capex for Battery [€/kWh]
        :param database_DataFrame: excel with the parameters for all Battery models (DataFrame)
        :param cash_exchange: €/$
        :return: Class with all the inputs of the Battery system updated
        '''
        self.id = id  # number of the Battery system
        self.id_list.append(id)  # list with all Battery system numbers
        self.name[id] = name  # name of the Battery system

        pos = {(self.id, bus_aux): 0 for bus_aux in l_bus}
        pos[self.id, bus] = 1
        self.pos_bus.update(pos)

        # General data
        self.model[id] = model  # model of the Battery, from the database
        self.sizing[id] = sizing  # binary that indicates if Battery should be sized (to add). 1: yes, 0: no
        self.existent_u[id] = existent  # battery installed [units] already in the system. This will have operation and replacement costs
        self.fix_u[id] = fix  # if the sizing is fixed, Battery installed [units]. This will have investment, operation and replacement costs
        self.capex_incentives[id] = incentives  # economic incentives on the capex for Battery [€/kWh]

        # extract characteristics of the selected model from the database, and add the row Model BESS
        component_DataFrame = pandas.concat([pandas.Series({'Model BESS': model}),
                                             database_DataFrame.loc[model]])

        # Costs of the selected model
        self.capital[id] = component_DataFrame.loc['Capital'] * cash_exchange  # investment cost --> [€/kW] for PV and genset and converter, [€/u] for battery
        self.replacement[id] = component_DataFrame.loc['Replacement'] * cash_exchange  # replacement cost --> [€/kW] for PV and genset and converter, [€/u] for battery
        self.om[id] = component_DataFrame.loc['O&M'] * cash_exchange  # operation and maintenance cost --> [€/kW/year] for PV and converter, [€/kW/h] for genset, [€/u/year] for battery
        self.lifetime[id] = component_DataFrame.loc['Lifetime']  # lifetime [years]
        self.degradation_cost[id] = component_DataFrame.loc['Degradation cost']  # cost of cycle aging [€/kWh carged and discharged], needs sensitivity analysis

        # Performance characteristics of the selected model
        self.capacity_kWh[id] = component_DataFrame.loc['Capacity (kWh)']  # storage capacity of 1 battery [kWh]
        self.maxCharge_kW[id] = component_DataFrame.loc['Max charge (kW)']  # maximum charging power of 1 battery [kW]
        self.maxDischarge_kW[id] = component_DataFrame.loc['Max discharge (kW)']  # maximum discharging power of 1 battery [kW]
        self.SOCmin[id] = component_DataFrame.loc['SOC min']/100  # minimum state of charge [pu]
        self.SOCmax[id] = component_DataFrame.loc['SOC max']/100  # maximum state of charge [pu]
        self.tau[id] = component_DataFrame.loc['Self-discharge rate (hourly)']/100  # Energy loss ratio of the storage or self-discharge rate [pu]
        self.charEff[id] = component_DataFrame.loc['Charge eff.']/100  # Charging efficiency [pu]
        self.dischEff[id] = component_DataFrame.loc['Discharge eff.']/100  # Discharging efficiency [pu]
        self.throughput[id] = component_DataFrame.loc['Throughput']  # throughput of 1 battery [kWh]
        self.calendar_aging_anual[id] = component_DataFrame.loc['Calendar aging (anual)']/100  # annual degradation due to calendar aging [% of the storage capacity]
        SOCmax_hourly = SOCmax_aging(self.SOCmax[id], self.calendar_aging_anual[id], l_t, inc_t)
        self.SOCmax_hourly.update({(id, t): SOCmax_hourly[t] for t in l_t})
        #
        self.existent_C[id] = self.existent_u[id]*self.capacity_kWh[id]  # storage capacity [kWh] of the battery already in the system
        self.existent_Pn_char[id] = self.existent_u[id]*self.maxCharge_kW[id]  # maximum charging power [kW] of the battery already in the system
        self.existent_Pn_disch[id] = self.existent_u[id]*self.maxDischarge_kW[id]  # maximum discharging power [kW] of the battery already in the system
        #
        self.SOCini[id] = float('nan')  # state of charge at the start of an islanded period for the islandable analysis [pu]

    def empty(self):
        '''
        If no PV, then call this function.
        If all variables and parameters are a function of the number of assets, then they will be empty dictionaries
        '''
        self.id = 0  # number of the PV system
        self.id_list = []  # list with all PV system numbers


def SOCmax_aging(SOCmax, calendar_aging_anual, l_t, inc_t):
    hourly_aging = calendar_aging_anual/100 /365 /24 * inc_t
    SOCmax_hourly = {}
    for t in l_t:
        if t== l_t[0]:
            SOCmax_hourly[t] = SOCmax
        else:
            SOCmax_hourly[t] = SOCmax_hourly[t-1] - SOCmax * hourly_aging
    return SOCmax_hourly
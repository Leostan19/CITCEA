import math

class SystemClass:
    def __init__(self):
        ...

    def full(self, client_DataFrame, l_t, inc_t, name_days, emissions_cost):
        self.min_renew = client_DataFrame.loc['Minimum share of renewables'][1]/100  # minimum renewable energy contribution [pu]
        self.lifetime = int(client_DataFrame.loc['Project Lifetime'][1])  # project lifetime [years]
        self.discount_rate_optimization = client_DataFrame.loc['Discount rate optimization'][1]/100  # [pu]
        self.discount_rate = client_DataFrame.loc['Discount rate'][1] / 100  # [pu]
        self.inflation_rate = client_DataFrame.loc['Inflation rate'][1]/100  # [pu]
        annual_cost_reference = client_DataFrame.loc['Operation cost of the reference case'][1]
        if math.isnan(annual_cost_reference):  # the cost is not provided
            annual_cost_reference = 0
        self.annual_cost_reference = annual_cost_reference  # operation cost of the reference case [€/year]

        self.noSupply_cost = client_DataFrame.loc['Load not supplyed cost'][1]  # cost of the energy not supplied in island mode [€/kWh]

        self.l_t = l_t
        self.inc_t = inc_t
        self.name_days = name_days  # DataFrame for a year with all time steps, columns = ['id', 'datetime', 'mes', 'dia', 'festivo']
        self.dict_month = {0: 'Enero', 1: 'Febrero', 2: 'Marzo', 3: 'Abril', 4: 'Mayo', 5: 'Junio', 6: 'Julio',
                           7: 'Agosto', 8: 'Septiembre', 9: 'Octubre', 10: 'Noviembre', 11: 'Diciembre'}  # dictionary that relates the name of a month with a key. dict_month[key]=month_name
        self.l_month = list(range(12))  # ``list`` containing all month keys in a year
        self.dict_K_month = t_in_month(self.name_days, self.dict_month, self.l_t,
                                       self.l_month)  # dictionary that indicates the month of each time-step. dict_K_month[month,t]=value. 1: yes, 0: no
        self.dict_days_month = count_days_in_month(self.name_days, self.dict_month, self.inc_t, self.l_t,
                                                   self.l_month)  # dictionary that indicates the number fo days in each month

        emissions_reference = client_DataFrame[1]['Emissions reference']
        if math.isnan(emissions_reference):  # the cost is not provided
            emissions_reference = math.inf
        self.emissions_reference = emissions_reference  # kg CO2 / year (electrical + thermal) of the reference case
        self.emissions_reduction = client_DataFrame[1]['Minimum emissions reduction']/100
        self.max_emissions = self.emissions_reference * (1-self.emissions_reduction)
        #
        self.emissions_cost = emissions_cost


def count_days_in_month(name_days, dict_month, inc_t, l_t, l_month):
    '''
    Counts the days in each month of the year and stores the results in a dictionary
    :param name_days: DataFrame with the month, day of the week and (national) holiday in each time-step
        // filas = l_t
        // column 'mes': 'Enero', 'Febrero', ...
        // column 'dia': 'Lunes', 'Martes', ...
        // column 'festivo': 'Sí', 'No'
    :param dict_month: dictionary that relates the name of a month with a key. dict_month[key]=month_name
    :param inc_t: time-step magnitude [h]
    :param l_t: ``list`` containing all time-steps
    :param l_month: ``list`` containing all month keys in a year
    :return: dictionary that indicates the number of days in each month
    '''
    dict_days_month = {}
    for mes in l_month:
        dias = 0
        for t in l_t:
            if name_days['mes'][t] == dict_month[mes]:
                dias = dias + 1 * inc_t / 24
        dict_days_month[mes] = int(dias)
    return dict_days_month


def t_in_month(name_days, dict_month, l_t, l_month):
    '''

    :param name_days: DataFrame with the month, day of the week and (national) holiday in each time-step
        // filas = l_t
        // column 'mes': 'Enero', 'Febrero', ...
        // column 'dia': 'Lunes', 'Martes', ...
        // column 'festivo': 'Sí', 'No'
    :param dict_month: dictionary that relates the name of a month with a key. dict_month[key]=month_name
    :param l_t: ``list`` containing all time-steps
    :param l_month: ``list`` containing all month keys in a year
    :return: dictionary that indicates the month of each time-step. dict_K_month[month,t]=value. 1: yes, 0: no
    '''
    dict_K_month = {}
    for mes in l_month:
        for t in l_t:
            if name_days['mes'][t] == dict_month[mes]:
                dict_K_month[(mes, t)] = 1
            else:
                dict_K_month[(mes, t)] = 0
    return dict_K_month


####################   ...   ####################


class AllInputsClass:
    def __init__(self, System, Loads, PV, BESS, Grid,
                 EV, economic_constraints,
                 Network):
        self.System = System
        self.PV = PV
        self.BESS = BESS
        self.Grid = Grid
        self.EV = EV
        self.economic_constraints = economic_constraints
        #
        self.Network = Network
        self.Load = Loads


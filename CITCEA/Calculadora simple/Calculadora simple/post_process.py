'''
3) Leer y Exportar resultados
'''

import pandas
import math
from post_processing.get_Results import *
from post_processing.KPIs import *
from post_processing.BESS_aging import *


def post_processing(instance, save_folder, AllInputs):
    '''
    Analyse the optimization results and saves them in excel files, from the inputs and the solved model.
    :param instance: pyomo solved Grid model (instance.EV)
    :param save_folder: string with the path in which the operation results file will be saved
    :param AllInputs: data class which contains all inputs
    '''

    l_t = AllInputs.System.l_t
    inc_t = AllInputs.System.inc_t
    l_PV = AllInputs.PV.id_list
    l_BESS = AllInputs.BESS.id_list
    L_prj = int(AllInputs.System.lifetime)

    '''print('G value is:')
    print(instance.G.get_values())'''

    # Extract the results from the pyomo instance and stores them in a self-defined class
    allResults = allResultsClass(l_t, AllInputs, instance)


    ##### ##### ##### #####       Save results       ##### ##### ##### #####

    # Energy Results: sizing
    save_sizing(allResults, AllInputs, save_folder)

    # Energy Results: peration
    save_operation(allResults, AllInputs, save_folder)

    # Economic Results
    save_economics(allResults, AllInputs, save_folder)

    # Network Results
    save_network(allResults, AllInputs, save_folder)


    ##### ##### ##### #####       BESS degradation       ##### ##### ##### #####
    if len(AllInputs.BESS.id_list) != 0:
        cycles = BESS_cycles(allResults, AllInputs)
        n_peaks = count_peaks(cycles)
    else:
        n_peaks = math.nan

    return allResults, n_peaks


def dataframe_from_dict_loads(dict, columns, rows):
    '''
    Creates a DataFrame from a dictionary

    This function is equivalent to:
        df = dataframe_from_dict_CashFlow(dict, columns, rows)

        df = df.transpose()
    :param dict: initial dictionary with the structure {(index_column, index_row): value}
    :param columns: ``list`` containing the columns indexes
    :param rows: ``list`` containing the rows indexes
    :return: DataFrame with the dictionary values
    '''
    dict_fin = {}
    for col in columns:
        lista = []
        for i in rows:
            lista.insert(i, dict[col, i])
        dict_fin[col] = lista
    tabla = pandas.DataFrame(dict_fin, index=rows)
    return tabla


def save_sizing(allResults, AllInputs, save_folder):
    '''
    Generates DataFrames with the sizing results of the system (by technology model, grid connection and flexibility request)
    and saves them in an Excel file in the given folder.
    :param allResults: data class which contains all results of the optimization
    :param AllInputs: data class which contains all inputs
    :param save_folder: string with the path in which the operation results file will be saved
    '''
    # PV
    l_PV = AllInputs.PV.id_list
    dict_PV = {'name': [],
               'PV installed power (new) [kW]': []}
    for i_PV in l_PV:
        dict_PV['name'].append(AllInputs.PV.name[i_PV])
        dict_PV['PV installed power (new) [kW]'].append(allResults.PV.G[i_PV])
    table_PV = pandas.DataFrame(dict_PV, index=l_PV)

    # BESS
    l_BESS = AllInputs.BESS.id_list
    dict_BESS = {'name': [],
                 'Number of BESS installed (new) [u]': [],
                 'BESS storage capacity installed (new) [kWh]': [],
                 'BESS charging power installed (new) [kW]': [],
                 'BESS discharging power installed (new) [kW]': []}
    for i_BESS in l_BESS:
        dict_BESS['name'].append(AllInputs.BESS.name[i_BESS])
        dict_BESS['Number of BESS installed (new) [u]'].append(allResults.BESS.k_bat[i_BESS])
        dict_BESS['BESS storage capacity installed (new) [kWh]'].append(allResults.BESS.C[i_BESS])
        dict_BESS['BESS charging power installed (new) [kW]'].append(allResults.BESS.Pn_char[i_BESS])
        dict_BESS['BESS discharging power installed (new) [kW]'].append(allResults.BESS.Pn_disch[i_BESS])
    table_BESS = pandas.DataFrame(dict_BESS, index=l_BESS)

    # other
    other = [['Power is injected to the grid? (1: yes, 0: no)', allResults.Grid.lambda_inj, '']]
    table_other = pandas.DataFrame(other, columns=['Variable', 'Value', 'Units'])

    # Hired power (grid connection)
    l_Grid = AllInputs.Grid.id_list
    dict_Grid = {'name': [],
                 'P1 [kW]': [],
                 'P2 [kW]': [],
                 'P3 [kW]': [],
                 'P4 [kW]': [],
                 'P5 [kW]': [],
                 'P6 [kW]': []}
    for i_Grid in l_Grid:
        dict_Grid['name'].append(AllInputs.Grid.name[i_Grid])
        dict_Grid['P1 [kW]'].append(allResults.Grid.P_hired_N[i_Grid, 0])
        dict_Grid['P2 [kW]'].append(allResults.Grid.P_hired_N[i_Grid, 1])
        dict_Grid['P3 [kW]'].append(allResults.Grid.P_hired_N[i_Grid, 2])
        dict_Grid['P4 [kW]'].append(allResults.Grid.P_hired_N[i_Grid, 3])
        dict_Grid['P5 [kW]'].append(allResults.Grid.P_hired_N[i_Grid, 4])
        dict_Grid['P6 [kW]'].append(allResults.Grid.P_hired_N[i_Grid, 5])
    table_P_hired = pandas.DataFrame(dict_Grid, index=l_Grid)

    # print
    with pandas.ExcelWriter(save_folder+'Sizing.xlsx') as writer:
        table_PV.to_excel(writer, sheet_name='PV', float_format="%.2f")
        table_BESS.to_excel(writer, sheet_name='Battery', float_format="%.2f")
        table_other.to_excel(writer, sheet_name='other', float_format="%.2f", header=False, index=False)
        table_P_hired.to_excel(writer, sheet_name='P_hired', float_format="%.2f")

    return


def list_from_dict(dict_i_t, i, l_t):
    '''
    Creates a list from a dictionary and the first index
    :param dict_i_t: initial dictionary with the structure {(i, t): value for i in l_i for t in l_t}
    :param i: first-item index of the dictionary key
    :param l_t: ``list`` containing the indexes of the second-item of the dictionary key
    :return: ``list`` containing the values of the dictionary for the specified index
    '''
    dict_t = {t: dict_i_t[i,t] for t in l_t}
    l = list(dict_t.values())
    return l


def save_operation(allResults, AllInputs, save_folder):
    '''
    Generates DataFrames with the operation of the system (by technology model, and by load)
    and saves them in an Excel file in the given folder.
    :param allResults: data class which contains all results of the optimization
    :param AllInputs: data class which contains all inputs
    :param save_folder: string with the path in which the operation results file will be saved
    '''
    l_t = AllInputs.System.l_t

    # Grid
    l_Grid = AllInputs.Grid.id_list
    dict_Grid = {}
    for i_Grid in l_Grid:
        dict_Grid[AllInputs.Grid.name[i_Grid]+': P_hired [kW]'] = list_from_dict(allResults.Grid.P_hired_t, i_Grid, l_t)  # P_hired_t[t]
        dict_Grid[AllInputs.Grid.name[i_Grid]+': P_buy [kW]'] = list_from_dict(allResults.Grid.P_buy, i_Grid, l_t)  # P_buy[t]
        dict_Grid[AllInputs.Grid.name[i_Grid]+': P_sell [kW]'] = list_from_dict(allResults.Grid.P_sell, i_Grid, l_t)  # P_sell[t]
        dict_Grid[AllInputs.Grid.name[i_Grid]+': P_excess [kW]'] = list_from_dict(allResults.Grid.P_excess, i_Grid, l_t)  # P_excess[t]

    # PV
    l_PV = AllInputs.PV.id_list
    dict_PV = {}
    for i_PV in l_PV:
        dict_PV[AllInputs.PV.name[i_PV]+': P [kW]'] = list_from_dict(allResults.PV.P, i_PV, l_t)

    # BESS
    l_BESS = AllInputs.BESS.id_list
    dict_BESS = {}
    for i_BESS in l_BESS:
        dict_BESS[AllInputs.BESS.name[i_BESS]+': P_char [kW]'] = list_from_dict(allResults.BESS.P_char, i_BESS, l_t)
        dict_BESS[AllInputs.BESS.name[i_BESS]+': P_disch [kW]'] = list_from_dict(allResults.BESS.P_disch, i_BESS, l_t)
    for i_BESS in l_BESS:
        dict_BESS[AllInputs.BESS.name[i_BESS]+': SOC [kWh]'] = list_from_dict(allResults.BESS.SOC, i_BESS, l_t)

    # Islanded
    l_bus = AllInputs.Network.Buses.id_list
    dict_islanded = {}
    for i_bus in l_bus:
        if sum(allResults.noSupply_P[i_bus,t] for t in l_t)!=0:
            dict_islanded['Load not supplied '+AllInputs.Network.Buses.name[i_bus]+' [kW]'] = list_from_dict(allResults.noSupply_P, i_bus, l_t)  # noSupply_P[t]

    dict_all = {}
    dict_all.update(dict_Grid)
    dict_all.update(dict_PV)
    dict_all.update(dict_BESS)
    dict_all.update(dict_islanded)

    table_all = pandas.DataFrame(dict_all, index=l_t)

    l_Mev = AllInputs.EV.smart.l_Mev

    if AllInputs.EV.hay == 1 and AllInputs.EV.immediate0_smart1 == 1: # Flexibility: EV smart charging
        table_EV = dataframe_from_dict_loads(allResults.EV.P, l_Mev, l_t)
    dict_cL = {}
    #dict_cL['Critical load'] = list(AllInputs.System.critical_Load.values())
    if AllInputs.EV.hay == 1 and AllInputs.EV.immediate0_smart1 == 0:
        dict_cL['EV immediate'] = list(AllInputs.EV.immediate.values())
    table_cL = pandas.DataFrame(dict_cL, index=l_t)

    dict_renGrid = {}
    for i_Grid in l_Grid:
        dict_Grid['Renewables from electrical grid' + AllInputs.Grid.name[i_Grid]] = \
            {t: AllInputs.Grid.renewable_factor[i_Grid, t]*(allResults.Grid.P_buy[i_Grid, t] + allResults.Grid.P_excess[i_Grid, t]) for t in l_t}
        dict_renGrid['Renewable factor electrical grid' + AllInputs.Grid.name[i_Grid]] = {t: AllInputs.Grid.renewable_factor[i_Grid, t] for t in l_t}
        dict_renGrid['CO2 emission factor electrical grid' + AllInputs.Grid.name[i_Grid]] = {t: AllInputs.Grid.emissions[i_Grid, t] for t in l_t}
    table_renGrid = pandas.DataFrame(dict_renGrid, index=l_t)

    with pandas.ExcelWriter(save_folder+'Operation.xlsx') as writer:
        table_all.to_excel(writer, sheet_name='General', float_format="%.2f")
        if AllInputs.EV.hay == 1 and AllInputs.EV.immediate0_smart1 == 1:
            # Flexibilidad: carga shiftable modular: EV smart charging
            table_EV.to_excel(writer, sheet_name='EV smart charging', float_format="%.2f")
        table_cL.to_excel(writer, sheet_name='critical load', float_format="%.2f")
        if AllInputs.Grid.conected1_islanded0 == 1:
            table_renGrid.to_excel(writer, sheet_name='renewables from grid', float_format="%.2f")

    return


def save_economics(allResults, AllInputs, save_folder):
    '''
    Calculates the economic results,
    generates DataFrames with those results
    and saves them in an Excel file in the given folder.
    :param allResults: data class which contains all results of the optimization
    :param AllInputs: data class which contains all inputs
    :param save_folder: string with the path in which the operation results file will be saved
    '''
    l_t = AllInputs.System.l_t
    inc_t = AllInputs.System.inc_t
    L_prj = int(AllInputs.System.lifetime)
    l_PV = AllInputs.PV.id_list
    l_BESS = AllInputs.BESS.id_list
    l_Grid = AllInputs.Grid.id_list
    l_bus = AllInputs.Network.Buses.id_list

    # equipment costs: PV, BESS, GS
    dict_equipment_cost = {'CAPEX [€]': [], 'incentives [€]': [], 'OPEX [€/year]': [], 'fuel [€/year]': [],
                         'emissions [€/year]': [], 'replacement [€]': [], 'total cost [€] in project lifetime': []}
    components = []
    for i_PV in l_PV:
        components.append(AllInputs.PV.name[i_PV])
        dict_equipment_cost['CAPEX [€]'].append(allResults.PV.C_capex[i_PV])
        dict_equipment_cost['incentives [€]'].append(allResults.PV.C_incentives[i_PV])
        dict_equipment_cost['OPEX [€/year]'].append(allResults.PV.C_opex[i_PV])
        dict_equipment_cost['fuel [€/year]'].append(0)
        dict_equipment_cost['emissions [€/year]'].append(0)
        dict_equipment_cost['replacement [€]'].append(allResults.PV.C_replacement[i_PV])
        C_PV_total = allResults.PV.C_capex[i_PV] - allResults.PV.C_incentives[i_PV] \
                     + allResults.PV.C_opex[i_PV] * L_prj + allResults.PV.C_replacement[i_PV]
        dict_equipment_cost['total cost [€] in project lifetime'].append(C_PV_total)
    for i_BESS in l_BESS:
        components.append(AllInputs.BESS.name[i_BESS])
        dict_equipment_cost['CAPEX [€]'].append(allResults.BESS.C_capex[i_BESS])
        dict_equipment_cost['incentives [€]'].append(allResults.BESS.C_incentives[i_BESS])
        dict_equipment_cost['OPEX [€/year]'].append(allResults.BESS.C_opex[i_BESS])
        dict_equipment_cost['fuel [€/year]'].append(0)
        dict_equipment_cost['emissions [€/year]'].append(0)
        dict_equipment_cost['replacement [€]'].append(allResults.BESS.C_replacement[i_BESS])
        C_BESS_total = allResults.BESS.C_capex[i_BESS] - allResults.BESS.C_incentives[i_BESS] \
                       + allResults.BESS.C_opex[i_BESS] * L_prj + allResults.BESS.C_replacement[i_BESS]
        dict_equipment_cost['total cost [€] in project lifetime'].append(C_BESS_total)
    components.append('total')
    C_capex_total = sum(dict_equipment_cost['CAPEX [€]'])
    C_incentivos_total = sum(dict_equipment_cost['incentives [€]'])
    C_om_total = sum(dict_equipment_cost['OPEX [€/year]'])
    C_fuel_total = sum(dict_equipment_cost['fuel [€/year]'])
    C_emissions_total = sum(dict_equipment_cost['emissions [€/year]'])
    C_replacement_total = sum(dict_equipment_cost['replacement [€]'])
    dict_equipment_cost['CAPEX [€]'].append(C_capex_total)
    dict_equipment_cost['incentives [€]'].append(C_incentivos_total)
    dict_equipment_cost['OPEX [€/year]'].append(C_om_total)
    dict_equipment_cost['fuel [€/year]'].append(C_fuel_total)
    dict_equipment_cost['emissions [€/year]'].append(C_emissions_total)
    dict_equipment_cost['replacement [€]'].append(C_replacement_total)
    C_equipment_total = C_capex_total - C_incentivos_total + (C_om_total + C_fuel_total + C_emissions_total) * L_prj \
                        + C_replacement_total
    dict_equipment_cost['total cost [€] in project lifetime'].append(C_equipment_total)
    table_equipment_cost = pandas.DataFrame(dict_equipment_cost, index=components)

    # Grid costs
    C_grid_total = sum(allResults.Grid.C_buy[i_Grid] - allResults.Grid.R_sell[i_Grid]
                       + allResults.Grid.C_power[i_Grid] + allResults.Grid.C_penalisation[i_Grid]
                       + allResults.Grid.C_emission[i_Grid] for i_Grid in l_Grid)
    dict_grid_cost1 = {'name': [], 'Buy energy cost [€/year]': [], 'Sell energy income [€/year]': [],
                       'Hired power cost [€/year]': [], 'Power penalization cost [€/year]': [],
                       'CO2 emissions [kgCO2/year]': [], 'CO2 emissions cost [€/year]': []}
    for i_Grid in l_Grid:
        dict_grid_cost1['name'].append(AllInputs.Grid.name[i_Grid])
        dict_grid_cost1['Buy energy cost [€/year]'].append(allResults.Grid.C_buy[i_Grid])
        dict_grid_cost1['Sell energy income [€/year]'].append(allResults.Grid.R_sell[i_Grid])
        dict_grid_cost1['Hired power cost [€/year]'].append(allResults.Grid.C_power[i_Grid])
        dict_grid_cost1['Power penalization cost [€/year]'].append(allResults.Grid.C_penalisation[i_Grid])
        dict_grid_cost1['CO2 emissions [kgCO2/year]'].append(allResults.Grid.C_emission[i_Grid]/AllInputs.System.emissions_cost)
        dict_grid_cost1['CO2 emissions cost [€/year]'].append(allResults.Grid.C_emission[i_Grid])
    table_grid1 = pandas.DataFrame(dict_grid_cost1, index=l_Grid)
    empty_df = pandas.DataFrame(columns=[' ','  ','   '])
    empty_df = empty_df.reindex(range(l_Grid[-1]))
    dict_grid_cost2 = [['Islanded: load not supplied cost', allResults.noSupply_C, '€/year']]
    table_grid2 = pandas.DataFrame(dict_grid_cost2, columns=['Variable', 'Value', 'Units'])
    table_grid = pandas.concat([table_grid1, empty_df, table_grid2], axis=1)

    # Flexibility costs
    table_flex_cost_Mev = pandas.DataFrame([allResults.EV.flexibility_cost]).transpose()
    table_flex_cost_Mev.columns = ['EV smart charging [€]']
    table_flex_cost = pandas.concat([table_flex_cost_Mev], axis=1)

    # Optimization indicators
    payback_optimization = allResults.Economic_indicators.payback  # payback == (total_capex - total_incentives + total_replacement) / (m.annual_cost_reference - m.total_annual_costs)
    ROI_optimization = allResults.Economic_indicators.ROI  # ROI = (annual_cost_reference - total_annual_costs) / total_investment
    summary_cost = [['total investment', allResults.Economic_indicators.total_investment, '€'],
                    ['annual costs', allResults.Economic_indicators.total_annual_costs, '€/year'],
                    ['Payback', payback_optimization, 'years'],
                    ['ROI', ROI_optimization, '%']]
    table_summary = pandas.DataFrame(summary_cost, columns=['Variable', 'Value', 'Units'])

    # KPIs:
    i = AllInputs.System.discount_rate
    (CashFlow, CashFlowComparison) = calc_CashFlow(allResults, AllInputs, i)
    (CashFlow_desglosado, CashFlowComparison_desglosado) = calc_CashFlow_desglosado(allResults, AllInputs, i)
    NetPresentCost_nominal = calc_NetPresentCost(CashFlow, 'nominal')
    NetPresentCost_discounted = calc_NetPresentCost(CashFlow, 'discounted')
    TotalAnnualizedCost_nominal = calc_TotalAnnualizedCost(NetPresentCost_nominal, i, L_prj)
    TotalAnnualizedCost_discounted = calc_TotalAnnualizedCost(NetPresentCost_discounted, i, L_prj)
    operating_cost_assets = calc_operating_cost(allResults, AllInputs, l_Grid, 'assets')
    operating_cost_grid = calc_operating_cost(allResults, AllInputs, l_Grid, 'grid')
    operating_cost_total = calc_operating_cost(allResults, AllInputs, l_Grid, 'total')
    total_E_served = calc_total_E_served(allResults, AllInputs, l_t, l_Grid, l_bus, inc_t)
    self_consumption = calc_self_consumption(allResults, l_t, inc_t, l_PV, l_bus)
    self_production = calc_self_production(allResults, l_t, inc_t, l_PV, l_bus)
    renewable_fraction = calc_renewable_fraction(allResults, AllInputs, inc_t, total_E_served, l_t, l_PV, l_Grid)
    ROI_nominal = calc_ROI(CashFlowComparison, 'nominal', L_prj)  # do not calculate it in the reference case
    ROI_discounted = calc_ROI(CashFlowComparison, 'discounted', L_prj)  # do not calculate it in the reference case
    payback_nominal = calc_payback(CashFlowComparison, 'nominal', L_prj)
    payback_discounted = calc_payback(CashFlowComparison, 'discounted', L_prj)
    LCOE_nominal = LCOE_calc(TotalAnnualizedCost_nominal, total_E_served)
    LCOE_discounted = LCOE_calc(TotalAnnualizedCost_discounted, total_E_served)
    KPIs = [['Discount rate (input)', i*100, '%'],
            ['Net Present Cost nominal', NetPresentCost_nominal/1000, 'k€'],
            ['Net Present Cost discounted', NetPresentCost_discounted/1000, 'k€'],
            ['Total Annualized Cost nominal', TotalAnnualizedCost_nominal/1000, 'k€/year'],
            ['Total Annualized Cost discounted', TotalAnnualizedCost_discounted/1000, 'k€/year'],
            ['Assets operating cost', operating_cost_assets/1000, 'k€/year'],
            ['Grid operating cost', operating_cost_grid/1000, 'k€/year'],
            ['Total operating cost', operating_cost_total/1000, 'k€/year'],
            ['total electricity served', total_E_served, 'kWh'],
            ['Grid CO2 emissions', sum(allResults.Grid.C_emission[i_Grid] for i_Grid in l_Grid)/AllInputs.System.emissions_cost, 'kg CO2/year'],
            ['Self-consumption', self_consumption*100, '%'],
            ['Self-production', self_production*100, '%'],
            ['Electrical renewable fraction', renewable_fraction*100, '%'],
            ['ROI nominal', ROI_nominal, '%'],
            ['ROI discounted', ROI_discounted, '%'],
            ['Payback nominal', payback_nominal, 'years'],
            ['Payback discounted', payback_discounted, 'years'],
            ['LCOE nominal', LCOE_nominal, '€/kWh'],
            ['LCOE discounted', LCOE_discounted, '€/kWh]']]
    table_KPIs = pandas.DataFrame(KPIs, columns=['Variable', 'Value', 'Units'])

    # Save in Excel
    with pandas.ExcelWriter(save_folder+'Economic.xlsx') as writer:
        table_equipment_cost.to_excel(writer, sheet_name='equipment', float_format="%.2f")
        table_grid.to_excel(writer, sheet_name='grid', float_format="%.2f", header=False, index=False)
        table_flex_cost.to_excel(writer, sheet_name='flexibility costs', float_format="%.2f")
        table_summary.to_excel(writer, sheet_name='optimization indicators', float_format="%.2f", header=False, index=False)
        CashFlow.to_excel(writer, sheet_name='CashFlow (€)', float_format="%.2f")
        CashFlow_desglosado.to_excel(writer, sheet_name='CashFlow desglosado (€)', float_format="%.2f")
        CashFlowComparison.to_excel(writer, sheet_name='CashFlow comparison (€)', float_format="%.2f")
        table_KPIs.to_excel(writer, sheet_name='KPI', float_format="%.2f", header=False, index=False)

    return


def save_network(allResults, AllInputs, save_folder):
    l_bus = AllInputs.Network.Buses.id_list
    l_t = AllInputs.System.l_t
    Sb = AllInputs.Network.Sb


    def dataframe_from_dict(dict, columns, filas):
        dict_fin = {}
        for col in columns:
            list = []
            for i in filas:
                list.insert(i,dict[col,i])
            dict_fin[col] = list
        table = pandas.DataFrame(dict_fin, index=filas)
        return table

    if AllInputs.Network.PF_type == 'DC-OPF':
        table_Pinj = dataframe_from_dict(allResults.Network.Pinj, l_bus, l_t)  # Pinj[i_bus, t]

        table_thetaV = dataframe_from_dict(allResults.Network.thetaV, l_bus, l_t)  # thetaV[i_bus, t]

        # Pline[i_bus1, i_bus2, t]
        dict_Pline = {}
        for i_bus1 in l_bus:
            for i_bus2 in l_bus:
                if AllInputs.Network.Lines.G_bus[i_bus1, i_bus2] != 0 and i_bus1 != i_bus2:
                    dict_linea = {t: allResults.Network.Pline[i_bus1, i_bus2, t] for t in l_t}
                    name = str(i_bus1) + '-' + str(i_bus2)
                    dict_Pline[name] = list(dict_linea.values())
        table_Pline = pandas.DataFrame(dict_Pline, index=l_t)

        # Save in Excel
        with pandas.ExcelWriter(save_folder + 'Network.xlsx') as writer:
            table_Pinj.to_excel(writer, sheet_name='Pinj', float_format="%.6f")
            table_thetaV.to_excel(writer, sheet_name='thetaV', float_format="%.6f")
            table_Pline.to_excel(writer, sheet_name='Pline', float_format="%.6f")


    elif AllInputs.Network.PF_type == 'AC-OPF':
        ...
        table_Pinj = dataframe_from_dict(allResults.Network.Pinj, l_bus, l_t)  # Pinj[i_bus, t]

        table_Qinj = dataframe_from_dict(allResults.Network.Qinj, l_bus, l_t)  # Qinj[i_bus, t]

        # Pline[i_bus1, i_bus2, t]
        dict_Pline = {}
        for i_bus1 in l_bus:
            for i_bus2 in l_bus:
                if AllInputs.Network.Lines.G_bus[i_bus1, i_bus2] != 0:
                    dict_linea = {t: allResults.Network.Pline[i_bus1, i_bus2, t] for t in l_t}
                    name = str(i_bus1) + '-' + str(i_bus2)
                    dict_Pline[name] = list(dict_linea.values())
        table_Pline = pandas.DataFrame(dict_Pline, index=l_t)

        # Qline[i_bus1, i_bus2, t]
        dict_Qline = {}
        for i_bus1 in l_bus:
            for i_bus2 in l_bus:
                if AllInputs.Network.Lines.G_bus[i_bus1, i_bus2] != 0:
                    dict_linea = {t: allResults.Network.Qline[i_bus1, i_bus2, t] for t in l_t}
                    name = str(i_bus1) + '-' + str(i_bus2)
                    dict_Qline[name] = list(dict_linea.values())
        table_Qline = pandas.DataFrame(dict_Qline, index=l_t)

        # c[i_bus1, i_bus2, t]  --> c[i_bus, i_bus, t] = V[i_bus, t]**2
        # s[i_bus1, i_bus2, t]

        dict_V = {}
        for i_bus in l_bus:
            dict_linea = {t: math.sqrt(max(allResults.Network.c[i_bus, i_bus, t], 0)) for t in l_t}
            name = str(i_bus)
            dict_V[name] = list(dict_linea.values())
        table_V = pandas.DataFrame(dict_V, index=l_t)

        # i_line_squared[i_bus1, i_bus2, t]
        dict_i_line = {}
        for i_bus1 in l_bus:
            for i_bus2 in l_bus:
                if AllInputs.Network.Lines.G_bus[i_bus1, i_bus2] != 0 and i_bus1 != i_bus2:
                    dict_linea = {t: math.sqrt(max(allResults.Network.i_line_squared[i_bus1, i_bus2, t], 0)) for t in
                                  l_t}
                    name = str(i_bus1) + '-' + str(i_bus2)
                    dict_i_line[name] = list(dict_linea.values())
        table_i_line = pandas.DataFrame(dict_i_line, index=l_t)

        # Save in Excel
        with pandas.ExcelWriter(save_folder + 'Network.xlsx') as writer:
            table_Pinj.to_excel(writer, sheet_name='Pinj', float_format="%.6f")
            table_Qinj.to_excel(writer, sheet_name='Qinj', float_format="%.6f")
            table_Pline.to_excel(writer, sheet_name='Pline', float_format="%.6f")
            table_Qline.to_excel(writer, sheet_name='Qline', float_format="%.6f")
            table_V.to_excel(writer, sheet_name='V', float_format="%.6f")
            table_i_line.to_excel(writer, sheet_name='i_line', float_format="%.6f")


    else:  # PF_type == 'economic_dispatch'
        ...

    return

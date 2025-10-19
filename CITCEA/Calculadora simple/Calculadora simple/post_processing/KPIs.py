import pandas


def calc_discount_rate(AllInputs):
    '''
    Calculates the discount rate as i = (i'-f)/(1+f) where i' is nominal discount rate and f is inflation
    :param AllInputs: data class which contains all inputs
    :return: discount rate [pu]
    '''
    nominal_dicount_rate = AllInputs.System.discount_rate
    inflation_rate = AllInputs.System.inflation_rate
    i = (nominal_dicount_rate - inflation_rate) / (1 + inflation_rate)
    return i


def dataframe_from_dict_CashFlow(dict, rows, columns):
    '''
    Creates a DataFrame from a dictionary
    :param dict: initial dictionary with the structure {(index_row, index_column): value}
    :param columns: ``list`` containing the columns indexes
    :param rows: ``list`` containing the rows indexes
    :return: DataFrame with the dictionary values
    '''
    dict_end = {}
    for col in columns:
        list_ = []
        for i in rows:
            list_.append(dict[i, col])
        dict_end[col] = list_
    tabla = pandas.DataFrame(dict_end, index=rows)
    return tabla


def calc_CashFlow(allResults, AllInputs, i=None):
    '''
    Obtains the Cash Flow from the optimization results, project lifetime and discount rate.
    This cash flow is broken down by technology/asset systems.
    :param allResults: data class which contains all results of the optimization
    :param AllInputs: data class which contains all inputs
    :param i: discount rate [pu]
    :return: DataFrame containing the Cash Flow [€],
    and DataFrame containing the cash flow comparison with the reference case [€]
    '''
    # TODO: correction factor for the grid prices variation along the years is not considered yet

    L_prj = int(AllInputs.System.lifetime)

    l_PV = AllInputs.PV.id_list
    l_BESS = AllInputs.BESS.id_list
    l_Grid = AllInputs.Grid.id_list

    names_CashFlow = []
    if l_PV:
        names_CashFlow.append('PV CAPEX')
    if l_BESS:
        names_CashFlow.append('BESS CAPEX')
    if l_PV:
        names_CashFlow.append('PV incentives')
    if l_BESS:
        names_CashFlow.append('BESS incentives')
    if l_PV:
        names_CashFlow.append('PV replacements')
    if l_BESS:
        names_CashFlow.append('BESS replacements')
    if l_PV:
        names_CashFlow.append('PV OPEX')
    if l_BESS:
        names_CashFlow.append('BESS OPEX')
    if l_BESS:
        names_CashFlow.append('BESS degradation')
    if l_Grid:
        names_CashFlow.append('Grid buy energy costs')
        names_CashFlow.append('Grid sell energy incomes')
        names_CashFlow.append('Grid hired power costs')
        names_CashFlow.append('Grid power penalization costs')
        names_CashFlow.append('Grid emisions costs')
    names_CashFlow.append('Loads flexibility cost')
    names_CashFlow.append('Loads not supplied cost')
                     # +['Cash Flow nominal', 'Cash Flow discounted',
                     # 'Cumulative Cash Flow nominal', 'Cumulative Cash Flow discounted']
    CashFlow_dict = {(name, year): 0 for name in names_CashFlow for year in list(range(1 + L_prj))}

    # CashFlow[column][row] = new value  //  CashFlow_dict[row, column] = new value
    CashFlow_dict['PV CAPEX', 0] = sum(allResults.PV.C_capex[i_PV] for i_PV in l_PV)
    CashFlow_dict['BESS CAPEX', 0] = sum(allResults.BESS.C_capex[i_BESS] for i_BESS in l_BESS)
    CashFlow_dict['PV incentives', 0] = - sum(allResults.PV.C_incentives[i_PV] for i_PV in l_PV)
    CashFlow_dict['BESS incentives', 0] = - sum(allResults.BESS.C_incentives[i_BESS] for i_BESS in l_BESS)
    for year in list(range(1, 1 + L_prj)):
        CashFlow_dict['PV OPEX', year] = sum(allResults.PV.C_opex[i_PV] for i_PV in l_PV)
        CashFlow_dict['BESS OPEX', year] = sum(allResults.BESS.C_opex[i_BESS] for i_BESS in l_BESS)
        CashFlow_dict['BESS degradation', year] = sum(allResults.BESS.C_degradation[i_BESS] for i_BESS in l_BESS)
        CashFlow_dict['Grid buy energy costs', year] = sum(allResults.Grid.C_buy[i_Grid] for i_Grid in l_Grid)
        CashFlow_dict['Grid sell energy incomes', year] = - sum(allResults.Grid.R_sell[i_Grid] for i_Grid in l_Grid)
        CashFlow_dict['Grid hired power costs', year] = sum(allResults.Grid.C_power[i_Grid] for i_Grid in l_Grid)
        CashFlow_dict['Grid power penalization costs', year] = sum(allResults.Grid.C_penalisation[i_Grid] for i_Grid in l_Grid)
        CashFlow_dict['Grid emisions costs', year] = sum(allResults.Grid.C_emission[i_Grid] for i_Grid in l_Grid)
        CashFlow_dict['Loads flexibility cost', year] = allResults.Economic_indicators.total_flexibility_cost
        CashFlow_dict['Loads not supplied cost', year] = allResults.noSupply_C
        for i_PV in l_PV:
            if (year % AllInputs.PV.lifetime[i_PV]) == 0 and year != L_prj:
                CashFlow_dict['PV replacements', year] = allResults.PV.C_replacement1[i_PV]
        for i_BESS in l_BESS:
            if (year % AllInputs.BESS.lifetime[i_BESS]) == 0 and year != L_prj:
                CashFlow_dict['BESS replacements', year] = allResults.BESS.C_replacement1[i_BESS]
    for year in list(range(1 + L_prj)):
        CashFlow_dict['Cash Flow nominal', year] = sum(CashFlow_dict[nom, year] for nom in names_CashFlow)  # nominal, without discount rate
        if i:  # if discount rate is given
            factor = 1 / ((1 + i) ** year)
            CashFlow_dict['Cash Flow discounted', year] = CashFlow_dict['Cash Flow nominal', year] * factor
    CashFlow_dict['Cumulative Cash Flow nominal', 0] = CashFlow_dict['Cash Flow nominal', 0]
    if i:  # if discount rate is given
        CashFlow_dict['Cumulative Cash Flow discounted', 0] = CashFlow_dict['Cash Flow discounted', 0]
    for year in list(range(1, 1 + L_prj)):
        CashFlow_dict['Cumulative Cash Flow nominal', year] = CashFlow_dict['Cumulative Cash Flow nominal', year - 1] + \
                                                             CashFlow_dict['Cash Flow nominal', year]
        if i:  # if discount rate is given
            CashFlow_dict['Cumulative Cash Flow discounted', year] = CashFlow_dict['Cumulative Cash Flow discounted', year - 1] + \
                                                                    CashFlow_dict['Cash Flow discounted', year]
    names_total_CashFlow = names_CashFlow + ['Cash Flow nominal', 'Cash Flow discounted',
                                           'Cumulative Cash Flow nominal', 'Cumulative Cash Flow discounted']
    CashFlow = dataframe_from_dict_CashFlow(CashFlow_dict, names_total_CashFlow, list(range(1 + L_prj)))

    # Comparison with the reference case
    names_CashFlowComparison = ['Costs of the current case (+)',
                                'Operating costs of the reference case (-)',
                                'Cash Flow nominal', 'Cash Flow discounted',
                                'Cumulative Cash Flow nominal', 'Cumulative Cash Flow discounted']
    CashFlowComparison_dict = {(name, year): 0 for name in names_CashFlowComparison for year in list(range(1 + L_prj))}
    for year in list(range(1 + L_prj)):
        CashFlowComparison_dict['Costs of the current case (+)', year] = CashFlow_dict['Cash Flow nominal', year]
    for year in list(range(1, 1 + L_prj)):
        CashFlowComparison_dict['Operating costs of the reference case (-)', year] = - AllInputs.System.annual_cost_reference
    for year in list(range(1 + L_prj)):
        CashFlowComparison_dict['Cash Flow nominal', year] = sum(CashFlowComparison_dict[nom, year] for nom in names_CashFlowComparison)  # nominal, without discount rate
        if i:  # if discount rate is given
            factor = 1 / ((1 + i) ** year)
            CashFlowComparison_dict['Cash Flow discounted', year] = CashFlowComparison_dict['Cash Flow nominal', year] * factor
    CashFlowComparison_dict['Cumulative Cash Flow nominal', 0] = CashFlowComparison_dict['Cash Flow nominal', 0]
    if i:  # if discount rate is given
        CashFlowComparison_dict['Cumulative Cash Flow discounted', 0] = CashFlowComparison_dict['Cash Flow discounted', 0]
    for year in list(range(1, 1 + L_prj)):
        CashFlowComparison_dict['Cumulative Cash Flow nominal', year] = CashFlowComparison_dict['Cumulative Cash Flow nominal', year - 1] + \
                                                                        CashFlowComparison_dict['Cash Flow nominal', year]
        if i:  # if discount rate is given
            CashFlowComparison_dict['Cumulative Cash Flow discounted', year] = CashFlowComparison_dict['Cumulative Cash Flow discounted', year - 1] + \
                                                                               CashFlowComparison_dict['Cash Flow discounted', year]
    CashFlowComparison = dataframe_from_dict_CashFlow(CashFlowComparison_dict, names_CashFlowComparison,
                                                      list(range(1 + L_prj)))

    return CashFlow, CashFlowComparison


def calc_CashFlow_desglosado(allResults, AllInputs, i=None):
    '''
    Obtains the Cash Flow from the optimization results, project lifetime and discount rate.
    This cash flow is broken down by subsystems (technology models).
    :param allResults: data class which contains all results of the optimization
    :param AllInputs: data class which contains all inputs
    :param i: discount rate [pu]
    :return: DataFrame containing the Cash Flow [€],
    and DataFrame containing the cash flow comparison with the reference case [€]
    '''
    # TODO: correction factor for the grid prices variation along the years is not considered yet

    L_prj = int(AllInputs.System.lifetime)

    l_PV = AllInputs.PV.id_list
    l_BESS = AllInputs.BESS.id_list
    l_Grid = AllInputs.Grid.id_list

    names_CashFlow = []
    for i_PV in l_PV:
        names_CashFlow.append(AllInputs.PV.name[i_PV] + ' CAPEX')
    for i_BESS in l_BESS:
        names_CashFlow.append(AllInputs.BESS.name[i_BESS] + ' CAPEX')
    for i_PV in l_PV:
        names_CashFlow.append(AllInputs.PV.name[i_PV] + ' incentives')
    for i_BESS in l_BESS:
        names_CashFlow.append(AllInputs.BESS.name[i_BESS] + ' incentives')
    for i_PV in l_PV:
        names_CashFlow.append(AllInputs.PV.name[i_PV] + ' replacements')
    for i_BESS in l_BESS:
        names_CashFlow.append(AllInputs.BESS.name[i_BESS] + ' replacements')
    for i_PV in l_PV:
        names_CashFlow.append(AllInputs.PV.name[i_PV] + ' OPEX')
    for i_BESS in l_BESS:
        names_CashFlow.append(AllInputs.BESS.name[i_BESS] + ' OPEX')
    for i_BESS in l_BESS:
        names_CashFlow.append(AllInputs.BESS.name[i_BESS] + ' degradation')
    for i_Grid in l_Grid:
        names_CashFlow.append(AllInputs.Grid.name[i_Grid] + ' buy energy costs')
    for i_Grid in l_Grid:
        names_CashFlow.append(AllInputs.Grid.name[i_Grid] + ' sell energy incomes')
    for i_Grid in l_Grid:
        names_CashFlow.append(AllInputs.Grid.name[i_Grid] + ' hired power costs')
    for i_Grid in l_Grid:
        names_CashFlow.append(AllInputs.Grid.name[i_Grid] + ' power penalization costs')
    for i_Grid in l_Grid:
        names_CashFlow.append(AllInputs.Grid.name[i_Grid] + ' emisions costs')
    names_CashFlow = names_CashFlow + ['Loads flexibility cost', 'Loads not supplied cost']
                     # + ['Cash Flow nominal', 'Cash Flow discounted',
                     # 'Cumulative Cash Flow nominal', 'Cumulative Cash Flow discounted']
    CashFlow_dict = {(name, year): 0 for name in names_CashFlow for year in list(range(1 + L_prj))}

    # CashFlow[column][row] = new value  //  CashFlow_dict[row, column] = new value
    for i_PV in l_PV:
        CashFlow_dict[AllInputs.PV.name[i_PV] + ' CAPEX', 0] = allResults.PV.C_capex[i_PV]
        CashFlow_dict[AllInputs.PV.name[i_PV] + ' incentives', 0] = - allResults.PV.C_incentives[i_PV]
    for i_BESS in l_BESS:
        CashFlow_dict[AllInputs.BESS.name[i_BESS] + ' CAPEX', 0] = allResults.BESS.C_capex[i_BESS]
        CashFlow_dict[AllInputs.BESS.name[i_BESS] + ' incentives', 0] = - allResults.BESS.C_incentives[i_BESS]
    for year in list(range(1, 1 + L_prj)):
        for i_PV in l_PV:
            CashFlow_dict[AllInputs.PV.name[i_PV] + ' OPEX', year] = allResults.PV.C_opex[i_PV]
            if (year % AllInputs.PV.lifetime[i_PV]) == 0 and year != L_prj:
                CashFlow_dict[AllInputs.PV.name[i_PV] + ' replacements', year] = allResults.PV.C_replacement1[i_PV]
        for i_BESS in l_BESS:
            CashFlow_dict[AllInputs.BESS.name[i_BESS] + ' OPEX', year] = allResults.BESS.C_opex[i_BESS]
            CashFlow_dict[AllInputs.BESS.name[i_BESS] + ' degradation', year] = allResults.BESS.C_degradation[i_BESS]
            if (year % AllInputs.BESS.lifetime[i_BESS]) == 0 and year != L_prj:
                CashFlow_dict[AllInputs.BESS.name[i_BESS] + ' replacements', year] = allResults.BESS.C_replacement1[i_BESS]
        for i_Grid in l_Grid:
            CashFlow_dict[AllInputs.Grid.name[i_Grid] + ' buy energy costs', year] = allResults.Grid.C_buy[i_Grid]
            CashFlow_dict[AllInputs.Grid.name[i_Grid] + ' sell energy incomes', year] = allResults.Grid.R_sell[i_Grid]
            CashFlow_dict[AllInputs.Grid.name[i_Grid] + ' hired power costs', year] = allResults.Grid.C_power[i_Grid]
            CashFlow_dict[AllInputs.Grid.name[i_Grid] + ' power penalization costs', year] = allResults.Grid.C_penalisation[i_Grid]
            CashFlow_dict[AllInputs.Grid.name[i_Grid] + ' emisions costs', year] = allResults.Grid.C_emission[i_Grid]
        CashFlow_dict['Loads not supplied cost', year] = allResults.noSupply_C
    for year in list(range(1 + L_prj)):
        CashFlow_dict['Cash Flow nominal', year] = sum(CashFlow_dict[nom, year] for nom in names_CashFlow)  # nominal, without discount rate
        if i:  # if discount rate is given
            factor = 1 / ((1 + i) ** year)
            CashFlow_dict['Cash Flow discounted', year] = CashFlow_dict['Cash Flow nominal', year] * factor
    CashFlow_dict['Cumulative Cash Flow nominal', 0] = CashFlow_dict['Cash Flow nominal', 0]
    if i:  # if discount rate is given
        CashFlow_dict['Cumulative Cash Flow discounted', 0] = CashFlow_dict['Cash Flow discounted', 0]
    for year in list(range(1, 1 + L_prj)):
        CashFlow_dict['Cumulative Cash Flow nominal', year] = CashFlow_dict['Cumulative Cash Flow nominal', year - 1] + \
                                                             CashFlow_dict['Cash Flow nominal', year]
        if i:  # if discount rate is given
            CashFlow_dict['Cumulative Cash Flow discounted', year] = CashFlow_dict['Cumulative Cash Flow discounted', year - 1] + \
                                                                    CashFlow_dict['Cash Flow discounted', year]
    names_total_CashFlow = names_CashFlow + ['Cash Flow nominal', 'Cash Flow discounted',
                                           'Cumulative Cash Flow nominal', 'Cumulative Cash Flow discounted']
    CashFlow = dataframe_from_dict_CashFlow(CashFlow_dict, names_total_CashFlow, list(range(1 + L_prj)))

    # Comparison with the reference case
    names_CashFlowComparison = ['Costs of the current case (+)',
                                'Operating costs of the reference case (-)',
                                'Cash Flow nominal', 'Cash Flow discounted',
                                'Cumulative Cash Flow nominal', 'Cumulative Cash Flow discounted']
    CashFlowComparison_dict = {(name, year): 0 for name in names_CashFlowComparison for year in list(range(1 + L_prj))}
    for year in list(range(1 + L_prj)):
        CashFlowComparison_dict['Costs of the current case (+)', year] = CashFlow_dict['Cash Flow nominal', year]
    for year in list(range(1, 1 + L_prj)):
        CashFlowComparison_dict['Operating costs of the reference case (-)', year] = - AllInputs.System.annual_cost_reference
    for year in list(range(1 + L_prj)):
        CashFlowComparison_dict['Cash Flow nominal', year] = sum(CashFlowComparison_dict[nom, year] for nom in names_CashFlowComparison)  # nominal, without discount rate
        if i:  # if discount rate is given
            factor = 1 / ((1 + i) ** year)
            CashFlowComparison_dict['Cash Flow discounted', year] = CashFlowComparison_dict['Cash Flow nominal', year] * factor
    CashFlowComparison_dict['Cumulative Cash Flow nominal', 0] = CashFlowComparison_dict['Cash Flow nominal', 0]
    if i:  # if discount rate is given
        CashFlowComparison_dict['Cumulative Cash Flow discounted', 0] = CashFlowComparison_dict['Cash Flow discounted', 0]
    for year in list(range(1, 1 + L_prj)):
        CashFlowComparison_dict['Cumulative Cash Flow nominal', year] = CashFlowComparison_dict['Cumulative Cash Flow nominal', year - 1] + \
                                                                        CashFlowComparison_dict['Cash Flow nominal', year]
        if i:  # if discount rate is given
            CashFlowComparison_dict['Cumulative Cash Flow discounted', year] = CashFlowComparison_dict['Cumulative Cash Flow discounted', year - 1] + \
                                                                               CashFlowComparison_dict['Cash Flow discounted', year]
    CashFlowComparison = dataframe_from_dict_CashFlow(CashFlowComparison_dict, names_CashFlowComparison,
                                                      list(range(1 + L_prj)))

    return CashFlow, CashFlowComparison


def calc_NetPresentCost(CashFlow_DataFrame, type_):
    '''
    Calculates the Net Present Cost from the Cash Flow, nominal or discounted type has to be indicated.
    :param CashFlow_DataFrame: DataFrame containing the Cash Flow [€]
    :param type_: 'nominal' or 'discounted'
    :return: Net Present Cost [€]
    '''
    if type_ == 'nominal':
        row = 'Cash Flow nominal'
    else:  # type_ == 'discounted'
        row = 'Cash Flow discounted'
    NetPresentCost = sum(CashFlow_DataFrame.loc[row])
    return NetPresentCost


def calc_TotalAnnualizedCost(NetPresentCost, i, L_prj):
    '''
    Calculates the Total Annualized Cost as the annualized value of the net present cost.
    Total Annualized Cost = i * ((1+i)**L_prj) / ((1+i)**L_prj - 1) * NetPresentCost
    :param NetPresentCost: Net Present Cost (nominal or discounted) [€]
    :param i: discount rate [pu]
    :param L_prj: project lifetime [years]
    :return: Total Annualized Cost [€/year]
    '''
    factor = i * ((1 + i) ** L_prj) / ((1 + i) ** L_prj - 1)
    TotalAnnualizedCost = factor * NetPresentCost
    return TotalAnnualizedCost


def calc_operating_cost(allResults, AllInputs, l_Grid, type_):
    '''
    Calculates the operating cost from the optimization results, and according to the assets to consider
    :param allResults: data class which contains all results of the optimization
    :param AllInputs: data class which contains all inputs
    :param type_: 'assets' , 'grid' or 'total'
    :return: operating cost [€/año]
    '''
    l_PV = AllInputs.PV.id_list
    l_BESS = AllInputs.BESS.id_list
    operating_cost_assets = sum(allResults.PV.C_opex[i_PV] for i_PV in l_PV) \
                            + sum(allResults.BESS.C_opex[i_BESS] for i_BESS in l_BESS)
    operating_cost_grid = sum(allResults.Grid.C_buy[i_Grid] - allResults.Grid.R_sell[i_Grid] \
                          + allResults.Grid.C_power[i_Grid] + allResults.Grid.C_penalisation[i_Grid] \
                          + allResults.Grid.C_emission[i_Grid] for i_Grid in l_Grid)
    operating_cost_total = allResults.Economic_indicators.total_annual_costs  # = operating_cost_assets + operating_cost_grid + allResults.Economic_indicators.total_flexibility_cost + allResults.noSupply_C + operating_cost_gas + operating_cost_otherH2
    if type_ == 'assets':  # PV + BESS + GS + Electrolyser + Burner + H2tank + Compressor + FuelCell + H2bottle
        return operating_cost_assets
    elif type_ == 'grid':  # of the grid:
        return operating_cost_grid
    else:  # type_ == 'total'
        return operating_cost_total


def calc_total_E_served(allResults, AllInputs, l_t, l_Grid, l_bus, inc_t):
    '''
    Calculates the total electric/thermal energy supplied annualy, considering the loads and the energy sold to the grid
    :param allResults: data class which contains all results of the optimization
    :param l_t: ``list`` containing all time-steps
    :param inc_t: time-step magnitude [h]
    :return: total electric energy supplied annualy [kWh]
    '''
    # total electrical load served: loads + ventas - load not supplied
    total_electrical_served = sum(allResults.D[t]*inc_t for t in l_t) \
                              + sum(allResults.Grid.P_sell[i_Grid, t] * inc_t for t in l_t for i_Grid in l_Grid) \
                              - sum(allResults.noSupply_P[i_bus, t] * inc_t for t in l_t for i_bus in l_bus)
    total_served = total_electrical_served
    return total_served


def calc_self_consumption(allResults, l_t, inc_t, l_PV, l_bus):
    '''
    Calculates the self-consumption:  min(PV annual generation, annual load) / PV annual generation
    :param allResults: data class which contains all results of the optimization
    :param l_t: ``list`` containing all time-steps
    :param inc_t: time-step magnitude [h]
    :param l_PV: ``list`` containing all PV subsystems id
    :return: self-consumption [pu]
    '''
    if sum(allResults.PV.P[i_PV, t] * inc_t for i_PV in l_PV for t in l_t) == 0:
        self_consumption = 0
    else:
        self_consumption = min(sum(allResults.PV.P[i_PV, t] * inc_t for i_PV in l_PV for t in l_t), sum((allResults.D[t]-sum(allResults.noSupply_P[i_bus, t] for i_bus in l_bus)) * inc_t for t in l_t)) \
                           / sum(allResults.PV.P[i_PV, t] * inc_t for i_PV in l_PV for t in l_t)
    return self_consumption


def calc_self_production(allResults, l_t, inc_t, l_PV, l_bus):
    '''
    Calculates the self-production: min(PV annual generation, annual load) / annual load
    :param allResults: data class which contains all results of the optimization
    :param l_t: ``list`` containing all time-steps
    :param inc_t: time-step magnitude [h]
    :param l_PV: ``list`` containing all PV subsystems id
    :return: self-production [pu]
    '''
    self_production = min(sum(allResults.PV.P[i_PV, t] * inc_t for i_PV in l_PV for t in l_t), sum((allResults.D[t]-sum(allResults.noSupply_P[i_bus, t] for i_bus in l_bus)) * inc_t for t in l_t)) \
                      / sum(allResults.D[t]*inc_t for t in l_t)
    return self_production


def calc_renewable_fraction(allResults, AllInputs, inc_t, total_E_served, l_t, l_PV, l_Grid):
    '''
    Calculates the electrical renewable fraction (not considering the grid): PV annual generation / total electricity supplied annualy
    :param allResults: data class which contains all results of the optimization
    :param total_E_served: total electric energy supplied annualy [kWh]
    :param l_t: ``list`` containing all time-steps
    :param l_PV: ``list`` containing all PV subsystems id
    :return: renewable fraction [pu]
    '''
    grid_renewables = {t: AllInputs.Grid.renewable_factor[i_Grid, t]*(allResults.Grid.P_buy[i_Grid, t] + allResults.Grid.P_excess[i_Grid, t]) for t in l_t for i_Grid in l_Grid}
    renewable_fraction = (sum(allResults.PV.P[i_PV, t]*inc_t for i_PV in l_PV for t in l_t)
                          + sum(grid_renewables[t]*inc_t for t in l_t)) / total_E_served
    return renewable_fraction

def calc_ROI(CashFlow_DataFrame, type_, L_prj):
    '''
    Calculates the Return On Investment from the Cash Flow, nominal or discounted type has to be indicated.
    :param CashFlow_DataFrame: DataFrame containing the Cash Flow [€]
    :param type_: 'nominal' or 'discounted'
    :param L_prj: project lifetime [years]
    :return: ROI [%]
    '''
    # ROI = sum(CashFlow_ref[t] - CashFlow[t] for t in L_prj) / (L_prj * (CAPEX - incentives)
    if type_ == 'nominal':
        row = 'Cash Flow nominal'
    else:  # tipo == 'discounted'
        row = 'Cash Flow discounted'
    if CashFlow_DataFrame.loc[row, 0] == 0:
        return 'inf'
    else:
        ROI = - sum(CashFlow_DataFrame.loc[row, year] for year in list(range(L_prj + 1))) / (L_prj * CashFlow_DataFrame.loc[row, 0])
        return ROI * 100


def calc_payback(CashFlow_DataFrame, type_, L_prj):
    '''
    Obtains the payback from the Cash Flow, nominal or discounted type has to be indicated.
    Payback = when the cumulative cash flow goes from <0 to >0 (in our case is the oposite as costs are >0)

    --> This formula is applied in the post-process and should be compared with the value obtained in the optimization
    :param CashFlow_DataFrame: DataFrame containing the Cash Flow [€]
    :param type_: 'nominal' or 'discounted'
    :param L_prj: project lifetime [years]
    :return: payback [years]
    '''
    if type_ == 'nominal':
        fila = 'Cumulative Cash Flow nominal'
    else:  # tipo == 'discounted'
        fila = 'Cumulative Cash Flow discounted'
    for year in range(1, L_prj + 1):
        if CashFlow_DataFrame.loc[fila, year] <= 0 and CashFlow_DataFrame.loc[fila, year - 1] > 0:
            # it is supposed that revenues are evently distributed during the year:
            # therefore the straight line that connects the points (year-1, CashFlow_DataFrame.loc[fila,year-1])
            # and (year, CashFlow_DataFrame.loc[fila,year])
            # passes through the point (payback, 0)
            payback = (year - 1) + (CashFlow_DataFrame.loc[fila, year - 1] - 0) * (year - (year - 1)) \
                      / (CashFlow_DataFrame.loc[fila, year - 1] - CashFlow_DataFrame.loc[fila, year])
            return payback
    return 'payback > L_prj'


def LCOE_calc(TotalAnnualizedCost, total_E_served):
    '''
    Calculates the Levelized Cost Of Energy: TotalAnnualizedCost / total_E_served
    :param TotalAnnualizedCost: Total Annualized Cost [€/year]
    :param total_E_served: total electric energy supplied annualy [kWh]
    :return: LCOE [€/kWh]
    '''
    LCOE = TotalAnnualizedCost / total_E_served
    # It's not correct to calculate it as:
    # LCOE = NetPresentCost_nominal / L_prj / total_E_served  # = ((C_capex_total - C_incentivos_total + C_replacement_total) / L_prj + operating_cost_total) / total_E_served = (allResults.total_investment / L_prj + allResults.total_annual_costs) / total_E_served
    # LCOE = NetPresentCost_discounted / L_prj / total_E_served
    return LCOE


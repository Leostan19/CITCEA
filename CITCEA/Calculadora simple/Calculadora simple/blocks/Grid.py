import pyomo.environ as pyo
import math

def Grid_block(model, l_t, l_N, l_month, l_PV, AllInputs):
    '''
    Grid connection.

    It considers a single connection point to the grid.
    This model includes performance characteristics and costs calculation.
    The connection is modelled according to the Spanish tariff system.
    It is characterized by a hired power and ability to buy power from the grid,
    in some cases it can also sell power to the grid.
    Regarding the costs, apart from the energy exchange,
    there is the hired power cost, and some penalisation may also appear.

    This is a MILP model.
    Constraint_Grid_inj1 was quadratic and with an integer (binary) variable to identify if we can inject power according to the PV installed capacity,
    this constraint is now linealized.
    Integer variable (binary) to decide if injecting.

    :param model: pyomo ``Block()`` or ``Model()`` in which the GS system is added
    :param l_N: ``list`` containing all tariff periods id
    :param l_month: ``list`` containing all month id
    :param l_PV: ``list`` containing all PV subsystems id
    :param l_t: ``list`` containing all time-steps
    :param AllInputs: data class

    Pyomo parameters:
        - ...
    Pyomo variables:
        - ...
    Pyomo constraints:
        - ... ESCRIBIR VARIABLES Y PARAMETROS EN FORMATO MATEMATICO, Y AQUÍ PONER LA DESCRIPCIÓN DE LAS RESTRICCIONES Y SUS ECUACIONES

    Block inputs: PV_G, PV_G0 (param)

    Block outputs: Grid_P_buy, Grid_P_sell, Grid_P_excess, Grid_C_buy, Grid_R_sell, Grid_C_power, Grid_C_penalisation, Grid_C_emission
    '''


    ##### Model Sets #####

    # model.t = pyo.Set(initialize=l_t)  # time steps to consider in the optimization (time horizon=365 days)
    # model.N = pyo.Set(initialize=AllInputs.Grid.l_N)  # tariff periods
    # model.mes = pyo.Set(initialize=l_month)  # month of the year
    # model.i_Grid = pyo.Set(initialize=l_Grid)  # models/elements of Grid
    l_Grid = AllInputs.Grid.id_list


    ##### Model Parameters #####

    if AllInputs.Grid.conected1_islanded0 == 1:  # if grid connected
        model.Grid_c_buy = pyo.Param(model.i_Grid, model.t, initialize=AllInputs.Grid.Cost_P_buy_grid,
                                     within=pyo.NonNegativeReals)  # price of the energy bought to the grid at each time-step [€/kWh]
        model.Grid_c_sell = pyo.Param(model.i_Grid, model.t, initialize=AllInputs.Grid.Cost_P_sell_grid,
                                      within=pyo.NonNegativeReals)  # price of the energy sold to the grid at each time-step [€/kWh]
        model.Grid_K_inj = pyo.Param(model.i_Grid, initialize=AllInputs.Grid.injection,
                                     within=pyo.NonNegativeReals)  # binary that indicates the client willingness to inject power to the grid. 1: yes under some conditions, 0: never
        model.Grid_P_lim_inj = pyo.Param(model.i_Grid, initialize=AllInputs.Grid.Plim_injection,
                                         within=pyo.NonNegativeReals)  # maximum PV power installed to enable grid injection [kW]
        model.Grid_K_P = pyo.Param(model.i_Grid, model.N, model.t, within=pyo.NonNegativeReals,
                                   initialize=AllInputs.Grid.K_P)  # binary that indicates if a hired power tariff period is applied at a time-step. 1: yes, 0: no
        model.Grid_cost_P = pyo.Param(model.i_Grid, model.N, initialize=AllInputs.Grid.Cost_power,
                                      within=pyo.NonNegativeReals)  # price of the hired power term [€/(kW*year)]
        model.Grid_fix_P_hired_N = pyo.Param(model.i_Grid, model.N, initialize=AllInputs.Grid.fix_Hired_power,
                                                  within=pyo.NonNegativeReals)  # fixed hired power [kW]
        model.Grid_cost_Pexcess45 = pyo.Param(model.i_Grid, initialize=AllInputs.Grid.cost_Pexcess45,
                                              within=pyo.NonNegativeReals)  # price of the excess power term with meters 4 and 5 [€/kW]
        model.Grid_cost_Pexcess123 = pyo.Param(model.i_Grid, initialize=AllInputs.Grid.cost_Pexcess123,
                                               within=pyo.NonNegativeReals)  # price of the excess power term with meters 1, 2 and 3 [€/kW]
        model.Grid_coefKp = pyo.Param(model.i_Grid, model.N, initialize=AllInputs.Grid.CoefK_cost_Pexcess,
                                      within=pyo.NonNegativeReals)  # coefficient of the excess power term with meters 1, 2 and 3
        model.coef_month = pyo.Param(model.month, model.t, within=pyo.NonNegativeReals,
                                     initialize=AllInputs.System.dict_K_month)  # binary that indicates the month of each time-step
        model.days_month = pyo.Param(model.month, within=pyo.NonNegativeReals,
                                     initialize=AllInputs.System.dict_days_month)  # number of days in each month
        model.Grid_hard_Plim = pyo.Param(model.i_Grid, initialize=AllInputs.Grid.hard_Plim, within=pyo.Any)  # Optional, grid hard power limit (both buy and sell) [kW]
        model.Grid_emission_factor = pyo.Param(model.i_Grid, model.t, initialize=AllInputs.Grid.emissions,
                                     within=pyo.NonNegativeReals)  # emission factor of the energy from the grid at each time-step [kgCO2/kWh]
    model.Grid_pos_bus = pyo.Param(model.i_Grid, model.i_bus, initialize=AllInputs.Grid.pos_bus, within=pyo.Binary)  # binary that indicates the bus to which the grid is connected --> [id_load,id_bus]=1


    ##### Model Variables #####

    model.Grid_P_excess = pyo.Var(model.i_Grid, model.t, within=pyo.NonNegativeReals)  # power excess from the hired one, or power not supplyed in islanded mode [kW]
    if AllInputs.Grid.conected1_islanded0 == 1:  # if grid connected
        model.Grid_P_buy = pyo.Var(model.i_Grid, model.t, within=pyo.NonNegativeReals)  # power bought to the grid [kW]
        model.Grid_P_sell = pyo.Var(model.i_Grid, model.t, within=pyo.NonNegativeReals)  # power sold to the grid [kW]
        model.Grid_P_hired_N = pyo.Var(model.i_Grid, model.N, within=pyo.NonNegativeReals)  # hired power at each tariff period [kW]
        model.Grid_P_hired_t = pyo.Var(model.i_Grid, model.t, within=pyo.NonNegativeReals)  # hired power at each time-step [kW]
        model.Grid_lambda_inj = pyo.Var(model.i_Grid, within=pyo.Binary)  # binary that indicates if injection to the grid is enabled. 1: yes, 0: no
        model.Grid_aux_inj = pyo.Var(model.i_Grid, within=pyo.NonNegativeReals)  # auxiliary variable = sum(m.PV_G[i_PV] for i_PV in l_PV) * m.Grid_lambda_inj
        model.Grid_P_excessmax = pyo.Var(model.i_Grid, model.N, model.month,
                                         within=pyo.NonNegativeReals)  # maximum power excess at each tariff period and month [kW]
        #
        model.Grid_C_buy = pyo.Var(model.i_Grid, within=pyo.NonNegativeReals)  # annual cost of energy bought to the grid [€]
        model.Grid_R_sell = pyo.Var(model.i_Grid, within=pyo.NonNegativeReals)  # annual revenues of energy sold to the grid [€]
        model.Grid_C_power = pyo.Var(model.i_Grid, within=pyo.NonNegativeReals)  # annual cost of the hired power term [€]
        model.Grid_C_penalisation = pyo.Var(model.i_Grid, within=pyo.NonNegativeReals)  # annual cost of the penalisation by the power excess [€]
        model.Grid_C_emission = pyo.Var(model.i_Grid, within=pyo.NonNegativeReals)  # annual cost of the grid emissions [€]
    else:  # if islanded mode
        model.Grid_P_buy = pyo.Param(model.i_Grid, model.t, within=pyo.NonNegativeReals, initialize={(0,t): 0 for t in l_t})
        model.Grid_P_sell = pyo.Param(model.i_Grid, model.t, within=pyo.NonNegativeReals, initialize={(0,t): 0 for t in l_t})
        model.Grid_P_hired_N = pyo.Param(model.i_Grid, model.N, within=pyo.NonNegativeReals, initialize={(0,N): 0 for N in AllInputs.Grid.l_N})
        model.Grid_P_hired_t = pyo.Param(model.i_Grid, model.t, within=pyo.NonNegativeReals, initialize={(0,t): 0 for t in l_t})
        model.Grid_lambda_inj = pyo.Param(model.i_Grid, within=pyo.Binary, initialize={0:0})
        model.Grid_aux_inj = pyo.Param(model.i_Grid, within=pyo.NonNegativeReals, initialize={0:0})
        #
        model.Grid_C_buy = pyo.Param(model.i_Grid, within=pyo.NonNegativeReals, initialize={0:0})
        model.Grid_R_sell = pyo.Param(model.i_Grid, within=pyo.NonNegativeReals, initialize={0:0})
        model.Grid_C_power = pyo.Param(model.i_Grid, within=pyo.NonNegativeReals, initialize={0:0})
        model.Grid_C_penalisation = pyo.Param(model.i_Grid, within=pyo.NonNegativeReals, initialize={0:0})
        model.Grid_C_emission = pyo.Param(model.i_Grid, within=pyo.NonNegativeReals, initialize={0:0})


    ##### Model Constraints if grid-connected #####

    def Constraint_Grid_P_hired_t(m, i_Grid, t):
        '''
        Constraint: hired power at each time-step according to the tariff periods
        :param m: Pyomo optimization model
        :param t: time-step index
        :return: expression of the constraint for every t
        '''
        return m.Grid_P_hired_t[i_Grid, t] == sum(m.Grid_P_hired_N[i_Grid, N] * m.Grid_K_P[i_Grid, N, t] for N in AllInputs.Grid.l_N)

    def Constraint_Grid_P_buy_max(m, i_Grid, t):
        '''
        Constraint: power bought from the grid has to be lower or equal to the hired power.
        If more power has to be bought from the grid, it is assigned to another variable and some penalizations will be applied
        :param m: Pyomo optimization model
        :param t: time-step index
        :return: expression of the constraint for every t
        '''
        return m.Grid_P_buy[i_Grid, t] <= m.Grid_P_hired_t[i_Grid, t]

    def Constraint_Grid_inject_willingness(m, i_Grid):
        '''
        Constraint: injection to the grid can be limited by the client willingness
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        # return m.Grid_lambda_inj <= m.Grid_K_inj
        if m.Grid_K_inj[i_Grid] == 0:
            return m.Grid_lambda_inj[i_Grid] == 0
        else:
            return pyo.Constraint.Skip

    # def Constraint_Grid_inj1(m):
    #     '''
    #     Constraint: injection to the grid can happen if the total PV power installed (considering both new and existent)
    #     is lower or equal to a certain amount. First expression to define injection capability
    #     :param m: Pyomo optimization model
    #     :return: expression of the constraint
    #     '''
    #     if m.Grid_K_inj == 1:
    #         if not l_PV:
    #             return m.Grid_lambda_inj == 0
    #         else:
    #             return sum(m.PV_G[i_PV] + m.PV_G0[i_PV] for i_PV in l_PV) * m.Grid_lambda_inj <= m.Grid_P_lim_inj
    #     else:
    #         return pyo.Constraint.Skip
    def Constraint_Grid_inj1aux(m, i_Grid):
        '''
        Constraint: injection to the grid can happen if the total PV power installed (considering both new and existent)
        is lower or equal to a certain amount. First expression to define injection capability. If no PV, then no injection.
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        if m.Grid_K_inj[i_Grid] == 1:
            if not l_PV:
                return m.Grid_lambda_inj[i_Grid] == 0
            else:
                return m.Grid_aux_inj[i_Grid] + sum(m.PV_G0[i_PV] for i_PV in l_PV) * m.Grid_lambda_inj[i_Grid] <= m.Grid_P_lim_inj[i_Grid]
        else:
            return pyo.Constraint.Skip
    def Constraint_Grid_aux_inj1(m, i_Grid):
        if not l_PV:
            return m.Grid_aux_inj[i_Grid] == 0
        else:
            return m.Grid_aux_inj[i_Grid] <= m.Grid_lambda_inj[i_Grid] * (10 ** 6)
    def Constraint_Grid_aux_inj2(m, i_Grid):
        if not l_PV:
            return m.Grid_aux_inj[i_Grid] == 0
        else:
            return m.Grid_aux_inj[i_Grid] <= sum(m.PV_G[i_PV] for i_PV in l_PV)
    def Constraint_Grid_aux_inj3(m, i_Grid):
        if not l_PV:
            return m.Grid_aux_inj[i_Grid] == 0
        else:
            return m.Grid_aux_inj[i_Grid] >= sum(m.PV_G[i_PV] for i_PV in l_PV) - (10 ** 6) * (1-m.Grid_lambda_inj[i_Grid])
    def Constraint_Grid_aux_inj4(m, i_Grid):
        if not l_PV:
            return m.Grid_aux_inj[i_Grid] == 0
        else:
            return m.Grid_aux_inj[i_Grid] >= 0

    def Constraint_Grid_inj2(m, i_Grid):
        '''
        Constraint: injection to the grid can happen if the total PV power installed (considering both new and existent)
        is lower or equal to a certain amount. Second expression to define injection capability. If no PV, then no injection.
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        if m.Grid_K_inj[i_Grid] == 1:
            if not l_PV:
                return m.Grid_lambda_inj[i_Grid] == 0
            else:
                return sum(m.PV_G[i_PV] + m.PV_G0[i_PV] for i_PV in l_PV) >= m.Grid_P_lim_inj[i_Grid] * (1 - m.Grid_lambda_inj[i_Grid])
        else:
            return pyo.Constraint.Skip

    def Constraint_Grid_P_sell(m, i_Grid, t):
        '''
        Constraint: power can be sold to the grid only if injection is enabled.
        Note: due to solver tolerance, the power sold to the grid has to be lower than 1 GW.
        :param m: Pyomo optimization model
        :param t: time-step index
        :return: expression of the constraint for every t
        '''
        return m.Grid_P_sell[i_Grid, t] <= m.Grid_lambda_inj[i_Grid] * (10 ** 6)

    def Constraint_Grid_P12(m, i_Grid):
        '''
        Constraint: if Spanish tariff different from 2.0TD is applied,
        the hired power at period 1 has to be lower or equal than at period 2
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        if AllInputs.Grid.Tariff[i_Grid] != '2.0TD':  # if Tariff = 3.0TD or 6.1TD or 6.2TD or 6.3TD or 6.4TDUP
            # P1 <= P2 <= P3 <= P4 <= P5 <= P6
            return m.Grid_P_hired_N[i_Grid, 0] <= m.Grid_P_hired_N[i_Grid, 1]
        else:
            return pyo.Constraint.Skip

    def Constraint_Grid_P23(m, i_Grid):
        '''
        Constraint: if Spanish tariff different from 2.0TD is applied,
        the hired power at period 2 has to be lower or equal than at period 3
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        if AllInputs.Grid.Tariff[i_Grid] != '2.0TD':  # if Tariff = 3.0TD or 6.1TD or 6.2TD or 6.3TD or 6.4TDUP
            # P1 <= P2 <= P3 <= P4 <= P5 <= P6
            return m.Grid_P_hired_N[i_Grid, 1] <= m.Grid_P_hired_N[i_Grid, 2]
        else:
            return pyo.Constraint.Skip

    def Constraint_Grid_P34(m, i_Grid):
        '''
        Constraint: if Spanish tariff different from 2.0TD is applied,
        the hired power at period 3 has to be lower or equal than at period 4
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        if AllInputs.Grid.Tariff[i_Grid] != '2.0TD':  # if Tariff = 3.0TD or 6.1TD or 6.2TD or 6.3TD or 6.4TDUP
            # P1 <= P2 <= P3 <= P4 <= P5 <= P6
            return m.Grid_P_hired_N[i_Grid, 2] <= m.Grid_P_hired_N[i_Grid, 3]
        else:
            return pyo.Constraint.Skip

    def Constraint_Grid_P45(m, i_Grid):
        '''
        Constraint: if Spanish tariff different from 2.0TD is applied,
        the hired power at period 4 has to be lower or equal than at period 5
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        if AllInputs.Grid.Tariff[i_Grid] != '2.0TD':  # if Tariff = 3.0TD or 6.1TD or 6.2TD or 6.3TD or 6.4TDUP
            # P1 <= P2 <= P3 <= P4 <= P5 <= P6
            return m.Grid_P_hired_N[i_Grid, 3] <= m.Grid_P_hired_N[i_Grid, 4]
        else:
            return pyo.Constraint.Skip

    def Constraint_Grid_P56(m, i_Grid):
        '''
        Constraint: if Spanish tariff different from 2.0TD is applied,
        the hired power at period 5 has to be lower or equal than at period 6
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        if AllInputs.Grid.Tariff[i_Grid] != '2.0TD':  # if Tariff = 3.0TD or 6.1TD or 6.2TD or 6.3TD or 6.4TDUP
            # P1 <= P2 <= P3 <= P4 <= P5 <= P6
            return m.Grid_P_hired_N[i_Grid, 4] <= m.Grid_P_hired_N[i_Grid, 5]
        else:
            return pyo.Constraint.Skip

    def Constraint_Grid_maximeter(m, i_Grid, N, t, month):
        '''
        Constraint: to obtain the maximum power excess (bought) at each month and tariff period
        :param m: Pyomo optimization model
        :param N: tariff period index
        :param m: Pyomo optimization model
        :param month: month index
        :return: expression of the constraint for every t, N and month
        '''
        return m.Grid_P_excessmax[i_Grid, N, month] >= m.coef_month[month, t] * m.Grid_K_P[i_Grid, N, t] * m.Grid_P_excess[i_Grid, t]

    def Constraint_Grid_no_excess(m, i_Grid, t):
        """
        Constraint: in Tariff 2.0TD, power excess must be equal to 0.
        :param m: Pyomo optimization model
        :param t: time-step index
        :return: expression of the constraint for every t
        """
        if AllInputs.Grid.Tariff[i_Grid] != '2.0TD':  # if Tariff = 2.0TD, there must be no penalizations, if the customer exceeds hired power it is islanded
            return m.Grid_P_excess[i_Grid, t] == 0
        else:
            return pyo.Constraint.Skip

    def Constraint_Grid_hard_Plim_buy(m, i_Grid, t):
        """
        Constraint: if there is a hard power limit, power bought must not exceed it
        :param m: Pyomo optimization model
        :param t: time-step index
        :return: expression of the constraint for every t
        """
        if not math.isnan(AllInputs.Grid.hard_Plim[i_Grid]):
            return m.Grid_P_buy[i_Grid, t] + m.Grid_P_excess[i_Grid, t] <= m.Grid_hard_Plim[i_Grid]
        else:
            return pyo.Constraint.Skip

    def Constraint_Grid_hard_Plim_sell(m, i_Grid, t):
        """
        Constraint: if there is a hard power limit, power sold must not exceed it
        :param m: Pyomo optimization model
        :param t: time-step index
        :return: expression of the constraint for every t
        """
        if not math.isnan(AllInputs.Grid.hard_Plim[i_Grid]):
            return m.Grid_P_sell[i_Grid, t] <= m.Grid_hard_Plim[i_Grid]
        else:
            return pyo.Constraint.Skip

    def Constraint_Grid_fix_P_hired_N(m, i_Grid, N):
        """
        Constraint: to fix the hired power, if desired
        :param m: Pyomo optimization model
        :param N: tariff period
        :return: expression of the constraint for every N
        """
        if AllInputs.Grid.fix[i_Grid] == 1:
            return m.Grid_P_hired_N[i_Grid, N] == m.Grid_fix_P_hired_N[i_Grid, N]
        else:
            return pyo.Constraint.Skip

    if AllInputs.Grid.conected1_islanded0 == 1:
        model.Constr_Grid_P_hired_t = pyo.Constraint(model.i_Grid, model.t, rule=Constraint_Grid_P_hired_t)
        model.Constr_Grid_P_buy_max = pyo.Constraint(model.i_Grid, model.t, rule=Constraint_Grid_P_buy_max)
        model.Constr_Grid_inject_willingness = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_inject_willingness)
        # model.Constr_Grid_inj1 = pyo.Constraint(rule=Constraint_inj1)
        model.Constr_Grid_inj1aux = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_inj1aux)
        model.Constr_Grid_aux_inj1 = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_aux_inj1)
        model.Constr_Grid_aux_inj2 = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_aux_inj2)
        model.Constr_Grid_aux_inj3 = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_aux_inj3)
        model.Constr_Grid_aux_inj4 = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_aux_inj4)
        model.Constr_Grid_inj2 = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_inj2)
        model.Constr_Grid_P_sell = pyo.Constraint(model.i_Grid, model.t, rule=Constraint_Grid_P_sell)
        model.Constr_Grid_P12 = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_P12)
        model.Constr_Grid_P23 = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_P23)
        model.Constr_Grid_P34 = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_P34)
        model.Constr_Grid_P45 = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_P45)
        model.Constr_Grid_P56 = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_P56)
        model.Constr_Grid_no_excess = pyo.Constraint(model.i_Grid, model.t, rule=Constraint_Grid_no_excess)
        model.Constr_Grid_maximeter = pyo.Constraint(model.i_Grid, model.N, model.t, model.month, rule=Constraint_Grid_maximeter)

        model.Constr_Grid_hard_Plim_buy = pyo.Constraint(model.i_Grid, model.t, rule=Constraint_Grid_hard_Plim_buy)
        model.Constr_Grid_hard_Plim_sell = pyo.Constraint(model.i_Grid, model.t, rule=Constraint_Grid_hard_Plim_sell)

        model.Constr_Grid_fix_P_hired_N = pyo.Constraint(model.i_Grid, model.N, rule=Constraint_Grid_fix_P_hired_N)

    def Constraint_Grid_C_buy(m, i_Grid):
        '''
        Constraint: annual cost of buying energy is calculated multiplying the hourly prices and the sum of bought and exceed powers
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        return m.Grid_C_buy[i_Grid] == sum(m.Grid_c_buy[i_Grid, t] * (m.Grid_P_buy[i_Grid, t] + m.Grid_P_excess[i_Grid, t]) * m.inc_t for t in l_t)

    def Constraint_Grid_R_sell(m, i_Grid):
        '''
        Constraint: annual revenue from selling energy is calculated multiplying the hourly prices and the power sold
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        return m.Grid_R_sell[i_Grid] == sum(m.Grid_c_sell[i_Grid, t] * m.Grid_P_sell[i_Grid, t] * m.inc_t for t in l_t)

    def Constraint_Grid_C_power(m, i_Grid):
        '''
        Constraint: annual cost of the power term is calculated multiplying the hired power and its cost at each tariff period
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        return m.Grid_C_power[i_Grid] == sum(m.Grid_cost_P[i_Grid, N] * m.Grid_P_hired_N[i_Grid, N] for N in AllInputs.Grid.l_N)

    def Constraint_Grid_C_penalisation(m, i_Grid):
        '''
        Constraint: annual cost due to power excess penalizations is calculated based on BOE ...
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        if AllInputs.Grid.meter_type[i_Grid] == 4 or AllInputs.Grid.meter_type[i_Grid] == 5:
            return m.Grid_C_penalisation[i_Grid] == m.Grid_cost_Pexcess45[i_Grid] * 2 * sum(
                sum(m.Grid_P_excessmax[i_Grid, N, mes] * m.days_month[mes] for mes in l_month) for N in
                AllInputs.Grid.l_N)  # coste anual de la penalización por exceso de potencia, para meters tipo 4 y 5
        else:  # AllInputs.Grid.meter_type==1,2,3
            return m.Grid_C_penalisation[i_Grid] == m.Grid_cost_Pexcess123[i_Grid] * sum(
                m.Grid_coefKp[i_Grid, N] * ((m.inc_t * 4 / 3 + 2 / 3) * sum(m.Grid_K_P[i_Grid, N, t] * m.Grid_P_excess[i_Grid, t] for t in l_t)) for N
                in AllInputs.Grid.l_N)  # coste anual de la penalizacion por exceso de potencia, para meters tipo 1, 2 y 3

    def Constraint_Grid_C_emission(m, i_Grid):
        '''
        Constraint: annual cost due to CO2 emissions of the energy bought from the grid
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        return m.Grid_C_emission[i_Grid] == m.c_emission * sum(m.Grid_emission_factor[i_Grid, t] * (m.Grid_P_buy[i_Grid, t] + m.Grid_P_excess[i_Grid, t]) * m.inc_t for t in l_t)

    if AllInputs.Grid.conected1_islanded0 == 1:  # si hay conexion a la red
        model.Constr_Grid_C_buy = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_C_buy)
        model.Constr_Grid_R_sell = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_R_sell)
        model.Constr_Grid_C_power = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_C_power)
        model.Constr_Grid_C_penalisation = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_C_penalisation)
        model.Constr_Grid_C_emission = pyo.Constraint(model.i_Grid, rule=Constraint_Grid_C_emission)


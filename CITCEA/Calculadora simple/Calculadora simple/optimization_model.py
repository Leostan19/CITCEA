import pyomo.environ as pyo
import math


def optimization(AllInputs):
    '''
    This function creates the optimization model
    :param AllInputs: data class which contains all inputs
    :return: pyomo instance with the model
    '''

    l_t = AllInputs.System.l_t
    l_month = AllInputs.System.l_month
    l_PV = AllInputs.PV.id_list
    l_BESS = AllInputs.BESS.id_list
    l_Grid = AllInputs.Grid.id_list
    l_Mev = AllInputs.EV.smart.l_Mev
    l_bus = AllInputs.Network.Buses.id_list

    # model initialization
    model = pyo.AbstractModel()


    ##### Model Sets #####
    model.t = pyo.Set(initialize=l_t)  # time steps to consider in the optimization (time horizon=365 days)
    model.N = pyo.Set(initialize=AllInputs.Grid.l_N)  # tariff periods
    model.month = pyo.Set(initialize=l_month)  # month of the year
    #
    model.Mev = pyo.Set(initialize=l_Mev)  # EV with smart charging
    #
    model.i_PV = pyo.Set(initialize=l_PV)  # models/elements of PV
    model.i_BESS = pyo.Set(initialize=l_BESS)  # models/elements of BESS
    model.i_Grid = pyo.Set(initialize=l_Grid)  #models/elements of Grid
    #
    model.i_bus = pyo.Set(initialize=l_bus)


    ##### Model Parameters #####

    model.inc_t = pyo.Param(initialize=AllInputs.System.inc_t, within=pyo.NonNegativeReals)  # time-step magnitude [h]
    model.Dc = pyo.Param(model.i_bus, model.t, within=pyo.NonNegativeReals, initialize=AllInputs.Load.Pd_total_inclEV)  # critical or fixed load [kW] from annual profiles provided
    model.discount_rate = pyo.Param(initialize=AllInputs.System.discount_rate_optimization, within=pyo.Reals)  # [pu]
    model.c_emission = pyo.Param(initialize=AllInputs.System.emissions_cost,
                                 within=pyo.NonNegativeReals)  # price of the general emissions [€/kgCO2]
    model.noSupply_c = pyo.Param(initialize=AllInputs.System.noSupply_cost,
                                 within=pyo.NonNegativeReals)  # price of the energy not supplied in island mode [€/kWh]
    #
    model.min_ren = pyo.Param(initialize=AllInputs.System.min_renew, within=pyo.NonNegativeReals)  # minimum renewable energy contribution annualy [pu=%/100]
    model.L_prj = pyo.Param(initialize=AllInputs.System.lifetime, within=pyo.NonNegativeReals)  # lifetime of the project [years]
    model.max_emissions = pyo.Param(initialize=AllInputs.System.max_emissions)
    model.Grid_renewable_factor = pyo.Param(model.i_Grid, model.t, initialize=AllInputs.Grid.renewable_factor,
                                            within=pyo.NonNegativeReals)  # renewable factor of the energy from the grid ar each time-step [pu]


    ##### Model Blocks #####

    from blocks.PV import PV_block
    PV_block(model, l_PV, l_t, AllInputs)  # Outputs: PV_P

    from blocks.Battery import Battery_block
    Battery_block(model, l_BESS, l_t, AllInputs, False)  # Outputs: BESS_P_char, BESS_P_disch

    from blocks.Grid import Grid_block
    Grid_block(model, l_t, AllInputs.Grid.l_N, l_month, l_PV, AllInputs)  # Outputs: P_buy, P_sell, P_excess

    from blocks.EV import EV_block
    EV_block(model, l_t, l_Mev, l_bus, AllInputs)  # Outputs: P

    from blocks.Network import PowerFlow
    PowerFlow(model, l_t, l_bus, AllInputs)

    from blocks.Economic_indicators import Economic_indicators_block
    Economic_indicators_block(model, l_t, l_PV, l_BESS, l_Mev, AllInputs)


    ##### Model Variables #####

    model.D_bus = pyo.Var(model.i_bus, model.t, within=pyo.NonNegativeReals)  # total load [kW]
    model.D = pyo.Var(model.t, within=pyo.NonNegativeReals)  # total load [kW]
    model.other = pyo.Var(within=pyo.Reals)  # minor term for the objective function
    #
    model.noSupply_P = pyo.Var(model.i_bus, model.t,
                               within=pyo.NonNegativeReals)  # the energy not supplied in island mode [kW]
    model.noSupply_C = pyo.Var(within=pyo.NonNegativeReals)  # cost of the energy not supplied in island mode [€]


    ##### Model Constraints #####

    def Constraint_all_electric_loads_bus(m, i_bus, t):
        '''
        Constraint: total load is the sum of all fixed and flexible loads, including the EV
        :param m: Pyomo optimization model
        :param t: time-step index
        :return: expression of the constraint for every t
        '''
        return m.D_bus[i_bus, t] == m.Dc[i_bus, t] + m.EV_D[i_bus, t] + sum(m.EV_P[Mev, t] for Mev in l_Mev) * m.EV_pos_bus[i_bus]
    model.Constr_all_electric_loads_bus = pyo.Constraint(model.i_bus, model.t, rule=Constraint_all_electric_loads_bus)

    def Constraint_all_electric_loads(m, t):
        '''
        Constraint: total load is the sum of all fixed and flexible loads, including the EV
        :param m: Pyomo optimization model
        :param t: time-step index
        :return: expression of the constraint for every t
        '''
        return m.D[t] == sum(m.D_bus[i_bus, t] for i_bus in l_bus)
    model.Constr_all_electric_loads = pyo.Constraint(model.t, rule=Constraint_all_electric_loads)

    def Constraint_balance_electric_syst_P(m, i_bus, t):
        '''
        Constraint: active power generation and demand have to be balanced
        :param m: Pyomo optimization model
        :param t: time-step index
        :return: expression of the constraint for every t
        '''
        return m.Pinj[i_bus, t] * m.Sb == - m.D_bus[i_bus, t] \
            + sum(m.PV_P[i_PV, t] * m.PV_pos_bus[i_PV, i_bus] for i_PV in l_PV) \
            + sum((m.BESS_P_disch[i_BESS, t] - m.BESS_P_char[i_BESS, t]) * m.BESS_pos_bus[i_BESS, i_bus] for i_BESS in l_BESS) \
            + sum((m.Grid_P_buy[i_Grid, t] - m.Grid_P_sell[i_Grid, t] + m.Grid_P_excess[i_Grid, t]) * m.Grid_pos_bus[i_Grid, i_bus] for i_Grid in AllInputs.Grid.id_list) \
            + m.noSupply_P[i_bus, t]
    model.Constr_balance_electric_syst_P = pyo.Constraint(model.i_bus, model.t, rule=Constraint_balance_electric_syst_P)
    def Constraint_balance_electric_syst_Q(m, i_bus, t):
        '''
        Constraint: active power generation and demand have to be balanced
        :param m: Pyomo optimization model
        :param t: time-step index
        :return: expression of the constraint for every t
        '''
        if m.bus_is_slack[i_bus] == 1:  # the bus is a slack
            return m.Qinj[i_bus, t] * m.Sb == m.Q_buy[t]
        else:
            return m.Qinj[i_bus, t] == 0
    model.Constr_balance_electric_syst_Q = pyo.Constraint(model.i_bus, model.t, rule=Constraint_balance_electric_syst_Q)

    def Constraint_islanded_C(m):
        '''
        Constraint: if some load cannot be supplied in islanded mode, it has a cost.
        This is the annual cost of not supplied load.
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        return m.noSupply_C == m.noSupply_c * sum(m.noSupply_P[i_bus, t] * m.inc_t for t in l_t for i_bus in l_bus)
    model.Constr_islanded_C = pyo.Constraint(rule=Constraint_islanded_C)

    ##### Model Constraint if grid-connected or islanded #####
    def Constraint_islanded_P(m, i_bus, t):
        '''
        Constraint: in islanded systems, it is supposed that all load has to be supplied.
        :param m: Pyomo optimization model
        :param t: time-step index
        :return: expression of the constraint for every t
        '''
        return m.noSupply_P[i_bus, t] == 0
    # if AllInputs.Grid.conected1_islanded0 == 0:  # si aislado
    #     model.Constr_islanded_P = pyo.Constraint(model.i_bus, model.t, rule=Constraint_islanded_P)

    def Constraint_other(m):
        return m.other == sum(m.BESS_P_char[i_BESS, t] + m.BESS_P_disch[i_BESS, t] for i_BESS in l_BESS for t in l_t) * 0.0001
    # model.Constr_other = pyo.Constraint(rule=Constraint_other)

    def Constraint_min_renewables(m):
        '''
        Constraint: the annual renewable generation (PV+renewable fraction of the grid) has to be higher or equal than a specified amount of annual load (electric load + electricity to h2 system)
        Losses in the BESS are not considered
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        if not l_PV:
            return pyo.Constraint.Skip
        else:
            return (sum(m.PV_P[i_PV, t] for i_PV in l_PV for t in l_t)
                    + sum(m.Grid_renewable_factor[i_Grid, t] * (m.Grid_P_buy[i_Grid, t] + m.Grid_P_excess[i_Grid, t]) for t in l_t for i_Grid in l_Grid)) \
                * m.inc_t >= m.min_ren \
                * sum(m.D[t] for t in l_t) * m.inc_t
    model.Constr_min_renewables = pyo.Constraint(rule=Constraint_min_renewables)

    def Constraint_emissions_reduction(m):
        '''
            model.c_emission = pyo.Param(initialize=AllInputs.System.emissions_cost,
                                 within=pyo.NonNegativeReals)  # price of the general emissions [€/kgCO2]
            Grid_C_emission, C_emission_gas_grid [€/year]
            new_emissions [kgCO2/year]
        :param m:
        :return:
        '''
        if m.max_emissions<0:
            return pyo.Constraint.Skip
        else:
            return (sum(m.Grid_C_emission[i_Grid] for i_Grid in l_Grid)) / m.c_emission <= m.max_emissions
    model.Constr_emissions_reduction = pyo.Constraint(rule=Constraint_emissions_reduction)


    ##### Objective function ####

    def func_obj(m):
        '''
        Objective function: minimize costs.
        Considering investment and operation (annual) costs through the project lifetime.
        :param m: Pyomo optimization model
        :return: expression of the objective function
        '''
        # coste total a lo largo del proyecto
        return m.total_investment + sum(m.total_annual_costs / (1 + m.discount_rate) ** y for y in range(1, AllInputs.System.lifetime, 1))#m.total_annual_costs * m.L_prj

    model.goal = pyo.Objective(rule=func_obj, sense=pyo.minimize)



    # To solve:
    instance = model.create_instance()
    #opt = pyo.SolverFactory('gurobi')
    #results=opt.solve(instance) #,tee=True)

    # Access to the results:
    #results.write()

    return instance

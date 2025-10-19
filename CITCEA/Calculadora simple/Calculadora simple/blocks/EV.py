import pyomo.environ as pyo
import math

def EV_block(model, l_t, l_Mev, l_bus, AllInputs):
    '''
    EV system.
    An immediate charging EV is defined as a critical load.
    A smart charging EV is defined very similar to the power-shiftable load.

    A single EV model is considered, and it can not combine immediate and smart charging.
    If immediate charging, the total load profile is considered.
    If smart charging, it can include several loads, where each load is characterized by a single decision variable,
    which is how should be the profile.

    This is a MILP model.
    Integer (binary) variables to indicate it is equal to the baseline.

    :param model: pyomo ``Block()`` or ``Model()`` in which the BESS system is added
    :param l_Mev: ``list`` containing all EV subsystems id
    :param l_t: ``list`` containing all time-steps
    :param AllInputs: data class

    Pyomo parameters:
        - ...
    Pyomo variables:
        - ...
    Pyomo constraints:
        - ... ESCRIBIR VARIABLES Y PARAMETROS EN FORMATO MATEMATICO, Y AQUÍ PONER LA DESCRIPCIÓN DE LAS RESTRICCIONES Y SUS ECUACIONES

    Block inputs: -

    Block outputs: EV_D (param), EV_P, EV_flexibility_cost
    '''

    ##### Model Sets #####

    # model.t = pyo.Set(initialize=l_t)  # time steps to consider in the optimization (time horizon=365 days)
    # model.Mev = pyo.Set(initialize=l_Mev)  # EV with smart charging


    ##### Model Parameters #####

    if AllInputs.EV.hay == 1: # if there is EV
        if AllInputs.EV.immediate0_smart1 == 0:  # immediate charging
            model.EV_D = pyo.Param(model.i_bus, model.t, within=pyo.NonNegativeReals, initialize=AllInputs.Load.Pd_EV_total)#AllInputs.EV.immediate)  # total critical load power profile of the EVs [kW] (profile built based on probability distributions)
        else:  # smart charging ~= power-shiftable load
            model.EV_D = pyo.Param(model.i_bus, model.t, within=pyo.NonNegativeReals, initialize={(i_bus,t): 0 for t in l_t for i_bus in l_bus})  # critical load EV = 0
            model.EV_Pmax = pyo.Param(model.Mev, initialize=AllInputs.EV.smart.Pmax_evMev, within=pyo.NonNegativeReals)  # maximum charging power of the EV [kW]
            model.EV_P_station = pyo.Param(initialize=AllInputs.EV.smart.P_estacion, within=pyo.NonNegativeReals)  # maximum power of the charging station [kW]
            model.EV_E = pyo.Param(model.Mev, initialize=AllInputs.EV.smart.E_evMev, within=pyo.NonNegativeReals)  # total energy charged for the EV [kWh]
            model.EV_t_availability = pyo.Param(model.Mev, model.t, initialize=AllInputs.EV.smart.K_evMev_t, within=pyo.Binary)  # binary that indicates if the EV can charge in a time-step. 1: yes, 0: no
            model.EV_Pbaseline = pyo.Param(model.Mev, model.t, initialize=AllInputs.EV.smart.Pbaseline_evMev_t, within=pyo.NonNegativeReals)  # baseline power profile of the EV [kW]
            model.EV_flexibility_price = pyo.Param(model.Mev, initialize=AllInputs.EV.smart.Cost_evMev, within=pyo.NonNegativeReals)  # price to change the EV profile from the baseline [€]
    else:
        model.EV_D = pyo.Param(model.i_bus, model.t, within=pyo.NonNegativeReals, initialize={(i_bus,t): 0 for t in l_t for i_bus in l_bus})  # critical load EV = 0
    model.EV_pos_bus = pyo.Param(model.i_bus, initialize=AllInputs.EV.pos_bus, within=pyo.Binary)  # binary that indicates the bus to which the load is connected --> [id_load,id_bus]=1


    ##### Model Variables #####

    if AllInputs.EV.hay == 1 and AllInputs.EV.immediate0_smart1 == 1:  # if there is EV and it is with smart charging
        model.EV_P = pyo.Var(model.Mev, model.t, within=pyo.NonNegativeReals)  # EV charging power [kW]
        model.EV_flexibility_cost = pyo.Var(model.Mev, within=pyo.NonNegativeReals)  # cost of EV flexibility [€]
        model.EV_is_baseline = pyo.Var(model.Mev, within=pyo.Binary)  # binary that indicates if the power profile of the EV is equal to the baseline. 1: yes, 0: no
    else:
        model.EV_P = pyo.Param(model.Mev, model.t, within=pyo.NonNegativeReals, initialize={(Mev, t): 0 for t in l_t for Mev in l_Mev})
        model.EV_flexibility_cost = pyo.Param(model.Mev, within=pyo.NonNegativeReals, initialize={Mev: 0 for Mev in l_Mev})


    ##### Model Constraints #####

    def Constraint_Pmax_Mev(m, Mev, t):
        '''
        Constraint: the power profile has to be lower or equal than the maximum charging power of the EV, considering the time availability of the EV
        :param m: Pyomo optimization model
        :param Mev: EV index
        :param t: time-step index
        :return: expression of the constraint for every t and Mev
        '''
        return m.EV_P[Mev, t] <= m.EV_t_availability[Mev, t] * m.EV_Pmax[Mev]

    def Constraint_E_Mev(m, Mev):
        '''
        Constraint: total energy charged by the EV has to be equal to the energy demand of the EV
        :param m: Pyomo optimization model
        :param Mev: EV index
        :return: expression of the constraint for every Mev
        '''
        return sum(m.EV_P[Mev, t] for t in l_t) * m.inc_t == m.EV_E[Mev]

    def Constraint_P_station_EV(m, t):
        '''
        Constraint: the charging power of all EVs has to be lower or equal than the charging station maximum power
        :param m: Pyomo optimization model
        :param t: time-step index
        :return: expression of the constraint for every t
        '''
        return sum(m.EV_P[Mev, t] for Mev in l_Mev) <= m.EV_P_station

    def Constraint_is_baseline_Mev1(m, Mev, t):
        '''
        Constraint: first expression to identify if the load profile is equal or different from the baseline.
        Note: due to solver tolerance, the loads have to be lower than 1 GW.
        :param m: Pyomo optimization model
        :param Mev: EV index
        :param t: time-step index
        :return: expression of the constraint for every t and Mev
        '''
        return -10**6 * (1-m.EV_is_baseline[Mev]) <= m.EV_P[Mev,  t] - m.EV_Pbaseline[Mev, t]

    def Constraint_is_baseline_Mev2(m, Mev, t):
        '''
        Constraint: second expression to identify if the load profile is equal or different from the baseline.
        Note: due to solver tolerance, the loads have to be lower than 1 GW.
        :param m: Pyomo optimization model
        :param Mev: EV index
        :param t: time-step index
        :return: expression of the constraint for every t and Mev
        '''
        return m.EV_P[Mev,  t] - m.EV_Pbaseline[Mev, t] <= 10**6 * (1-m.EV_is_baseline[Mev])

    def Constraint_flexibility_cost_Mev(m, Mev):
        '''
        Constraint: the cost of flexibility is the price given if the load profile is different from the baseline,
        and 0 otherwise
        :param m: Pyomo optimization model
        :param Mev: EV index
        :return: expression of the constraint for every Mev
        '''
        return m.EV_flexibility_cost[Mev] == (1-m.EV_is_baseline[Mev]) * m.EV_flexibility_price[Mev]

    if AllInputs.EV.hay == 1 and AllInputs.EV.immediate0_smart1 == 1:  # if there is EV and it is with smart charging
        model.Constr_Pmax_Mev = pyo.Constraint(model.Mev, model.t, rule=Constraint_Pmax_Mev)
        model.Constr_E_Mev = pyo.Constraint(model.Mev, rule=Constraint_E_Mev)
        model.Constr_P_station_EV = pyo.Constraint(model.t, rule=Constraint_P_station_EV)
        model.Constr_is_baseline_Mev1 = pyo.Constraint(model.Mev, model.t, rule=Constraint_is_baseline_Mev1)
        model.Constr_is_baseline_Mev2 = pyo.Constraint(model.Mev, model.t, rule=Constraint_is_baseline_Mev2)
        model.Constr_flexibility_cost_Mev = pyo.Constraint(model.Mev, rule=Constraint_flexibility_cost_Mev)

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
            #model.EV_Pbaseline = pyo.Param(model.Mev, model.t, initialize=AllInputs.EV.smart.Pbaseline_evMev_t, within=pyo.NonNegativeReals)  # baseline power profile of the EV [kW]
            model.EV_flexibility_price = pyo.Param(model.Mev, initialize=AllInputs.EV.smart.Cost_evMev, within=pyo.NonNegativeReals)  # price to change the EV profile from the baseline [€]
    else:
        model.EV_D = pyo.Param(model.i_bus, model.t, within=pyo.NonNegativeReals, initialize={(i_bus,t): 0 for t in l_t for i_bus in l_bus})  # critical load EV = 0
    model.EV_pos_bus = pyo.Param(model.i_bus, initialize=AllInputs.EV.pos_bus, within=pyo.Binary)  # binary that indicates the bus to which the load is connected --> [id_load,id_bus]=1


    ##### Model Variables #####

    if AllInputs.EV.hay == 1 and AllInputs.EV.immediate0_smart1 == 1:  # smart charging
        # 关键：允许正负，>0 充电，<0 放电（V2G）
        model.EV_P = pyo.Var(model.Mev, model.t, within=pyo.Reals)
        # 新增：EV 的 SoC 变量，单位 kWh
        model.EV_SOC = pyo.Var(model.Mev, model.t, within=pyo.NonNegativeReals)
        #model.EV_flexibility_cost = pyo.Var(model.Mev, within=pyo.NonNegativeReals)
        #model.EV_is_baseline = pyo.Var(model.Mev, within=pyo.Binary)
        model.EV_P_neg = pyo.Var(model.Mev, model.t, within=pyo.NonNegativeReals)
    else:
        model.EV_P = pyo.Var(model.Mev, model.t, within=pyo.Reals)
        model.EV_P_neg = pyo.Var(model.Mev, model.t, within=pyo.NonNegativeReals)
        #model.EV_flexibility_cost = pyo.Var(model.Mev, within=pyo.NonNegativeReals)
    ##### Model Constraints #####

    def Constraint_Pmax_Mev(m, Mev, t):
        # -Pmax <= EV_P <= Pmax，并且只在 t_availability=1 的时候允许有功率
        return pyo.inequality(
            - m.EV_t_availability[Mev, t] * m.EV_Pmax[Mev],
            m.EV_P[Mev, t],
            + m.EV_t_availability[Mev, t] * m.EV_Pmax[Mev]
        )

    def Constraint_SOC_EV(m, Mev, t):
        # l_t 是传进来的时间列表（你函数的参数里就有）
        idx = l_t.index(t)

        if idx == 0:
            # 这里就是你要的：初始 SOC = 0 * 总电量（总电量用 EV_E 这个参数）
            return m.EV_SOC[Mev, t] == 0.25 * m.EV_E[Mev]

        # 前一时刻
        t_prev = l_t[idx - 1]

        # SoC[k] = SoC[k-1] + P[k] * Δt
        return m.EV_SOC[Mev, t] == m.EV_SOC[Mev, t_prev] + m.EV_P[Mev, t] * m.inc_t

    def Constraint_SOC_bounds_EV(m, Mev, t):
        # 0 <= SoC <= 总电量（用 EV_E 做容量）
        return pyo.inequality(
            0,
            m.EV_SOC[Mev, t],
            m.EV_E[Mev]
        )

    def Constraint_E_Mev(m, Mev):
        '''
        Constraint: total energy charged by the EV has to be equal to the energy demand of the EV
        :param m: Pyomo optimization model
        :param Mev: EV index
        :return: expression of the constraint for every Mev
        '''
        return sum(m.EV_P[Mev, t] for t in l_t) * m.inc_t == m.EV_E[Mev]-0.25*m.EV_SOC[Mev, 0]

    def Constraint_P_station_EV(m, t):
        return pyo.inequality(
            - m.EV_P_station,
            sum(m.EV_P[Mev, t] for Mev in l_Mev),
            + m.EV_P_station
        )

    #def Constraint_is_baseline_Mev1(m, Mev, t):
        '''
        Constraint: first expression to identify if the load profile is equal or different from the baseline.
        Note: due to solver tolerance, the loads have to be lower than 1 GW.
        :param m: Pyomo optimization model
        :param Mev: EV index
        :param t: time-step index
        :return: expression of the constraint for every t and Mev
        '''
        return -10**6 * (1-m.EV_is_baseline[Mev]) <= m.EV_P[Mev,  t] - m.EV_Pbaseline[Mev, t]

    #def Constraint_is_baseline_Mev2(m, Mev, t):
        '''
        Constraint: second expression to identify if the load profile is equal or different from the baseline.
        Note: due to solver tolerance, the loads have to be lower than 1 GW.
        :param m: Pyomo optimization model
        :param Mev: EV index
        :param t: time-step index
        :return: expression of the constraint for every t and Mev
        '''
        return m.EV_P[Mev,  t] - m.EV_Pbaseline[Mev, t] <= 10**6 * (1-m.EV_is_baseline[Mev])

    #def Constraint_flexibility_cost_Mev(m, Mev):
        '''
        Constraint: the cost of flexibility is the price given if the load profile is different from the baseline,
        and 0 otherwise
        :param m: Pyomo optimization model
        :param Mev: EV index
        :return: expression of the constraint for every Mev
        '''
        return m.EV_flexibility_cost[Mev] == (1-m.EV_is_baseline[Mev]) * m.EV_flexibility_price[Mev]

    def Constraint_EV_P_neg_1(m, Mev, t):
        # EV_P_neg >= -EV_P
        return m.EV_P_neg[Mev, t] >= -m.EV_P[Mev, t]

    def Constraint_EV_P_neg_2(m, Mev, t):
        # EV_P_neg >= 0  （自动成立，但保留）
        return m.EV_P_neg[Mev, t] >= 0

    if AllInputs.EV.hay == 1 and AllInputs.EV.immediate0_smart1 == 1:  # if there is EV and it is with smart charging
        model.Constr_Pmax_Mev = pyo.Constraint(model.Mev, model.t, rule=Constraint_Pmax_Mev)
        model.Constr_E_Mev = pyo.Constraint(model.Mev, rule=Constraint_E_Mev)
        model.Constr_P_station_EV = pyo.Constraint(model.t, rule=Constraint_P_station_EV)
        #model.Constr_is_baseline_Mev1 = pyo.Constraint(model.Mev, model.t, rule=Constraint_is_baseline_Mev1)
        #model.Constr_is_baseline_Mev2 = pyo.Constraint(model.Mev, model.t, rule=Constraint_is_baseline_Mev2)
        #model.Constr_flexibility_cost_Mev = pyo.Constraint(model.Mev, rule=Constraint_flexibility_cost_Mev)
        model.Constr_SOC_EV = pyo.Constraint(model.Mev, model.t, rule=Constraint_SOC_EV)
        model.Constr_SOC_bounds_EV = pyo.Constraint(model.Mev, model.t, rule=Constraint_SOC_bounds_EV)
        model.constr_EV_P_neg_1 = pyo.Constraint(model.Mev, model.t, rule=Constraint_EV_P_neg_1)
        model.constr_EV_P_neg_2 = pyo.Constraint(model.Mev, model.t, rule=Constraint_EV_P_neg_2)
'''
BESS pyomo block.
It includes performance characteristics and costs calculation. The number of batteries can be optimized or fixed.
'''

import pyomo.environ as pyo
import math


def Battery_block(model, l_BESS, l_t, AllInputs, emergency):
    """
    BESS system.

    It can include different battery models, which will be trated as different subsystems.
    Each BESS subsystem is composed by an amount of existing capacity and can be expanded.
    The capacity expansion can also be fixed.
    This model includes performance characteristics and costs calculation, as well as a sizing limitation.
    It includes some considerations about battery degradation, aging or life cycle.

    This is a MILP model.
    Integer variable to indicate the number of batteries.

    :param model: pyomo ``Block()`` or ``Model()`` in which the BESS system is added
    :param l_BESS: ``list`` containing all BESS subsystems id
    :param l_t: ``list`` containing all time-steps
    :param AllInputs: data class

    Pyomo parameters:
        - ...
    Pyomo variables:
        - ...
    Pyomo constraints:
        - ... ESCRIBIR VARIABLES Y PARAMETROS EN FORMATO MATEMATICO, Y AQUÍ PONER LA DESCRIPCIÓN DE LAS RESTRICCIONES Y SUS ECUACIONES

    Block inputs: -

    Block outputs: BESS_P_char, BESS_P_disch, BESS_C_capex, BESS_C_incentives, BESS_C_opex, BESS_C_replacement
    """

    ##### Model Sets #####

    # model.t = pyo.Set(initialize=l_t)  # time steps to consider in the optimization (time horizon=365 days)
    # model.i_BESS = pyo.Set(initialize=l_BESS)  # models/elements of BESS


    ##### Model Parameters #####

    model.BESS_SOC_min = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.SOCmin,
                                   within=pyo.NonNegativeReals)  # minimum state of charge [pu]
    # model.BESS_SOC_max = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.SOCmax,
    #                                within=pyo.NonNegativeReals)  # maximum state of charge [pu]
    model.BESS_SOC_max = pyo.Param(model.i_BESS, model.t, initialize=AllInputs.BESS.SOCmax_hourly,
                                   within=pyo.NonNegativeReals)  # maximum state of charge [pu] at each time-step including calendar aging
    model.BESS_SOC_ini = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.SOCini,
                                   within=pyo.Any)  # state of charge at the start of an islanded period for the islandable analysis [pu]
    model.BESS_tau = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.tau,
                               within=pyo.NonNegativeReals)  # Energy loss ratio of the storage or self-discharge rate [pu]
    model.BESS_ef_char = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.charEff,
                                   within=pyo.NonNegativeReals)  # Charging efficiency [pu]
    model.BESS_ef_disch = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.dischEff,
                                    within=pyo.NonNegativeReals)  # Discharging efficiency [pu]
    model.BESS_E = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.throughput,
                            within=pyo.NonNegativeReals)  # throughput de una unidad de bateria [kWh]
    model.BESS_Pn_char0 = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.existent_Pn_char,
                                    within=pyo.NonNegativeReals)  # maximum charging power [kW] of the battery already in the system
    model.BESS_Pn_disch0 = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.existent_Pn_disch,
                                     within=pyo.NonNegativeReals)  # maximum discharging power [kW] of the battery already in the system
    model.BESS_C_bat0 = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.existent_C,
                                  within=pyo.NonNegativeReals)  # storage capacity [kWh] of the battery already in the system
    model.BESS_Pn_char1 = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.maxCharge_kW,
                                    within=pyo.NonNegativeReals)  # maximum charging power of 1 battery [kW]
    model.BESS_Pn_disch1 = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.maxDischarge_kW,
                                     within=pyo.NonNegativeReals)  # maximum discharging power of 1 battery [kW]
    model.BESS_C_1 = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.capacity_kWh,
                               within=pyo.NonNegativeReals)  # storage capacity of 1 battery [kWh]
    model.BESS_k0 = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.existent_u,
                              within=pyo.NonNegativeIntegers)  # battery installed [units] already in the system
    model.BESS_c_capex = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.capital,
                                   within=pyo.NonNegativeReals)  # Battery capital cost [€/unidad]
    model.BESS_c_opex = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.om,
                                  within=pyo.NonNegativeReals)  # Battery operation and maintenance cost [€/(year*unidad)]
    model.BESS_c_replacement = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.replacement,
                                         within=pyo.NonNegativeReals)  # Battery replacement cost [€/unidad]
    # BESS_n_r = {i_BESS: math.ceil(AllInputs.System.lifetime / AllInputs.BESS.lifetime[i_BESS]) - 1 for i_BESS in l_BESS}
    model.BESS_L = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.lifetime)
    # model.BESS_n_replacement = pyo.Param(model.i_BESS, initialize=BESS_n_r)  # number of times the battery has to be replaced during the project lifetime
    model.BESS_c_incentives = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.capex_incentives,
                                        within=pyo.NonNegativeReals)  # economic incentives on the Battery capex [€/kWh]
    model.BESS_fix_k = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.fix_u, within=pyo.Any)  # number of batteries (to add) if it is fixed
    model.BESS_c_degradation = pyo.Param(model.i_BESS, initialize=AllInputs.BESS.degradation_cost, within=pyo.NonNegativeReals)  # cost of cycle aging [€/kWh carged and discharged]


    ##### Model Variables #####

    model.BESS_P_char = pyo.Var(model.i_BESS, model.t, within=pyo.NonNegativeReals)  # Battery charging power [kW]
    model.BESS_P_disch = pyo.Var(model.i_BESS, model.t, within=pyo.NonNegativeReals)  # Battery discharging power [kW]
    model.BESS_SOC = pyo.Var(model.i_BESS, model.t, within=pyo.NonNegativeReals)  # state of charge of the battery [kW]
    model.BESS_Pn_char = pyo.Var(model.i_BESS, within=pyo.NonNegativeReals)  # maximum battery charging power [kW]
    model.BESS_Pn_disch = pyo.Var(model.i_BESS, within=pyo.NonNegativeReals)  # maximum battery discharging power [kW]
    model.BESS_C = pyo.Var(model.i_BESS, within=pyo.NonNegativeReals)  # energy storage capacity of the battery [kWh]
    model.BESS_k = pyo.Var(model.i_BESS, within=pyo.NonNegativeIntegers)  # number of batteries (to add)
    #
    model.BESS_C_capex = pyo.Var(model.i_BESS, within=pyo.NonNegativeReals)  # total battery CAPEX [€]
    model.BESS_C_incentives = pyo.Var(model.i_BESS, within=pyo.NonNegativeReals)  # total incentives on the battery CAPEX [€]
    model.BESS_C_opex = pyo.Var(model.i_BESS, within=pyo.NonNegativeReals)  # total annual battery OPEX [€]
    model.BESS_C_replacement1 = pyo.Var(model.i_BESS, within=pyo.NonNegativeReals)  # total cost of battery replacement in 1 year [€]
    model.BESS_C_replacement = pyo.Var(model.i_BESS, within=pyo.NonNegativeReals)  # total cost of battery replacement during the project lifetime [€]
    model.BESS_C_degradation = pyo.Var(model.i_BESS, within=pyo.NonNegativeReals)  # annual cost of cycle aging [€]
    #
    model.BESS_pos_bus = pyo.Param(model.i_BESS, model.i_bus, initialize=AllInputs.BESS.pos_bus, within=pyo.Binary)  # binary that indicates the bus to which the BESS is connected --> [id_load,id_bus]=1


    ##### Model Constraints #####

    def Constraint_BESS_Pn_char(m, i_BESS):
        """
        Constraint: the maximum BESS charging power of the subsystem is calculated multiplying the maximum charging power of 1 battery and the number of batteries
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :return: expression of the constraint for every i_BESS
        """
        return m.BESS_Pn_char[i_BESS] == m.BESS_k[i_BESS] * m.BESS_Pn_char1[i_BESS]
    model.Constr_BESS_Pn_char = pyo.Constraint(model.i_BESS, rule=Constraint_BESS_Pn_char)

    def Constraint_BESS_Pn_disch(m, i_BESS):
        """
        Constraint: the maximum BESS discharging power of the subsystem is calculated multiplying the maximum discharging power of 1 battery and the number of batteries
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :return: expression of the constraint for every i_BESS
        """
        return m.BESS_Pn_disch[i_BESS] == m.BESS_k[i_BESS] * m.BESS_Pn_disch1[i_BESS]
    model.Constr_BESS_Pn_disch = pyo.Constraint(model.i_BESS, rule=Constraint_BESS_Pn_disch)

    def Constraint_BESS_C(m, i_BESS):
        """
        Constraint: the energy storage capacity of the subsystem is calculated multiplying the storage capacity of 1 battery and the number of batteries
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :return: expression of the constraint for every i_BESS
        """
        return m.BESS_C[i_BESS] == m.BESS_k[i_BESS] * m.BESS_C_1[i_BESS]
    model.Constr_BESS_C = pyo.Constraint(model.i_BESS, rule=Constraint_BESS_C)

    def Constraint_BESS_SOC_min(m, i_BESS, t):  # SOC en kWh
        """
        Constraint: state of charge lower limit
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :param t: time-step index
        :return: expression of the constraint for every t and i_BESS
        """
        return m.BESS_SOC_min[i_BESS] * (m.BESS_C[i_BESS] + m.BESS_C_bat0[i_BESS]) <= m.BESS_SOC[i_BESS, t]
    model.Constr_BESS_SOC_min = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_BESS_SOC_min)

    def Constraint_BESS_SOC_max(m, i_BESS, t):  # SOC en kWh
        """
        Constraint: state of charge upper limit
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :param t: time-step index
        :return: expression of the constraint for every t and i_BESS
        """
        return m.BESS_SOC[i_BESS, t] <= m.BESS_SOC_max[i_BESS, t] * (m.BESS_C[i_BESS] + m.BESS_C_bat0[i_BESS])
    model.Constr_BESS_SOC_max = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_BESS_SOC_max)

    def Constraint_BESS_P_char(m, i_BESS, t):
        """
        Constraint: BESS charging power upper limit
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :param t: time-step index
        :return: expression of the constraint for every t and i_BESS
        """
        return m.BESS_P_char[i_BESS, t] <= (m.BESS_Pn_char[i_BESS] + m.BESS_Pn_char0[i_BESS])
    model.Constr_BESS_P_char = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_BESS_P_char)

    def Constraint_BESS_P_disch(m, i_BESS, t):
        """
        Constraint: BESS discharging power upper limit
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :param t: time-step index
        :return: expression of the constraint for every t and i_BESS
        """
        return m.BESS_P_disch[i_BESS, t] <= (m.BESS_Pn_disch[i_BESS] + m.BESS_Pn_disch0[i_BESS])
    model.Constr_BESS_P_disch = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_BESS_P_disch)

    def Constraint_BESS_SOC(m, i_BESS, t):
        """
        Constraint: BESS state of charge evolution with time is calculated considering charging and discharging efficiencies, as well as a self-discharge ratio.
        It is supposed that the SOC at the start and at the end of the year is the same (cyclic operation).
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :param t: time-step index
        :return: expression of the constraint for every t and i_BESS
        """
        if t > 0:
            # t --> t+1
            return m.BESS_SOC[i_BESS, t] == m.BESS_SOC[i_BESS, t - 1] * (1 - m.BESS_tau[i_BESS]) + \
                (m.BESS_P_char[i_BESS, t] * m.BESS_ef_char[i_BESS] - m.BESS_P_disch[i_BESS, t] / m.BESS_ef_disch[i_BESS]) * m.inc_t
        else:  # SOC[0]=SOC[fin]
            if emergency==False:
                return m.BESS_SOC[i_BESS, l_t[0]] == m.BESS_SOC[i_BESS, l_t[-1]] * (1 - m.BESS_tau[i_BESS]) + \
                    (m.BESS_P_char[i_BESS, l_t[0]] * m.BESS_ef_char[i_BESS] - m.BESS_P_disch[i_BESS, l_t[0]] / m.BESS_ef_disch[i_BESS]) * m.inc_t
            else:  # state of charge at the start of an islanded period for the islandable analysis [pu]
                return m.BESS_SOC[i_BESS, l_t[0]] == m.BESS_SOC_ini[i_BESS] * (m.BESS_C[i_BESS] + m.BESS_C_bat0[i_BESS]) * (1 - m.BESS_tau[i_BESS]) + \
                    (m.BESS_P_char[i_BESS, l_t[0]] * m.BESS_ef_char[i_BESS] - m.BESS_P_disch[i_BESS, l_t[0]] / m.BESS_ef_disch[i_BESS]) * m.inc_t
    model.Constr_BESS_SOC = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_BESS_SOC)

    def Calculo_BESS_C_capex(m, i_BESS):
        """
        Constraint: total BESS CAPEX is calculated multiplying the unitary cost and the number of batteries (to add)
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :return: expression of the constraint for every i_BESS
        """
        return m.BESS_C_capex[i_BESS] == m.BESS_c_capex[i_BESS] * m.BESS_k[i_BESS]
    model.Constr_BESS_C_capex = pyo.Constraint(model.i_BESS, rule=Calculo_BESS_C_capex)

    def Calculo_BESS_C_incentives(m, i_BESS):
        """
        Constraint: total incentices for BESS is calculated multiplying the unitary incentives and the number of batteries (to add)
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :return: expression of the constraint for every i_BESS
        """
        return m.BESS_C_incentives[i_BESS] == m.BESS_c_incentives[i_BESS] * m.BESS_C[i_BESS]
    model.Constr_BESS_C_incentives = pyo.Constraint(model.i_BESS, rule=Calculo_BESS_C_incentives)

    def Calculo_BESS_C_opex(m, i_BESS):
        """
        Constraint: total BESS OPEX is calculated multiplying the unitary cost and the number of batteries (considering both new and existent)
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :return: expression of the constraint for every i_BESS
        """
        return m.BESS_C_opex[i_BESS] == m.BESS_c_opex[i_BESS] * (m.BESS_k[i_BESS] + m.BESS_k0[i_BESS])
    model.Constr_BESS_C_opex = pyo.Constraint(model.i_BESS, rule=Calculo_BESS_C_opex)

    def Calculo_BESS_C_replacement1(m, i_BESS):
        """
        Constraint: total annual BESS replacement cost is calculated multiplying the unitary cost and the number of batteries
        (considering both new and existent, supposing existent capacity is replaced at the same time as the new one)
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :return: expression of the constraint for every i_BESS
        """
        return m.BESS_C_replacement1[i_BESS] == m.BESS_c_replacement[i_BESS] * (m.BESS_k[i_BESS] + m.BESS_k0[i_BESS])
    model.Constr_BESS_C_replacement1 = pyo.Constraint(model.i_BESS, rule=Calculo_BESS_C_replacement1)
    def Calculo_BESS_C_replacement(m, i_BESS):
        """
        Constraint: total BESS replacement cost is calculated as the NPC of the annual replacement cost
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :return: expression of the constraint for every i_BESS
        """
        # m.BESS_C_replacement[i_BESS] == m.BESS_C_replacement1[i_BESS] * m.BESS_n_replacement[i_BESS]
        return m.BESS_C_replacement[i_BESS] == sum(m.BESS_C_replacement1[i_BESS]/(1+m.discount_rate)**y
                                                   for y in range(AllInputs.BESS.lifetime[i_BESS], AllInputs.System.lifetime, AllInputs.BESS.lifetime[i_BESS]))

    model.Constr_BESS_C_replacement = pyo.Constraint(model.i_BESS, rule=Calculo_BESS_C_replacement)

    def Constraint_BESS_fix_k(m, i_BESS):
        """
        Constraint: if a subsystem is set as non-expandable or the aim is to perform an operation optimization,
        the number of batteries (to add) is fixed to a certain value
        :param m: Pyomo optimization model
        :param i_BESS: BESS model or subsystem index
        :return: expression of the constraint for every i_BESS
        """
        if AllInputs.BESS.sizing[i_BESS] == 0:
            return m.BESS_k[i_BESS] == m.BESS_fix_k[i_BESS]
        else:
            return pyo.Constraint.Skip
    model.Constr_BESS_fix_k = pyo.Constraint(model.i_BESS, rule=Constraint_BESS_fix_k)

    def Constraint_throughput(m, i_BESS):
        return sum(m.BESS_P_disch[i_BESS, t] for t in l_t) * m.inc_t / m.BESS_ef_disch[i_BESS] <= (m.BESS_k0[i_BESS] + m.BESS_k[i_BESS]) * m.BESS_E[i_BESS] / m.BESS_L[i_BESS]
    model.Constr_Bat10 = pyo.Constraint(model.i_BESS, rule=Constraint_throughput)

    def Constraint_BESS_degradation_cost(m, i_BESS):  # it works also as minor term to avoid BESS charging and discharging simultaneously
        return m.BESS_C_degradation[i_BESS] == sum(m.BESS_P_char[i_BESS, t]+m.BESS_P_disch[i_BESS, t] for i_BESS in l_BESS for t in l_t) * m.inc_t * m.BESS_c_degradation[i_BESS]
    model.Constr_BESS_degradation_cost = pyo.Constraint(model.i_BESS, rule=Constraint_BESS_degradation_cost)

    # model.char_disch_estricta = pyo.Var(model.i_BESS, model.t, within=pyo.Binary)  # 1: carga, 0: descarga
    # def Constraint_char_disch_estricta_1(m, i_BESS, t):
    #     return m.BESS_P_char[i_BESS, t] <= m.char_disch_estricta[i_BESS, t] * 10**6
    # def Constraint_char_disch_estricta_2(m, i_BESS, t):
    #     return m.BESS_P_disch[i_BESS, t] <= (1 - m.char_disch_estricta[i_BESS, t]) * 10**6
    # model.Constr_char_disch_estricta_1 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_char_disch_estricta_1)
    # model.Constr_char_disch_estricta_2 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_char_disch_estricta_2)
    #
    # model.no_use = pyo.Var(model.i_BESS, model.t, within=pyo.Binary)  # 1: bateria en useo, 0: bateria sin intercambio de potencia
    # def Constraint_no_use_1(m, i_BESS, t):
    #     return m.no_use[i_BESS, t] <= (m.BESS_P_char[i_BESS, t] + m.BESS_P_disch[i_BESS, t]) * 10**6
    # def Constraint_no_use_2(m, i_BESS, t):
    #     return m.BESS_P_char[i_BESS, t] + m.BESS_P_disch[i_BESS, t] <= m.no_use[i_BESS, t] * 10**6
    # model.Constr_no_use_1 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_no_use_1)
    # model.Constr_no_use_2 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_no_use_2)
    #
    # model.ciclos_char_disch = pyo.Var(model.i_BESS, model.t, within=pyo.Binary)  # 1: ciclo de carga, 0: ciclo de descarga
    # model.aux_estricta_use_t = pyo.Var(model.i_BESS, model.t, within=pyo.Binary)  # = m.char_disch_estricta[i_BESS, t] * m.no_use[i_BESS, t]
    # model.aux_estricta_use_t1 = pyo.Var(model.i_BESS, model.t, within=pyo.Binary)  # = m.char_disch_estricta[i_BESS, t-1] * m.no_use[i_BESS, t]
    # def Constraint_ciclos_char_disch(m, i_BESS, t):
    #     if t>l_t[0]:
    #         return m.ciclos_char_disch[i_BESS, t] == m.aux_estricta_use_t[i_BESS, t] + m.char_disch_estricta[i_BESS, t-1] - m.aux_estricta_use_t1[i_BESS, t]
    #     else:
    #         return m.ciclos_char_disch[i_BESS, t] == m.aux_estricta_use_t[i_BESS, t] + m.char_disch_estricta[i_BESS, l_t[-1]] - m.aux_estricta_use_t1[i_BESS, t]
    # model.Constr_ciclos_char_disch = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_ciclos_char_disch)
    # def Constraint_aux_estricta_use_t_1(m, i_BESS, t):
    #     return m.aux_estricta_use_t[i_BESS, t] <= m.char_disch_estricta[i_BESS, t]
    # def Constraint_aux_estricta_use_t_2(m, i_BESS, t):
    #     return m.aux_estricta_use_t[i_BESS, t] <= m.no_use[i_BESS, t]
    # def Constraint_aux_estricta_use_t_3(m, i_BESS, t):
    #     return m.aux_estricta_use_t[i_BESS, t] >= m.char_disch_estricta[i_BESS, t] + m.no_use[i_BESS, t] - 1
    # model.Constr_aux_estricta_use_t_1 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_aux_estricta_use_t_1)
    # model.Constr_aux_estricta_use_t_2 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_aux_estricta_use_t_2)
    # model.Constr_aux_estricta_use_t_3 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_aux_estricta_use_t_3)
    # def Constraint_aux_estricta_use_t1_1(m, i_BESS, t):
    #     if t>l_t[0]:
    #         return m.aux_estricta_use_t1[i_BESS, t] <= m.char_disch_estricta[i_BESS, t-1]
    #     else:
    #         return m.aux_estricta_use_t1[i_BESS, t] <= m.char_disch_estricta[i_BESS, l_t[-1]]
    # def Constraint_aux_estricta_use_t1_2(m, i_BESS, t):
    #     return m.aux_estricta_use_t1[i_BESS, t] <= m.no_use[i_BESS, t]
    # def Constraint_aux_estricta_use_t1_3(m, i_BESS, t):
    #     if t>l_t[0]:
    #         return m.aux_estricta_use_t1[i_BESS, t] >= m.char_disch_estricta[i_BESS, t-1] + m.no_use[i_BESS, t] - 1
    #     else:
    #         return m.aux_estricta_use_t1[i_BESS, t] >= m.char_disch_estricta[i_BESS, l_t[-1]] + m.no_use[i_BESS, t] - 1
    # model.Constr_aux_estricta_use_t1_1 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_aux_estricta_use_t1_1)
    # model.Constr_aux_estricta_use_t1_2 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_aux_estricta_use_t1_2)
    # model.Constr_aux_estricta_use_t1_3 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_aux_estricta_use_t1_3)
    #
    # model.SOC_pico = pyo.Var(model.i_BESS, model.t, within=pyo.Binary)  # 1: pasa de cargar a descargar, 0: resto
    # model.aux_ciclos_t_t1 = pyo.Var(model.i_BESS, model.t, within=pyo.Binary)  # = m.ciclos_char_disch[i_BESS, t+1] * m.ciclos_char_disch[i_BESS, t]
    # def Constraint_SOC_pico(m, i_BESS, t):
    #     return m.SOC_pico[i_BESS, t] == m.ciclos_char_disch[i_BESS, t] - m.aux_ciclos_t_t1[i_BESS, t]
    # model.Constr_SOC_pico = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_SOC_pico)
    # def Constraint_aux_ciclos_t_t1_1(m, i_BESS, t):
    #     if t<l_t[-1]:
    #         return m.aux_ciclos_t_t1[i_BESS, t] <= m.ciclos_char_disch[i_BESS, t+1]
    #     else:
    #         return m.aux_ciclos_t_t1[i_BESS, t] <= m.ciclos_char_disch[i_BESS, l_t[0]]
    # def Constraint_aux_ciclos_t_t1_2(m, i_BESS, t):
    #     return m.aux_ciclos_t_t1[i_BESS, t] <= m.ciclos_char_disch[i_BESS, t]
    # def Constraint_aux_ciclos_t_t1_3(m, i_BESS, t):
    #     if t < l_t[-1]:
    #         return m.aux_ciclos_t_t1[i_BESS, t] >= m.ciclos_char_disch[i_BESS, t+1] + m.ciclos_char_disch[i_BESS, t] - 1
    #     else:
    #         return m.aux_ciclos_t_t1[i_BESS, t] >= m.ciclos_char_disch[i_BESS, l_t[0]] + m.ciclos_char_disch[i_BESS, t] - 1
    # model.Constr_aux_ciclos_t_t1_1 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_aux_ciclos_t_t1_1)
    # model.Constr_aux_ciclos_t_t1_2 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_aux_ciclos_t_t1_2)
    # model.Constr_aux_ciclos_t_t1_3 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_aux_ciclos_t_t1_3)





    # model.char_disch_estricta = pyo.Var(model.i_BESS, model.t, within=pyo.Binary)  # 1: carga, 0: descarga
    # def Constraint_char_disch_estricta_1(m, i_BESS, t):
    #     return m.BESS_P_char[i_BESS, t] <= m.char_disch_estricta[i_BESS, t] * 10**6
    # def Constraint_char_disch_estricta_2(m, i_BESS, t):
    #     return m.BESS_P_disch[i_BESS, t] <= (1 - m.char_disch_estricta[i_BESS, t]) * 10**6
    # model.Constr_char_disch_estricta_1 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_char_disch_estricta_1)
    # model.Constr_char_disch_estricta_2 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_char_disch_estricta_2)
    #
    # model.cambio = pyo.Var(model.i_BESS, model.t, within=pyo.Binary)  # 1: cambio carga-descarga, 0: no
    # model.aux_cambio = pyo.Var(model.i_BESS, model.t, within=pyo.Binary)  # = m.char_disch_estricta[i_BESS, t] * m.char_disch_estricta[i_BESS, t+1]
    # def Constraint_cambio(m, i_BESS, t):
    #     # m.cambio[i_BESS, t] == m.char_disch_estricta[i_BESS, t] XOR m.char_disch_estricta[i_BESS, t+1]
    #     # m.cambio[i_BESS, t] == m.char_disch_estricta[i_BESS, t] * (1 - m.char_disch_estricta[i_BESS, t+1]) + (1 - m.char_disch_estricta[i_BESS, t]) * m.char_disch_estricta[i_BESS, t+1]
    #     # m.cambio[i_BESS, t] == m.char_disch_estricta[i_BESS, t] + m.char_disch_estricta[i_BESS, t+1] - 2 * m.char_disch_estricta[i_BESS, t] * m.char_disch_estricta[i_BESS, t+1]
    #     if t < l_t[-1]:
    #         return m.cambio[i_BESS, t] == m.char_disch_estricta[i_BESS, t] + m.char_disch_estricta[i_BESS, t+1] - 2 * m.aux_cambio[i_BESS, t]
    #     else:
    #         return m.cambio[i_BESS, t] == m.char_disch_estricta[i_BESS, t] + m.char_disch_estricta[i_BESS, l_t[0]] - 2 * m.aux_cambio[i_BESS, t]
    # model.Constr_cambio = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_cambio)
    # def Constraint_aux_cambio_1(m, i_BESS, t):
    #     return m.aux_cambio[i_BESS, t] <= m.char_disch_estricta[i_BESS, t]
    # def Constraint_aux_cambio_2(m, i_BESS, t):
    #     if t < l_t[-1]:
    #         return m.aux_cambio[i_BESS, t] <= m.char_disch_estricta[i_BESS, t+1]
    #     else:
    #         return m.aux_cambio[i_BESS, t] <= m.char_disch_estricta[i_BESS, l_t[0]]
    # def Constraint_aux_cambio_3(m, i_BESS, t):
    #     if t < l_t[-1]:
    #         return m.aux_cambio[i_BESS, t] <= m.char_disch_estricta[i_BESS, t] + m.char_disch_estricta[i_BESS, t+1] - 1
    #     else:
    #         return m.aux_cambio[i_BESS, t] <= m.char_disch_estricta[i_BESS, t] + m.char_disch_estricta[i_BESS, l_t[0]] - 1
    # model.Constr_aux_cambio_1 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_aux_cambio_1)
    # model.Constr_aux_cambio_2 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_aux_cambio_2)
    # model.Constr_aux_cambio_3 = pyo.Constraint(model.i_BESS, model.t, rule=Constraint_aux_cambio_3)
    #
    # def Constaint_cambio_max(m, i_BESS):
    #     return sum(m.cambio[i_BESS, t] for t in l_t) <= 35*4
    # model.Constr_cambio_max = pyo.Constraint(model.i_BESS, rule=Constaint_cambio_max)

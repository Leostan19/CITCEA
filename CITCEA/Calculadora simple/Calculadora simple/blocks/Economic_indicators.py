import pyomo.environ as pyo
import math

def Economic_indicators_block(block, l_t, l_PV, l_BESS, l_Mev, AllInputs):
    '''
    Economic indicators

    Considering all systems, some economic indicators are calculated and specific constraints can be applied to them.
    The economic indicators considered are: total investment (includes replacements), ROI, and payback

    This model is mixed-integer quadratic.
    Definition of payback and ROI is quadratic, the rest of the constraints are linear.
    ROI and payback constraints are currently disabled, making the model LP!!!

    :param block: pyomo ``Block()`` or ``Model()`` in which the indicators is added
    :param model_i_PV: pyomo ``Set()`` referring to the PV subsystem
    :param l_PV: ``list`` containing all PV subsystems id
    :param model_i_BESS: pyomo ``Set()`` referring to the BESS subsystem
    :param l_BESS: ``list`` containing all BESS subsystems id
    :param model_Md: pyomo ``Set()`` referring to the disconnectable load
    :param l_Md: ``list`` containing all disconnectable loads id
    :param model_Mf: pyomo ``Set()`` referring to the power-shiftable load
    :param l_Mf: ``list`` containing all power-shiftable loads id
    :param model_Ms: pyomo ``Set()`` referring to the time-shiftable load
    :param l_Ms: ``list`` containing all time-shiftable loads id
    :param model_Mev: pyomo ``Set()`` referring to the EV
    :param l_Mev: ``list`` containing all EV id
    :param model_t: pyomo ``Set()`` referring to the time-step
    :param l_t: ``list`` containing all time-steps
    :param AllInputs: data class

    Pyomo parameters:
        - ...
    Pyomo variables:
        - ...
    Pyomo constraints:
        - ... ESCRIBIR VARIABLES Y PARAMETROS EN FORMATO MATEMATICO, Y AQUÍ PONER LA DESCRIPCIÓN DE LAS RESTRICCIONES Y SUS ECUACIONES

    Block inputs: PV_C_capex, PV_C_incentives, PV_C_opex, PV_C_replacement,
                  BESS_C_capex, BESS_C_incentives, BESS_C_opex, BESS_C_replacement,
                  GS_C_capex, GS_C_incentives, GS_C_opex, GS_C_replacement, GS_C_fuel_anual, GS_C_emissions,
                  Grid_C_buy, Grid_R_sell, Grid_C_power, Grid_C_penalisation, Grid_C_emission
                  discL_flexibility_cost, reducL_flexibility_cost, PshiftL_flexibility_cost, TshiftL_flexibility_cost, EV_flexibility_cost,
                  FlexReq_max.R, FlexReq_min.R, FlexReq_eq.R

    Block outputs: total_investment, total_annual_costs
    '''

    ##### Model Sets #####

    # model.t = pyo.Set(initialize=l_t)  # time steps to consider in the optimization (time horizon=365 days)
    # model.i_PV = pyo.Set(initialize=l_PV)  # models/elements of PV
    # model.i_BESS = pyo.Set(initialize=l_BESS)  # models/elements of GS


    ##### Model Parameters #####

    block.annual_cost_reference = pyo.Param(initialize=AllInputs.System.annual_cost_reference)


    ##### Model Variables #####

    block.total_flexibility_cost = pyo.Var(within=pyo.NonNegativeReals)  # total annual cost of loads flexibility [€]
    block.total_investment = pyo.Var(within=pyo.NonNegativeReals)  # total investment cost in the project lifetime [€]
    block.total_annual_costs = pyo.Var(within=pyo.NonNegativeReals)  # total annual costs [€], supposed the same in all years during the project lifetime
    block.ROI = pyo.Var(within=pyo.Reals)  # return of investment [%]
    block.is_investment = pyo.Var(within=pyo.Binary)  # binary that indicates if there is investment. 1: yes, 0: no
    block.payback = pyo.Var(within=pyo.Reals)  # payback time [years]



    ##### Model Constraints #####

    '''Calculation of indicators'''

    def Constraint_total_flexibility_cost(m):
        '''
        Constraint: total annual cost of flexible loads is calculated considering disconnectable, power-shiftable, time-shiftable, and EV
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        return m.total_flexibility_cost == sum(m.EV_flexibility_cost[Mev] for Mev in l_Mev)
    block.Constr_Calc25 = pyo.Constraint(rule=Constraint_total_flexibility_cost)

    def Constraint_total_investment(m):
        '''
        Constraint: total investment cost is calculated considering PV, BESS, GS.
        This costs includes CAPEX, incentives and replacement costs
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        capex_total = sum(m.PV_C_capex[i_PV] for i_PV in l_PV) \
                      + sum(m.BESS_C_capex[i_BESS] for i_BESS in l_BESS)
        incentives_total = sum(m.PV_C_incentives[i_PV] for i_PV in l_PV) \
                           + sum(m.BESS_C_incentives[i_BESS] for i_BESS in l_BESS)
        replacement_total = sum(m.PV_C_replacement[i_PV] for i_PV in l_PV) \
                            + sum(m.BESS_C_replacement[i_BESS] for i_BESS in l_BESS)
        return m.total_investment == capex_total - incentives_total + replacement_total
    block.Constr_Calc21 = pyo.Constraint(rule=Constraint_total_investment)

    def Constraint_total_annual_costs(m):
        '''
        Constraint: total annual cost is calculated considering PV, BESS, GS, grid connection, loads flexibility, flexibility requests, not supplied load (island)
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        Com_total = sum(m.PV_C_opex[i_PV] for i_PV in l_PV) \
                    + sum(m.BESS_C_opex[i_BESS] for i_BESS in l_BESS) \
                    + sum(m.BESS_C_degradation[i_BESS] for i_BESS in l_BESS)
        C_grid_total = sum(m.Grid_C_buy[i_Grid] - m.Grid_R_sell[i_Grid] + m.Grid_C_power[i_Grid] + m.Grid_C_penalisation[i_Grid] + m.Grid_C_emission[i_Grid] for i_Grid in AllInputs.Grid.id_list)
        return m.total_annual_costs == Com_total \
            + C_grid_total + m.total_flexibility_cost + m.noSupply_C
    block.Constr_Calc22 = pyo.Constraint(rule=Constraint_total_annual_costs)

    def Constraint_is_investment1(m):
        '''
        Constraint: definition of the there is investment binary, here lower limit is applied.
        Note: total investment lower than 0.1 € will be considered as 0, and therefore as no invesment is happening
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        return m.is_investment * 0.1 <= m.total_investment
    block.Constr_Calc26 = pyo.Constraint(rule=Constraint_is_investment1)
    def Constraint_is_investment2(m):
        '''
        Constraint: definition of the there is investment binary, here upper limit is applied.
        Note: due to solver tolerance, total investment has to be lower or equal than 100 M€.
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        return m.total_investment / 100 <= m.is_investment * 10**6
    block.Constr_Calc27 = pyo.Constraint(rule=Constraint_is_investment2)

    def Constraint_ROI(m):
        '''
        Restricción: ROI [%] is calculated as
        ROI = (annual_cost_reference - total_annual_costs) / total_investment * 100
        where total_investment includes both initial investment and replacements
        :param m: Pyomo optimization model
        :return: expression of the constraint
        '''
        # m.ROI == (m.annual_cost_reference - m.total_annual_costs) / m.total_investment * 100
        return m.ROI * m.total_investment == (m.annual_cost_reference - m.total_annual_costs) * 100 * m.is_investment
    # block.Constr_Calc23 = pyo.Constraint(rule=Constraint_ROI)

    def Constraint_payback(m):
        '''
        Constraint: payback [years] is calculated as the total investment divided by
        the difference in annual costs between the reference and the optimization
        :param m: Pyomo optimization model
        :return: expression of the constraint
        payback = total_investment / (annual_cost_reference - total_annual_costs)
        where total_investment includes both initial investment and replacements
        '''
        # m.payback == m.total_investment / (m.annual_cost_reference - m.total_annual_costs)
        return m.payback * (m.annual_cost_reference - m.total_annual_costs) == m.total_investment
    # block.Constr_Calc24 = pyo.Constraint(rule=Constraint_payback)

    '''Constraints of the indicators'''

    def Constraint_ROI_max(m, v):
        '''
        Constraint: ROI has to be lower or equal than a specified value
        :param m: Pyomo optimization model
        :param v: maximum ROI
        :return: expression of the constraint
        '''
        return m.ROI <= v

    def Constraint_ROI_min(m, v):
        '''
        Constraint: ROI has to be higher or equal than a specified value
        :param m: Pyomo optimization model
        :param v: minimum ROI
        :return: expression of the constraint
        '''
        return m.ROI >= v

    def Constraint_ROI_eq(m, v):
        '''
        Constraint: ROI has to be equal to a specified value
        :param m: Pyomo optimization model
        :param v: ROI
        :return: expression of the constraint
        '''
        return m.ROI == v

    def Constraint_payback_max(m, v):
        '''
        Constraint: payback has to be lower or equal than a specified value
        :param m: Pyomo optimization model
        :param v: maximum payback
        :return: expression of the constraint
        '''
        return m.payback <= v

    def Constraint_payback_min(m, v):
        '''
        Constraint: payback has to be higher or equal than a specified value
        :param m: Pyomo optimization model
        :param v: minimum payback
        :return: expression of the constraint
        '''
        return m.payback >= v

    def Constraint_payback_eq(m, v):
        '''
        Constraint: payback has to be equal to a specified value
        :param m: Pyomo optimization model
        :param v: payback
        :return: expression of the constraint
        '''
        return m.payback == v

    def Constraint_investment_max(m, v):
        '''
        Constraint: total investment has to be lower or equal than a specified value
        :param m: Pyomo optimization model
        :param v: maximum investment
        :return: expression of the constraint
        '''
        return m.total_investment <= v

    def Constraint_investment_min(m, v):
        '''
        Constraint: total investment has to be higher or equal than a specified value
        :param m: Pyomo optimization model
        :param v: minimum investment
        :return: expression of the constraint
        '''
        return m.total_investment >= v

    def Constraint_investment_eq(m, v):
        '''
        Constraint: total investment has to be equal to a specified value
        :param m: Pyomo optimization model
        :param v: investment
        :return: expression of the constraint
        '''
        return m.total_investment == v

    if AllInputs.economic_constraints:  # si no es una lista vacia
        for constr in AllInputs.economic_constraints:
            if constr.enabled == 1:
                # if constr.variable == 'ROI':
                #     if constr.expression == '<=':
                #         block.Constr_ROI_max = pyo.Constraint(rule=Constraint_ROI_max(block, constr.value))
                #     elif constr.expression == '>=':
                #         block.Constr_ROI_min = pyo.Constraint(rule=Constraint_ROI_min(block, constr.value))
                #     elif constr.expression == '==':
                #         block.Constr_ROI_eq = pyo.Constraint(rule=Constraint_ROI_eq(block, constr.value))
                # if constr.variable == 'payback':
                #     if constr.expression == '<=':
                #         block.Constr_payback_max = pyo.Constraint(rule=Constraint_payback_max(block, constr.value))
                #     elif constr.expression == '>=':
                #         block.Constr_payback_min = pyo.Constraint(rule=Constraint_payback_min(block, constr.value))
                #     elif constr.expression == '==':
                #         block.Constr_payback_eq = pyo.Constraint(rule=Constraint_payback_eq(block, constr.value))
                if constr.variable == 'investment':
                    if constr.expression == '<=':
                        block.Constr_investment_max = pyo.Constraint(rule=Constraint_investment_max(block, constr.value))
                    elif constr.expression == '>=':
                        block.Constr_investment_min = pyo.Constraint(rule=Constraint_investment_min(block, constr.value))
                    elif constr.expression == '==':
                        block.Constr_investment_eq = pyo.Constraint(rule=Constraint_investment_eq(block, constr.value))

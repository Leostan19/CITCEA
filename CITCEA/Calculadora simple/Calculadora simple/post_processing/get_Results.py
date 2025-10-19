class PVResultsClass:
    '''
    Class that extracts and stores the PV results from the instance
    '''
    def __init__(self, instance):  # instance=instance.PV
        '''
        Class that extracts and stores the PV results from the instance
        :param instance: pyomo solved PV model (instance.PV)
        '''
        self.P = instance.PV_P.get_values() # AllResults.PV.P
        self.G = instance.PV_G.get_values()
        #
        self.C_capex = instance.PV_C_capex.get_values()
        self.C_incentives = instance.PV_C_incentives.get_values()
        self.C_opex = instance.PV_C_opex.get_values()
        self.C_replacement1 = instance.PV_C_replacement1.get_values()
        self.C_replacement = instance.PV_C_replacement.get_values()


class BatteryResultsClass:
    '''
    Class that extracts and stores the BESS results from the instance
    '''
    def __init__(self, instance, l_t, l_BESS):  # instance=instance.BESS
        '''
        Class that extracts and stores the BESS results from the instance
        :param instance: pyomo solved BESS model (instance.BESS)
        :param l_t: ``list`` containing all time-steps
        :param l_BESS: ``list`` containing all BESS subsystems id
        '''
        if not l_BESS:
            self.P_char = {t: 0 for t in l_t}
            self.P_disch = {t: 0 for t in l_t}
            self.SOC = {t: 0 for t in l_t}
            self.Pn_char = 0
            self.Pn_disch = 0
            self.C = 0
            self.k_bat = 0
            self.C_capex = 0
            self.C_incentives = 0
            self.C_opex = 0
            self.C_replacement1 = 0
            self.C_replacement = 0
            self.C_degradation = 0
        else:
            self.P_char = instance.BESS_P_char.get_values()
            self.P_disch = instance.BESS_P_disch.get_values()
            self.SOC = instance.BESS_SOC.get_values()
            self.Pn_char = instance.BESS_Pn_char.get_values()
            self.Pn_disch = instance.BESS_Pn_disch.get_values()
            self.C = instance.BESS_C.get_values()
            self.k_bat = instance.BESS_k.get_values()
            self.C_capex = instance.BESS_C_capex.get_values()
            self.C_incentives = instance.BESS_C_incentives.get_values()
            self.C_opex = instance.BESS_C_opex.get_values()
            self.C_replacement1 = instance.BESS_C_replacement1.get_values()
            self.C_replacement = instance.BESS_C_replacement.get_values()
            self.C_degradation = instance.BESS_C_degradation.get_values()


class GridResultsClass:
    '''
    Class that extracts and stores the Grid results from the instance
    '''
    def __init__(self, instance, l_t, AllInputs):  # instance=instance.Grid
        '''
        Class that extracts and stores the Grid results from the instance
        :param instance: pyomo solved Grid model (instance.Grid)
        :param l_t: ``list`` containing all time-steps
        :param AllInputs: data class which contains all inputs
        '''
        self.P_excess = instance.Grid_P_excess.get_values()

        if AllInputs.Grid.conected1_islanded0 == 1:
            self.P_buy = instance.Grid_P_buy.get_values()
            self.P_sell = instance.Grid_P_sell.get_values()
            self.P_hired_N = instance.Grid_P_hired_N.get_values()
            self.P_hired_t = instance.Grid_P_hired_t.get_values()
            self.lambda_inj = instance.Grid_lambda_inj.get_values()
            self.P_excessmax = instance.Grid_P_excessmax.get_values()
            #
            self.C_buy = instance.Grid_C_buy.get_values()
            self.R_sell = instance.Grid_R_sell.get_values()
            self.C_power = instance.Grid_C_power.get_values()
            self.C_penalisation = instance.Grid_C_penalisation.get_values()
            self.C_emission = instance.Grid_C_emission.get_values()
        else:
            self.P_buy = {(0,t): 0 for t in l_t}
            self.P_sell = {(0,t): 0 for t in l_t}
            self.P_hired_N = {(0,N): 0 for N in AllInputs.Grid.l_N}
            self.P_hired_t = {(0,t): 0 for t in l_t}
            self.lambda_inj = {0:0}
            self.P_excessmax = {0:0}
            #
            self.C_buy = {0:0}
            self.R_sell = {0:0}
            self.C_power = {0:0}
            self.C_penalisation = {0:0}
            self.C_emission = {0:0}


class EVResultsClass:
    '''
    Class that extracts and stores the smart charging EV results from the instance
    '''
    def __init__(self, instance, l_t, AllInputs):  # instance=instance.EV
        '''
        Class that extracts and stores the smart charging EV results from the instance
        :param instance: pyomo solved Grid model (instance.EV)
        :param l_t: ``list`` containing all time-steps
        :param AllInputs: data class which contains all inputs
        '''
        l_Mev = AllInputs.EV.smart.l_Mev
        if AllInputs.EV.hay == 1 and AllInputs.EV.immediate0_smart1 == 1:
            self.P = instance.EV_P.get_values()
            self.flexibility_cost = instance.EV_flexibility_cost.get_values()
            self.is_baseline = instance.EV_is_baseline.get_values()
        else:
            self.P = {(Mev, t): 0 for t in l_t for Mev in l_Mev}
            self.flexibility_cost = {Mev: 0 for Mev in l_Mev}


class NetworkResultsClass:
    def __init__(self, PF_type, instance, l_t, l_bus):
        self.Pinj = instance.Pinj.get_values()
        self.Qinj = instance.Qinj.get_values()
        #
        self.Q_buy = instance.Q_buy.get_values()
        if PF_type == 'DC-OPF':
            self.thetaV = instance.thetaV.get_values()
            self.Pline = instance.Pline.get_values()
        elif PF_type == 'AC-OPF':
            self.Pline = instance.Pline.get_values()
            self.Qline = instance.Qline.get_values()
            self.c = instance.c.get_values()
            self.s = instance.s.get_values()
            self.i_line_squared = {} #instance.i_line_squared.get_values()
            for i_bus1 in l_bus:
                for i_bus2 in l_bus:
                    for t in l_t:
                        self.i_line_squared[i_bus1, i_bus2, t] = (self.Pline[i_bus1, i_bus2, t]**2 + self.Qline[i_bus1, i_bus2, t]**2) / self.c[i_bus1, i_bus1, t]
        else:  # PF_type == 'economic_dispatch'
            ...


class EconomicIndicatorsResultsClass:
    '''
    Class that extracts and stores the Economic indicators results from the instance
    '''
    def __init__(self, instance):
        '''
        Class that extracts and stores the Economic indicators results from the instance
        :param instance: pyomo solved Grid model (instance.Economic_indicators)
        '''
        self.total_flexibility_cost = instance.total_flexibility_cost.get_values()[None]
        self.total_investment = instance.total_investment.get_values()[None]  # = capex_total - incentivos_total + replacement_total
        self.total_annual_costs = instance.total_annual_costs.get_values()[None]  # = Com_total + C_fuel_anual + C_emissions + C_grid_total - I_request
        self.ROI = instance.ROI.get_values()[None]  # = ((annual_cost_reference - allResults.total_annual_costs) * L_prj - allResults.total_investment) / allResults.total_investment * 100  # en porcentage
        self.payback = instance.payback.get_values()[None]  # total_investment/(annual_cost_reference - total_annual_costs)  # periodo de retorno = inversión / beneficio anual
        self.is_investment = instance.is_investment.get_values()[None]


class allResultsClass:
    '''
    Class that extracts and stores all the results from the solved instance
    '''
    def __init__(self, l_t, AllInputs, instance):
        '''
        Class that extracts and stores all the results from the solved instance
        :param instance: pyomo solved Grid model (instance.EV)
        :param l_t: ``list`` containing all time-steps
        :param AllInputs: data class which contains all inputs
        '''
        # sigue exactamente la misma nomenclatura que la optimización

        # General
        self.D = instance.D.get_values()

        # Blocks
        self.PV = PVResultsClass(instance)
        self.BESS = BatteryResultsClass(instance, l_t, AllInputs.BESS.id_list)
        self.Grid = GridResultsClass(instance, l_t, AllInputs)
        self.EV = EVResultsClass(instance, l_t, AllInputs)
        self.Economic_indicators = EconomicIndicatorsResultsClass(instance)

        # Network
        self.Network = NetworkResultsClass(AllInputs.Network.PF_type, instance, l_t, AllInputs.Network.Buses.id_list)

        # Other
        self.noSupply_P = instance.noSupply_P.get_values()
        self.noSupply_C = instance.noSupply_C.get_values()[None]

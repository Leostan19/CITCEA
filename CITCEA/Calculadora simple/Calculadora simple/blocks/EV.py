import pyomo.environ as pyo
import math


def EV_block(model, l_t, l_Mev, l_bus, AllInputs):
    '''
    ==========================================================================
    EV_block(model, l_t, l_Mev, l_bus, AllInputs)
    ==========================================================================
    Defines all EV-related parameters, variables, and constraints.
    Supports Vehicle-to-Grid (V2G): charging (+) and discharging (−).

    MAIN IDEAS:
      - EVs can both charge (consume power) and discharge (inject to grid)
      - The net power EV_P = EV_Pch − EV_Pdis replaces old EV_P
      - All other constraints (power balance, economics) stay valid
    ==========================================================================

    Inputs:
        model        : main Pyomo model
        l_t          : list of timesteps
        l_Mev        : list of EV IDs (smart charging ones)
        l_bus        : list of network bus IDs
        AllInputs    : full data structure with EV, grid, and system info

    Outputs (to the optimization model):
        EV_Pch[Mev,t]       : EV charging power decision variable [kW]
        EV_Pdis[Mev,t]      : EV discharging power decision variable [kW]
        EV_P[Mev,t]         : Expression (net power = charge − discharge)
        EV_flexibility_cost : cost if deviating from baseline profile [€]
    ==========================================================================

    '''

    ##### ────────────────────────────── PARAMETERS ────────────────────────────── #####

    # If there are EVs defined by the user
    if AllInputs.EV.hay == 1:
        if AllInputs.EV.immediate0_smart1 == 0:
            # Immediate charging = fixed load
            model.EV_D = pyo.Param(
                model.i_bus, model.t, within=pyo.NonNegativeReals,
                initialize=AllInputs.Load.Pd_EV_total
            )
        else:
            # Smart charging = flexible (optimizable)
            # Initialize empty critical load (none, since it's flexible)
            model.EV_D = pyo.Param(
                model.i_bus, model.t, within=pyo.NonNegativeReals,
                initialize={(i_bus, t): 0 for t in l_t for i_bus in l_bus}
            )

            # Maximum charge power per EV [kW]
            model.EV_Pmax = pyo.Param(model.Mev,
                                      initialize=AllInputs.EV.smart.Pmax_evMev, within=pyo.NonNegativeReals)

            # NEW: Maximum discharge power per EV [kW]
            # if not provided, we assume equal to charge power
            Pdismax_dict = getattr(AllInputs.EV.smart, "Pdismax_evMev", None)
            if Pdismax_dict is None:
                Pdismax_dict = AllInputs.EV.smart.Pmax_evMev
            model.EV_Pdismax = pyo.Param(model.Mev,
                                         initialize=Pdismax_dict, within=pyo.NonNegativeReals)

            # Station limit (shared converter rating)
            model.EV_P_station = pyo.Param(
                initialize=AllInputs.EV.smart.P_estacion, within=pyo.NonNegativeReals)

            # Total required net charged energy per EV [kWh]
            model.EV_E = pyo.Param(model.Mev,
                                   initialize=AllInputs.EV.smart.E_evMev, within=pyo.NonNegativeReals)

            # Availability (1 = connected, 0 = not connected)
            model.EV_t_availability = pyo.Param(model.Mev, model.t,
                                                initialize=AllInputs.EV.smart.K_evMev_t, within=pyo.Binary)

            # Baseline charging profile (for flexibility comparison)
            model.EV_Pbaseline = pyo.Param(model.Mev, model.t,
                                           initialize=AllInputs.EV.smart.Pbaseline_evMev_t,
                                           within=pyo.NonNegativeReals)

            # Flexibility price (€/EV per deviation)
            model.EV_flexibility_price = pyo.Param(model.Mev,
                                                   initialize=AllInputs.EV.smart.Cost_evMev,
                                                   within=pyo.NonNegativeReals)

            # Charging/discharging efficiencies
            eta_ch = getattr(AllInputs.EV.smart, "eta_ch", 0.95)
            eta_dis = getattr(AllInputs.EV.smart, "eta_dis", 0.95)
            model.EV_eta_ch = pyo.Param(initialize=eta_ch, within=pyo.PercentFraction)
            model.EV_eta_dis = pyo.Param(initialize=eta_dis, within=pyo.PercentFraction)

    else:
        # No EVs at all
        model.EV_D = pyo.Param(
            model.i_bus, model.t, within=pyo.NonNegativeReals,
            initialize={(i_bus, t): 0 for t in l_t for i_bus in l_bus}
        )

    # Binary mapping of which bus each EV is connected to
    model.EV_pos_bus = pyo.Param(
        model.i_bus, initialize=AllInputs.EV.pos_bus, within=pyo.Binary)

    ##### ────────────────────────────── VARIABLES ────────────────────────────── #####

    if AllInputs.EV.hay == 1 and AllInputs.EV.immediate0_smart1 == 1:
        # Charging and discharging decision variables (kW)
        model.EV_Pch = pyo.Var(model.Mev, model.t, within=pyo.NonNegativeReals)
        model.EV_Pdis = pyo.Var(model.Mev, model.t, within=pyo.NonNegativeReals)

        # Net EV power variable (positive = charging, negative = discharging)
        model.EV_P = pyo.Var(model.Mev, model.t, within=pyo.Reals)

        # Constraint linking charge and discharge to net power
        def ev_power_balance(m, Mev, t):
            return m.EV_P[Mev, t] == m.EV_Pch[Mev, t] - m.EV_Pdis[Mev, t]

        model.EV_power_balance = pyo.Constraint(model.Mev, model.t, rule=ev_power_balance)

        # Cost-related variables
        model.EV_flexibility_cost = pyo.Var(model.Mev, within=pyo.NonNegativeReals)
        model.EV_is_baseline = pyo.Var(model.Mev, within=pyo.Binary)

    else:
        # No smart EVs, set constants to zero
        model.EV_P = pyo.Param(model.Mev, model.t, within=pyo.Reals,
                               initialize={(Mev, t): 0.0 for Mev in l_Mev for t in l_t})
        model.EV_flexibility_cost = pyo.Param(model.Mev, within=pyo.NonNegativeReals,
                                              initialize={Mev: 0.0 for Mev in l_Mev})

    ##### ────────────────────────────── CONSTRAINTS ────────────────────────────── #####

    if AllInputs.EV.hay == 1 and AllInputs.EV.immediate0_smart1 == 1:
        # (1) Power limits
        def EV_Pch_limit(m, Mev, t):
            return m.EV_Pch[Mev, t] <= m.EV_t_availability[Mev, t] * m.EV_Pmax[Mev]

        def EV_Pdis_limit(m, Mev, t):
            return m.EV_Pdis[Mev, t] <= m.EV_t_availability[Mev, t] * m.EV_Pdismax[Mev]

        model.Constr_EV_Pch_limit = pyo.Constraint(model.Mev, model.t, rule=EV_Pch_limit)
        model.Constr_EV_Pdis_limit = pyo.Constraint(model.Mev, model.t, rule=EV_Pdis_limit)

        # (2) Station limit — total power flow cannot exceed station capacity
        def EV_station_limit(m, t):
            return sum(m.EV_Pch[Mev, t] + m.EV_Pdis[Mev, t] for Mev in l_Mev) <= m.EV_P_station

        model.Constr_EV_station_limit = pyo.Constraint(model.t, rule=EV_station_limit)

        # (3) Energy balance over horizon
        # Ensures that, accounting for efficiencies, the net charged energy equals EV_E
        def EV_energy_rule(m, Mev):
            return sum(m.EV_eta_ch * m.EV_Pch[Mev, t]
                       - (1.0 / m.EV_eta_dis) * m.EV_Pdis[Mev, t]
                       for t in l_t) * m.inc_t == m.EV_E[Mev]

        model.Constr_EV_energy = pyo.Constraint(model.Mev, rule=EV_energy_rule)

        # (4) Baseline comparison constraints (Big-M)
        BIGM = 1e6

        def EV_is_baseline_1(m, Mev, t):
            return -BIGM * (1 - m.EV_is_baseline[Mev]) <= (m.EV_Pch[Mev, t] - m.EV_Pdis[Mev, t]) - m.EV_Pbaseline[
                Mev, t]

        def EV_is_baseline_2(m, Mev, t):
            return (m.EV_Pch[Mev, t] - m.EV_Pdis[Mev, t]) - m.EV_Pbaseline[Mev, t] <= BIGM * (1 - m.EV_is_baseline[Mev])

        model.Constr_EV_is_baseline_1 = pyo.Constraint(model.Mev, model.t, rule=EV_is_baseline_1)
        model.Constr_EV_is_baseline_2 = pyo.Constraint(model.Mev, model.t, rule=EV_is_baseline_2)

        # (5) Flexibility cost constraint
        def EV_flex_cost_rule(m, Mev):
            return m.EV_flexibility_cost[Mev] == (1 - m.EV_is_baseline[Mev]) * m.EV_flexibility_price[Mev]

        model.Constr_EV_flex_cost = pyo.Constraint(model.Mev, rule=EV_flex_cost_rule)

        model.EV_mode = pyo.Var(model.Mev, model.t, within=pyo.Binary)

        def no_simul_charge(m, Mev, t):
            return m.EV_Pch[Mev, t] <= m.EV_Pmax[Mev] * m.EV_mode[Mev, t]

        def no_simul_discharge(m, Mev, t):
            return m.EV_Pdis[Mev, t] <= m.EV_Pdismax[Mev] * (1 - m.EV_mode[Mev, t])

        model.Constr_no_simul_charge = pyo.Constraint(model.Mev, model.t, rule=no_simul_charge)
        model.Constr_no_simul_discharge = pyo.Constraint(model.Mev, model.t, rule=no_simul_discharge)

        def EV_energy_neutrality(m, Mev):
            # 0.95: charging efficiency, 0.95: discharging efficiency
            return sum(m.EV_Pch[Mev, t] * 0.95 for t in m.t) * m.inc_t >= \
                sum(m.EV_Pdis[Mev, t] / 0.95 for t in m.t) * m.inc_t

        model.Constr_EV_energy_neutrality = pyo.Constraint(model.Mev, rule=EV_energy_neutrality)


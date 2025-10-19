import pyomo.environ as pyo
import math

def ACPowerFlow_iplug(model, l_t, l_bus, AllInputs):  # data, init_data):

    ##### Model of the system network ##### -->

    ## Sets ##

    ## Parameters ##
    model.G_bus = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.LinesGlobal.G_bus, within=pyo.Reals)  # real part of the y_bus matrix [pu]
    model.B_bus = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.LinesGlobal.B_bus, within=pyo.Reals)  # imaginary part of the y_bus matrix [pu]
    model.bus_is_slack = pyo.Param(model.i_bus, initialize=AllInputs.Buses.slack, within=pyo.Binary)  # binary that indicates if the bus is a slack (1) or not (0)
    model.bus_type = pyo.Param(model.i_bus, initialize=AllInputs.Buses.type, within=pyo.Any)  # string that indicates the bus type (AC or DC)
    model.Vmin = pyo.Param(model.i_bus, initialize=AllInputs.Buses.Vmin, within=pyo.NonNegativeReals)  # minimum voltage of the bus [pu]
    model.Vmax = pyo.Param(model.i_bus, initialize=AllInputs.Buses.Vmax, within=pyo.NonNegativeReals)  # maximum voltage of the bus [pu]
    model.Zmod = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.LinesGlobal.Zmod, within=pyo.Reals)  # impedance modul matrix of the system [pu]
    model.Zphase = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.LinesGlobal.Zphase, within=pyo.Reals)  # impedance phase matrix of the system [pu]
    model.Ymod = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.LinesGlobal.Ymod, within=pyo.Reals)  # admitance modul matrix of the system [pu]
    model.Yphase = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.LinesGlobal.Yphase, within=pyo.Reals)  # admitance phase matrix of the system [pu]
    model.i_max = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.LinesGlobal.i_max, within=pyo.NonNegativeReals)  # maximum current flowing through the line [pu]
    # block.Sline_max = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.LinesGlobal.Pmax, within=pyo.NonNegativeReals)  # maximum power flowing through the line [pu]

    ## Variables ##
    model.V = pyo.Var(model.i_bus, model.t, within=pyo.NonNegativeReals, initialize={(bus, t): 0.98 for bus in l_bus for t in l_t})  # voltage magnitude of each bus at each time [pu]
    model.thetaV = pyo.Var(model.i_bus, model.t, within=pyo.Reals, bounds=(-2 * math.pi, 2 * math.pi), initialize={(bus, t): 0 for bus in l_bus for t in l_t})  # voltage angle of each bus at each time [rad]
    model.Qinj = pyo.Var(model.i_bus, model.t, within=pyo.Reals, initialize={(bus, t): 0 for bus in l_bus for t in l_t})  # total reactive power injected to each bus at each time [pu]
    model.i_line_squared = pyo.Var(model.i_bus, model.i_bus, model.t, within=pyo.Reals, initialize={(bus1, bus2, t): 0 for bus1 in l_bus for bus2 in l_bus for t in l_t})  # current between two buses at each time [pu]
    # block.S_line_squared = pyo.Var(model.i_bus, model.i_bus, model.t, within=pyo.Reals)  # power between two buses at each time [pu]


    ## Constraints ##
    def min_V(m, bus, t):
        return m.Vmin[bus] <= m.V[bus, t]
    model.Constr_min_V = pyo.Constraint(model.i_bus, model.t, rule=min_V)
    def max_V(m, bus, t):
        return m.V[bus, t] <= m.Vmax[bus]
    model.Constr_max_V = pyo.Constraint(model.i_bus, model.t, rule=max_V)
    def V_slack(m, bus, t):
        if m.bus_is_slack[bus] == 1:  # the bus is a slack
            return m.V[bus, t] == 1
        else:  # the bus is not a slack
            return pyo.Constraint.Skip
    model.Constr_V_slack = pyo.Constraint(model.i_bus, model.t, rule=V_slack)
    def thetaV_slack(m, bus, t):
        if m.bus_is_slack[bus] == 1:  # the bus is a slack
            return m.thetaV[bus, t] == 0
        else:  # the bus is not a slack
            return pyo.Constraint.Skip
    model.Constr_thetaV_slack = pyo.Constraint(model.i_bus, model.t, rule=thetaV_slack)
    def AC_PowerFlow_P(m, bus, t):
        # if m.bus_is_slack[bus] != 1:  # the bus is not a slack
        return m.Pinj[bus,t] == m.V[bus, t] * sum(m.V[bus_aux, t] * (m.G_bus[bus, bus_aux] * pyo.cos(m.thetaV[bus, t] - m.thetaV[bus_aux, t])
                                                              + m.B_bus[bus, bus_aux] * pyo.sin(m.thetaV[bus, t] - m.thetaV[bus_aux, t])) for bus_aux in l_bus)
        # else:
        #     return pyo.Constraint.Skip
    model.Constr_AC_PowerFlow_P = pyo.Constraint(model.i_bus, model.t, rule=AC_PowerFlow_P)
    def AC_PowerFlow_Q(m, bus, t):
        # if m.bus_is_slack[bus] != 1:  # the bus is not a slack
        return m.Qinj[bus,t] == m.V[bus, t] * sum(m.V[bus_aux, t] * (m.G_bus[bus, bus_aux] * pyo.sin(m.thetaV[bus, t] - m.thetaV[bus_aux, t])
                                                              - m.B_bus[bus, bus_aux] * pyo.cos(m.thetaV[bus, t] - m.thetaV[bus_aux, t])) for bus_aux in l_bus)
        # else:
        #     return pyo.Constraint.Skip
    model.Constr_AC_PowerFlow_Q = pyo.Constraint(model.i_bus, model.t, rule=AC_PowerFlow_Q)
    def DC_PowerFlow_P(m, bus, t):
        return m.Pinj[bus, t] == sum(m.B_bus[bus, bus_aux] * m.thetaV[bus_aux, t] for bus_aux in l_bus)
    # block.Constr_DC_PowerFlow_P = pyo.Constraint(model.i_bus, model.t, rule=DC_PowerFlow_P)
    def i_line_squared_calc(m, bus1, bus2, t):
        if m.Zmod[bus1, bus2] != 0:
            return m.i_line_squared[bus1, bus2, t] == \
                (m.V[bus1, t] ** 2 + m.V[bus2, t] ** 2 - 2 * m.V[bus1, t] * m.V[bus2, t] * pyo.cos(m.thetaV[bus2, t] - m.thetaV[bus1, t])) / m.Zmod[bus1, bus2] ** 2 \
                + (m.Ymod[bus1, bus2] * m.V[bus1, t] ** 2 * pyo.cos(m.Zphase[bus1, bus2] + m.Yphase[bus1, bus2])) / m.Zmod[bus1, bus2] \
                - (m.Ymod[bus1, bus2] * m.V[bus1, t] * m.V[bus2, t] * pyo.cos(m.Yphase[bus1, bus2] + m.thetaV[bus1, t] + m.Zphase[bus1, bus2] - m.thetaV[bus2, t])) / m.Zmod[bus1, bus2] \
                + (m.Ymod[bus1, bus2] ** 2 * m.V[bus1, t] ** 2) / 4
        else:
            return pyo.Constraint.Skip
    model.Constr_i_line_squared_calc = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=i_line_squared_calc)
    def max_i_line(m, bus1, bus2, t):
        if m.Zmod[bus1, bus2] != 0:
            return m.i_line_squared[bus1, bus2, t] <= m.i_max[bus1, bus2] ** 2
        else:
            return pyo.Constraint.Skip
    model.Constr_max_i_line = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=max_i_line)
    def S_line_squared_calc(m, bus1, bus2, t):
        if m.Zmod[bus1, bus2] != 0:
            return m.S_line_squared[bus1, bus2, t] <= m.V[bus1, t]**2 * m.i_line_squared[bus1, bus2, t]
        else:
            return pyo.Constraint.Skip
    # block.Constr_S_line_squared_calc = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=S_line_squared_calc)
    def max_S_line(m, bus1, bus2, t):
        if m.Zmod[bus1, bus2] != 0:
            return m.S_line_squared[bus1, bus2, t] <= m.Sline_max[bus1, bus2]**2
        else:
            return pyo.Constraint.Skip
    # block.Constr_max_S_line = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=max_S_line)


def ACPowerFlow(model, l_t, l_bus, AllInputs):  # data, init_data):

    ##### Model of the system network ##### -->

    ## Sets ##

    ## Parameters ##
    # model.bus_type = pyo.Param(model.i_bus, initialize=AllInputs.Network.Buses.type, within=pyo.Any)  # string that indicates the bus type (AC or DC)
    model.G_bus = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.Network.Lines.G_bus, within=pyo.Reals)  # real part of the y_bus matrix [pu]
    model.B_bus = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.Network.Lines.B_bus, within=pyo.Reals)  # imaginary part of the y_bus matrix [pu]
    model.Vmin = pyo.Param(model.i_bus, initialize=AllInputs.Network.Buses.Vmin, within=pyo.NonNegativeReals)  # minimum voltage of the bus [pu]
    model.Vmax = pyo.Param(model.i_bus, initialize=AllInputs.Network.Buses.Vmax, within=pyo.NonNegativeReals)  # maximum voltage of the bus [pu]

    ## Variables ##
    model.Vreal = pyo.Var(model.i_bus, model.t, within=pyo.Reals, bounds=(-2, 2), initialize={(bus, t): 0 for bus in l_bus for t in l_t})  # real part of the voltagee phasor [pu]
    model.Vimag = pyo.Var(model.i_bus, model.t, within=pyo.Reals, bounds=(-2, 2), initialize={(bus, t): 0 for bus in l_bus for t in l_t})  # imaginary part of the voltagee phasor [pu]
    #
    model.c = pyo.Var(model.i_bus, model.i_bus, model.t, within=pyo.Reals,
                      initialize={(bus1, bus2, t): 0 for bus1 in l_bus for bus2 in l_bus for t in l_t})  # c[bus1, bus2, t] = m.Vreal[bus1, t] * m.Vreal[bus2, t] + m.Vimag[bus1, t] * m.Vimag[bus2, t]
    model.s = pyo.Var(model.i_bus, model.i_bus, model.t, within=pyo.Reals,
                      initialize={(bus1, bus2, t): 0 for bus1 in l_bus for bus2 in l_bus for t in l_t})  # s[bus1, bus2, t] = m.Vimag[bus1, t] * m.Vreal[bus2, t] - m.Vreal[bus1, t] * m.Vimag[bus2, t]
    #
    model.Pline = pyo.Var(model.i_bus, model.i_bus, model.t, within=pyo.Reals, initialize={(bus1, bus2, t): 0 for bus1 in l_bus for bus2 in l_bus for t in l_t})  # active power flowing between two buses at each time [pu]
    model.Qline = pyo.Var(model.i_bus, model.i_bus, model.t, within=pyo.Reals, initialize={(bus1, bus2, t): 0 for bus1 in l_bus for bus2 in l_bus for t in l_t})  # reactive power flowing between two buses at each time [pu]



    ## Constraints ##
    def Vreal_slack(m, bus, t):
        if m.bus_is_slack[bus] == 1:  # the bus is a slack
            return m.Vreal[bus, t] == 1
        else:  # the bus is not a slack
            return pyo.Constraint.Skip
    model.Constr_Vreal_slack = pyo.Constraint(model.i_bus, model.t, rule=Vreal_slack)
    def Vimag_slack(m, bus, t):
        if m.bus_is_slack[bus] == 1:  # the bus is a slack
            return m.Vimag[bus, t] == 0
        else:  # the bus is not a slack
            return pyo.Constraint.Skip
    model.Constr_Vimag_slack = pyo.Constraint(model.i_bus, model.t, rule=Vimag_slack)

    def Constraint_AC_PF_Pinj(m, i_bus, t):
        return m.Pinj[i_bus,t] == sum(m.Pline[i_bus, bus_aux, t] for bus_aux in l_bus)
    model.Constr_AC_PF_Pinj = pyo.Constraint(model.i_bus, model.t, rule=Constraint_AC_PF_Pinj)
    def Constraint_AC_PF_Qinj(m, i_bus, t):
        return m.Qinj[i_bus,t] == sum(m.Qline[i_bus, bus_aux, t] for bus_aux in l_bus)
    model.Constr_AC_PF_Qinj = pyo.Constraint(model.i_bus, model.t, rule=Constraint_AC_PF_Qinj)

    # AC Power Flow
    # def AC_PowerFlow_Pline(m, i_bus1, i_bus2, t):
    #     return m.Pline[i_bus1, i_bus2, t] == m.G_bus[i_bus1, i_bus2] * (m.Vreal[i_bus1, t] * m.Vreal[i_bus2, t] + m.Vimag[i_bus1, t] * m.Vimag[i_bus2, t])\
    #         + m.B_bus[i_bus1, i_bus2] * (m.Vimag[i_bus1, t] * m.Vreal[i_bus2, t] - m.Vreal[i_bus1, t] * m.Vimag[i_bus2, t])
    # model.Constr_AC_PowerFlow_Pline = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=AC_PowerFlow_Pline)
    # def AC_PowerFlow_Qline(m, i_bus1, i_bus2, t):
    #     return m.Qline[i_bus1, i_bus2, t] == m.G_bus[i_bus1, i_bus2] * (m.Vimag[i_bus1, t] * m.Vreal[i_bus2, t] - m.Vreal[i_bus1, t] * m.Vimag[i_bus2, t])\
    #         - m.B_bus[i_bus1, i_bus2] * (m.Vreal[i_bus1, t] * m.Vreal[i_bus2, t] + m.Vimag[i_bus1, t] * m.Vimag[i_bus2, t])
    # model.Constr_AC_PowerFlow_Qline = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=AC_PowerFlow_Qline)

    def AC_PowerFlow_Pline(m, i_bus1, i_bus2, t):
        return m.Pline[i_bus1, i_bus2, t] == m.G_bus[i_bus1, i_bus2] * (m.c[i_bus1, i_bus2, t]-m.c[i_bus1, i_bus1, t]) + m.B_bus[i_bus1, i_bus2] * m.s[i_bus1, i_bus2, t]
    model.Constr_AC_PowerFlow_Pline = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=AC_PowerFlow_Pline)
    def AC_PowerFlow_Qline(m, i_bus1, i_bus2, t):
        return m.Qline[i_bus1, i_bus2, t] == m.G_bus[i_bus1, i_bus2] * m.s[i_bus1, i_bus2, t]- m.B_bus[i_bus1, i_bus2] * (m.c[i_bus1, i_bus2, t]-m.c[i_bus1, i_bus1, t])
    model.Constr_AC_PowerFlow_Qline = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=AC_PowerFlow_Qline)
    def AC_PowerFlow_c_def(m, i_bus1, i_bus2, t):
        return m.c[i_bus1, i_bus2, t] == m.Vreal[i_bus1, t] * m.Vreal[i_bus2, t] + m.Vimag[i_bus1, t] * m.Vimag[i_bus2, t]
    model.Constr_AC_PowerFlow_c_def = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=AC_PowerFlow_c_def)
    def AC_PowerFlow_s_def(m, i_bus1, i_bus2, t):
        return m.s[i_bus1, i_bus2, t] == m.Vreal[i_bus2, t] * m.Vimag[i_bus1, t] - m.Vreal[i_bus1, t] * m.Vimag[i_bus2, t]
    model.Constr_AC_PowerFlow_s_def = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=AC_PowerFlow_s_def)

    '''
    + V upper and lower limits
    + Pline limits
    '''

    # V limit
    def min_V(m, i_bus, t):
        return m.Vmin[i_bus]**2 <= m.c[i_bus, i_bus, t] # m.V[i_bus, t]
    model.Constr_min_V = pyo.Constraint(model.i_bus, model.t, rule=min_V)
    def max_V(m, i_bus, t):
        return m.c[i_bus, i_bus, t] <= m.Vmax[i_bus]**2
    model.Constr_max_V = pyo.Constraint(model.i_bus, model.t, rule=max_V)
    # i limit
    '''
    Iik = (Vi-Vk)/Zik - Vi*yik/2
    Sik = Vi * Iik_conj --> mod(Sik) = mod(Vi) * mod(Iik) --> Sik**2 = Vi**2 * Iik**2 --> Pik**2 + Qik**2 = cii * Iik**2
    '''
    model.i_max = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.Network.Lines.i_max, within=pyo.NonNegativeReals)  # maximum current flowing through the line [pu]
    model.i_line_squared = pyo.Var(model.i_bus, model.i_bus, model.t, within=pyo.Reals, initialize={(bus1, bus2, t): 0 for bus1 in l_bus for bus2 in l_bus for t in l_t})  # current between two buses at each time [pu]
    def AC_PowerFlow_i_line_squared(m, i_bus1, i_bus2, t):
        return m.Pline[i_bus1, i_bus2, t]**2 + m.Qline[i_bus1, i_bus2, t]**2 == m.c[i_bus1, i_bus1, t] * m.i_line_squared[i_bus1, i_bus2, t]
    model.Constr_AC_PowerFlow_i_line_squared = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=AC_PowerFlow_i_line_squared)
    def AC_PowerFlow_max_i_line(m, i_bus1, i_bus2, t):
        if m.G_bus[i_bus1, i_bus2] != 0 and i_bus1 != i_bus2:
            return m.i_line_squared[i_bus1, i_bus2, t] <= m.i_max[i_bus1, i_bus2]**2
        else:
            return pyo.Constraint.Skip
    # model.Constr_AC_PowerFlow_max_i_line = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=AC_PowerFlow_max_i_line)



def SOCPACPowerFlow(model, l_t, l_bus, AllInputs):  # data, init_data):

    ##### Model of the system network ##### -->

    ## Sets ##

    ## Parameters ##
    # model.bus_type = pyo.Param(model.i_bus, initialize=AllInputs.Network.Buses.type, within=pyo.Any)  # string that indicates the bus type (AC or DC)
    model.G_bus = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.Network.Lines.G_bus, within=pyo.Reals)  # real part of the y_bus matrix [pu]
    model.B_bus = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.Network.Lines.B_bus, within=pyo.Reals)  # imaginary part of the y_bus matrix [pu]
    model.Vmin = pyo.Param(model.i_bus, initialize=AllInputs.Network.Buses.Vmin, within=pyo.NonNegativeReals)  # minimum voltage of the bus [pu]
    model.Vmax = pyo.Param(model.i_bus, initialize=AllInputs.Network.Buses.Vmax, within=pyo.NonNegativeReals)  # maximum voltage of the bus [pu]

    ## Variables ##
    model.c = pyo.Var(model.i_bus, model.i_bus, model.t, within=pyo.Reals,
                      initialize={(bus1, bus2, t): 0 for bus1 in l_bus for bus2 in l_bus for t in l_t})  # c[bus1, bus2, t] = m.Vreal[bus1, t] * m.Vreal[bus2, t] + m.Vimag[bus1, t] * m.Vimag[bus2, t]
    model.s = pyo.Var(model.i_bus, model.i_bus, model.t, within=pyo.Reals,
                      initialize={(bus1, bus2, t): 0 for bus1 in l_bus for bus2 in l_bus for t in l_t})  # s[bus1, bus2, t] = m.Vimag[bus1, t] * m.Vreal[bus2, t] - m.Vreal[bus1, t] * m.Vimag[bus2, t]
    #
    model.Pline = pyo.Var(model.i_bus, model.i_bus, model.t, within=pyo.Reals, initialize={(bus1, bus2, t): 0 for bus1 in l_bus for bus2 in l_bus for t in l_t})  # active power flowing between two buses at each time [pu]
    model.Qline = pyo.Var(model.i_bus, model.i_bus, model.t, within=pyo.Reals, initialize={(bus1, bus2, t): 0 for bus1 in l_bus for bus2 in l_bus for t in l_t})  # reactive power flowing between two buses at each time [pu]



    ## Constraints ##
    def Constraint_AC_PF_Pinj(m, i_bus, t):
        return m.Pinj[i_bus,t] == sum(m.Pline[i_bus, bus_aux, t] for bus_aux in l_bus)
    model.Constr_AC_PF_Pinj = pyo.Constraint(model.i_bus, model.t, rule=Constraint_AC_PF_Pinj)
    def Constraint_AC_PF_Qinj(m, i_bus, t):
        return m.Qinj[i_bus,t] == sum(m.Qline[i_bus, bus_aux, t] for bus_aux in l_bus)
    model.Constr_AC_PF_Qinj = pyo.Constraint(model.i_bus, model.t, rule=Constraint_AC_PF_Qinj)

    # SOCP AC Power Flow
    def SOCP_AC_PowerFlow_Pline(m, i_bus1, i_bus2, t):
        # return m.Pline[i_bus1, i_bus2, t] == m.G_bus[i_bus1, i_bus2] * m.c[i_bus1, i_bus2, t] + m.B_bus[i_bus1, i_bus2] * m.s[i_bus1, i_bus2, t]
        return m.Pline[i_bus1, i_bus2, t] == m.G_bus[i_bus1, i_bus2] * (m.c[i_bus1, i_bus2, t]-m.c[i_bus1, i_bus1, t]) + m.B_bus[i_bus1, i_bus2] * m.s[i_bus1, i_bus2, t]
    model.Constr_SOCP_AC_PowerFlow_Pline = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=SOCP_AC_PowerFlow_Pline)
    def SOCP_AC_PowerFlow_Qline(m, i_bus1, i_bus2, t):
        # return m.Qline[i_bus1, i_bus2, t] == m.G_bus[i_bus1, i_bus2] * m.s[i_bus1, i_bus2, t]- m.B_bus[i_bus1, i_bus2] * m.c[i_bus1, i_bus2, t]
        return m.Qline[i_bus1, i_bus2, t] == m.G_bus[i_bus1, i_bus2] * m.s[i_bus1, i_bus2, t] - m.B_bus[i_bus1, i_bus2] * (m.c[i_bus1, i_bus2, t]-m.c[i_bus1, i_bus1, t])
    model.Constr_SOCP_AC_PowerFlow_Qline = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=SOCP_AC_PowerFlow_Qline)
    def SOCP_AC_PowerFlow_c(m, i_bus1, i_bus2, t):
        return m.c[i_bus1, i_bus2, t] == m.c[i_bus2, i_bus1, t]
    model.Constr_SOCP_AC_PowerFlow_c = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=SOCP_AC_PowerFlow_c)
    def SOCP_AC_PowerFlow_s(m, i_bus1, i_bus2, t):
        return m.s[i_bus1, i_bus2, t] == - m.s[i_bus2, i_bus1, t]
    model.Constr_SOCP_AC_PowerFlow_s = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=SOCP_AC_PowerFlow_s)
    def SOCP_AC_PowerFlow_cs(m, i_bus1, i_bus2, t):
        return m.c[i_bus1, i_bus2, t] ** 2 + m.s[i_bus1, i_bus2, t] ** 2 == m.c[i_bus1, i_bus1, t] * m.c[i_bus2, i_bus2, t]
    model.Constr_SOCP_AC_PowerFlow_cs = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=SOCP_AC_PowerFlow_cs)

    def c_slack(m, i_bus, t):
        if m.bus_is_slack[i_bus] == 1:  # the bus is a slack
            return m.c[i_bus, i_bus, t] == 1
        else:  # the bus is not a slack
            return m.c[i_bus, i_bus, t] >= 0  # V**2
    model.Constr_c_slack = pyo.Constraint(model.i_bus, model.t, rule=c_slack)

    # Exact AC Power Flow
    # m.c[i_bus1, i_bus2, t] == m.Vreal[i_bus1, t] * m.Vreal[i_bus2, t] + m.Vimag[i_bus1, t] * m.Vimag[i_bus2, t]
    # m.s[i_bus1, i_bus2, t] == m.Vreal[i_bus2, t] * m.Vimag[i_bus1, t] - m.Vreal[i_bus1, t] * m.Vimag[i_bus2, t]

    # V limit
    def min_V(m, i_bus, t):
        return m.Vmin[i_bus]**2 <= m.c[i_bus, i_bus, t] # m.V[i_bus, t]
    # model.Constr_min_V = pyo.Constraint(model.i_bus, model.t, rule=min_V)
    def max_V(m, i_bus, t):
        return m.c[i_bus, i_bus, t] <= m.Vmax[i_bus]**2
    # model.Constr_max_V = pyo.Constraint(model.i_bus, model.t, rule=max_V)

    # i limit
    ''' Iik = (Vi-Vk)/Zik - Vi*yik/2
    Sik = Vi * Iik_conj --> mod(Sik) = mod(Vi) * mod(Iik) --> Sik**2 = Vi**2 * Iik**2 --> Pik**2 + Qik**2 = cii * Iik**2'''
    model.i_max = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.Network.Lines.i_max, within=pyo.NonNegativeReals)  # maximum current flowing through the line [pu]
    # model.i_line_squared = pyo.Var(model.i_bus, model.i_bus, model.t, within=pyo.Reals, initialize={(bus1, bus2, t): 0 for bus1 in l_bus for bus2 in l_bus for t in l_t})  # current between two buses at each time [pu]
    def SOCP_AC_PowerFlow_i_line_squared(m, i_bus1, i_bus2, t):
        return m.Pline[i_bus1, i_bus2, t]**2 + m.Qline[i_bus1, i_bus2, t]**2 == m.c[i_bus1, i_bus1, t] * m.i_line_squared[i_bus1, i_bus2, t]
    # model.Constr_SOCP_AC_PowerFlow_i_line_squared = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=SOCP_AC_PowerFlow_i_line_squared)
    def SOCP_AC_PowerFlow_max_i_line(m, i_bus1, i_bus2, t):
        if m.G_bus[i_bus1, i_bus2] != 0 and i_bus1 != i_bus2:
            return m.i_line_squared[i_bus1, i_bus2, t] <= m.i_max[i_bus1, i_bus2]**2
        else:
            return pyo.Constraint.Skip
    # model.Constr_SOCP_AC_PowerFlow_max_i_line = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=SOCP_AC_PowerFlow_max_i_line)


def DCPowerFlow(model, l_t, l_bus, AllInputs):  # data, init_data):

    ##### Model of the system network ##### -->

    ## Sets ##

    ## Parameters ##
    # model.bus_type = pyo.Param(model.i_bus, initialize=AllInputs.Network.Buses.type, within=pyo.Any)  # string that indicates the bus type (AC or DC)
    model.B_bus = pyo.Param(model.i_bus, model.i_bus, initialize=AllInputs.Network.Lines.B_bus, within=pyo.Reals)  # imaginary part of the y_bus matrix [pu]
    model.Pmax = pyo.Param(model.i_bus, model.i_bus, within=pyo.Reals, initialize=AllInputs.Network.Lines.Pmax)  # maximum power flow through each line [pu]


    ## Variables ##
    model.thetaV = pyo.Var(model.i_bus, model.t, within=pyo.Reals, bounds=(-2 * math.pi, 2 * math.pi), initialize={(bus, t): 0 for bus in l_bus for t in l_t})  # voltage angle of each bus at each time [rad]
    model.Pline = pyo.Var(model.i_bus, model.i_bus, model.t, within=pyo.Reals, initialize={(bus1, bus2, t): 0 for bus1 in l_bus for bus2 in l_bus for t in l_t})  # power flowing between two buses at each time [pu]


    ## Constraints ##
    
    def thetaV_slack(m, i_bus, t):
        if m.bus_is_slack[i_bus] == 1:  # the bus is a slack
            return m.thetaV[i_bus, t] == 0
        else:  # the bus is not a slack
            return pyo.Constraint.Skip
    model.Constr_thetaV_slack = pyo.Constraint(model.i_bus, model.t, rule=thetaV_slack)

    def Constraint_DC_PF_Pinj(m, i_bus, t):
        return m.Pinj[i_bus,t] == sum(m.Pline[i_bus, bus_aux, t] for bus_aux in l_bus)  #sum(m.B_bus[i_bus, bus_aux] * (m.thetaV[i_bus, t] - m.thetaV[bus_aux, t]) for bus_aux in l_bus)
    model.Constr_DC_PF_Pinj = pyo.Constraint(model.i_bus, model.t, rule=Constraint_DC_PF_Pinj)
    def Constraint_DC_PF_Pline(m, i_bus1, i_bus2, t):
        return m.Pline[i_bus1, i_bus2, t] == m.B_bus[i_bus1, i_bus2] * (m.thetaV[i_bus1, t] - m.thetaV[i_bus2, t])
    model.Constr_DC_PF_Pline = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=Constraint_DC_PF_Pline)

    def Constraint_Pmax_line1(m, i_bus1, i_bus2, t):
        return m.Pline[i_bus1, i_bus2, t] <= m.Pmax[i_bus1, i_bus2]
    model.Constr_Pmax_line1 = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=Constraint_Pmax_line1)
    def Constraint_Pmax_line2(m, i_bus1, i_bus2, t):
        return -m.Pline[i_bus1, i_bus2, t] <= m.Pmax[i_bus1, i_bus2]
    model.Constr_Pmax_line2 = pyo.Constraint(model.i_bus, model.i_bus, model.t, rule=Constraint_Pmax_line2)


def PowerFlow(model, l_t, l_bus, AllInputs):

    ##### Model of the system network ##### --> [pu]
    PF_type = AllInputs.Network.PF_type  # economic_dispatch / DC-OPF

    ## Sets ##

    ## Parameters ##
    model.Sb = pyo.Param(initialize=AllInputs.Network.Sb)  # S_base = 100 MVA --> PF in [pu]
    model.bus_is_slack = pyo.Param(model.i_bus, initialize=AllInputs.Network.Buses.slack, within=pyo.Binary)  # binary that indicates if the bus is a slack (1) or not (0)


    ## Variables ##
    model.Pinj = pyo.Var(model.i_bus, model.t, within=pyo.Reals, initialize={(bus, t): 0 for bus in l_bus for t in l_t})  # total active power injected to each node at each time [pu]
    model.Qinj = pyo.Var(model.i_bus, model.t, within=pyo.Reals, initialize={(bus, t): 0 for bus in l_bus for t in l_t})  # total reactive power injected to each node at each time [pu]
    #
    model.Q_buy = pyo.Var(model.t, within=pyo.Reals, initialize={t: 0 for t in l_t})  # reactive power imported from the grid,
                                                                                    # for now we suppose that any element exchanges reactive power


    ## Constraints ##

    if PF_type == 'DC-OPF':
        DCPowerFlow(model, l_t, l_bus, AllInputs)
        def Constraint_DC_PF_Q(m, t):
            return sum(m.Qinj[i_bus, t] for i_bus in l_bus) == 0
        model.Constr_DC_PF_Q = pyo.Constraint(model.t, rule=Constraint_DC_PF_Q)
    elif PF_type == 'AC-OPF':
        SOCPACPowerFlow(model, l_t, l_bus, AllInputs)
    else:  # PF_type == 'economic_dispatch'
        def Constraint_PF_economic_dispatch_P(m, t):
            return sum(m.Pinj[i_bus, t] for i_bus in l_bus) == 0
        model.Constr_PF_economic_dispatch_P = pyo.Constraint(model.t, rule=Constraint_PF_economic_dispatch_P)
        def Constraint_PF_economic_dispatch_Q(m, t):
            return sum(m.Qinj[i_bus, t] for i_bus in l_bus) == 0
        model.Constr_PF_economic_dispatch_Q = pyo.Constraint(model.t, rule=Constraint_PF_economic_dispatch_Q)

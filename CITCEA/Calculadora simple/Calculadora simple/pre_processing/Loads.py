
class DemandClass:  # de moment només base i EV immediate charging
    def __init__(self):
        self.id = 0  # number of the load
        self.id_list = []  # list with all loads numbers
        self.name = {}  # name of the load
        self.pos_bus = {}  # binary that indicates the bus to which the load is connected --> [id_load,id_bus]=1
        self.type = {}  # type of load (AC, DC, EV)
        self.Pd = {}  # Active power demand of the load [kW]

    def add(self, id, name, type, bus, l_bus, l_t, P_installed, P_demand_DataFrame):
        self.id = id  # number of the load
        self.id_list.append(id)  # list with all loads numbers
        self.name[id] = name  # name of the load
        pos = {(self.id, bus_aux): 0 for bus_aux in l_bus}
        pos[self.id, bus] = 1
        self.pos_bus.update(pos)
        self.type[id] = type  # type of load (AC, DC, EV)
        new_Pd = {(self.id, t): P_demand_DataFrame[t] * P_installed for t in l_t}
        self.Pd.update(new_Pd)


    def total_buses(self, l_bus, l_t):
        Pd_total = {(bus, t): 0 for t in l_t for bus in l_bus}
        Pd_EV_total = {(bus, t): 0 for t in l_t for bus in l_bus}
        Pd_total_inclEV = {(bus, t): 0 for t in l_t for bus in l_bus}
        for id_load in self.id_list:
            for bus in l_bus:
                for t in l_t:
                    Pd_total_inclEV[bus, t] = Pd_total_inclEV[bus, t] + self.Pd[id_load, t] * self.pos_bus[id_load, bus]
            if self.type[id_load] == 'EV':
                for bus in l_bus:
                    for t in l_t:
                        Pd_EV_total[bus,t] = Pd_EV_total[bus,t] + self.Pd[id_load, t] * self.pos_bus[id_load, bus]
            else:
                for bus in l_bus:
                    for t in l_t:
                        Pd_total[bus, t] = Pd_total[bus, t] + self.Pd[id_load, t] * self.pos_bus[id_load, bus]
        self.Pd_total = Pd_total  # Active power demand of the bus [kW]
        self.Pd_EV_total = Pd_EV_total  # Active power demand of EV of the bus [kW]
        self.Pd_total_inclEV = Pd_total_inclEV  # Active power demand of the bus including EV [kW]


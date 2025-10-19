
class BusClass:
    def __init__(self):
        self.id = 0  # number of the bus
        self.id_list = []  # list with all bus numbers
        self.name = {}  # name of the bus
        self.type = {}  # bus type (AC or DC)
        self.Vn = {}  # nominal voltage of the bus [kV]
        self.slack = {}  # binary that indicates if the bus is a slack (1) or not (0)
        self.Vmin = {}  # minimum voltage of the bus [pu]
        self.Vmax = {}  # maximum voltage of the bus [pu]

    def add(self, id, name, type, Vn, slack, Vmin, Vmax):
        self.id = id  # number of the bus
        self.id_list.append(id)  # list with all bus numbers
        self.name[id] = name  # name of the bus
        self.type[id] = type  # bus type (AC or DC)
        self.Vn[id] = Vn  # nominal voltage of the bus [kV]
        self.slack[id] = slack  # binary that indicates if the bus is a slack (1) or not (0)
        self.Vmin[id] = Vmin  # minimum voltage of the bus [pu]
        self.Vmax[id] = Vmax  # maximum voltage of the bus [pu]


class LinesClass:  # --------------------------------------------------------------------- from iplug
    def __init__(self, l_bus):
        self.id = 0  # number of the line
        self.id_list = []  # list with all lines numbers
        self.name = {}  # name of the line
        self.from_bus = {}
        self.to_bus = {}
        self.Pmax_line = {}  # maximum power flowing through the line [pu]
        self.i_max_line = {}  # maximum current flowing through the line [pu]
        self.r_line = {}  # resistence [Ω]
        self.x_line = {}  # reactance [Ω]
        self.b_line = {}  # impedance [S]

        self.z_matrix = {(bus1, bus2): 0 for bus1 in l_bus for bus2 in l_bus}  # impedance [pu] --> Z[bus1,bus2] = R+Xj
        self.y_earth_matrix = {(bus1, bus2): 0 for bus1 in l_bus for bus2 in l_bus}  # earth admitance [pu] --> Y[bus1,bus2] = Bj

        self.y_bus = {(bus1, bus2): 0 for bus1 in l_bus for bus2 in l_bus}

        self.Pmax = {(bus1, bus2): 0 for bus1 in l_bus for bus2 in l_bus}  # maximum power flowing through the line [pu]
        self.i_max = {(bus1, bus2): 0 for bus1 in l_bus for bus2 in l_bus}  # maximum current flowing through the line [pu]


    def add(self, id, name, from_bus, to_bus, Pmax, I_max, R, X, B, Zb, Sb, Ib):
        self.id = id  # number of the line
        self.id_list.append(id)  # list with all lines numbers
        self.name[id] = name  # name of the line
        self.from_bus[id] = from_bus
        self.to_bus[id] = to_bus
        self.Pmax_line[id] = Pmax/Sb  # maximum power flowing through the line [pu]
        self.i_max_line[id] = I_max/Ib  # maximum current flowing through the line [pu]
        self.r_line[id] = R/Zb  # resistence [pu]
        self.x_line[id] = X/Zb  # reactance [pu]
        self.b_line[id] = B*Zb  # susceptance [pu]

        self.z_matrix[from_bus, to_bus] = self.r_line[id] + 1j * self.x_line[id]
        # z_mod[bus1, bus2] = m.sqrt(z[bus1, bus2].real ** 2 + z[bus1, bus2].imag ** 2)
        # z_phase[bus1, bus2] = cm.phase(z[bus1, bus2])
        self.y_earth_matrix[from_bus, to_bus] = 1j * self.b_line[id]

        self.y_bus[from_bus, to_bus] = self.y_bus[to_bus, from_bus] = -1 / self.z_matrix[from_bus, to_bus]
        self.y_bus[from_bus, from_bus] += 1 / self.z_matrix[from_bus, to_bus] + self.y_earth_matrix[from_bus, to_bus]/2
        self.y_bus[to_bus, to_bus] += 1 / self.z_matrix[from_bus, to_bus] + self.y_earth_matrix[from_bus, to_bus]/2

        self.Pmax[from_bus, to_bus] = self.Pmax[to_bus, from_bus] = self.Pmax_line[id]
        self.i_max[from_bus, to_bus] = self.i_max[to_bus, from_bus] = self.i_max_line[id]


    def global_system(self, l_bus):
        self.G_bus = {}  # real part of the y_bus matrix [pu]
        self.B_bus = {}  # imaginary part of the y_bus matrix [pu]
        for bus1 in l_bus:
            for bus2 in l_bus:
                self.G_bus[bus1, bus2] = self.y_bus[bus1, bus2].real
                self.B_bus[bus1, bus2] = self.y_bus[bus1, bus2].imag


class NetworkClass:
    def __init__(self, PF_type, Sb, Buses, Lines):
        self.PF_type = PF_type  # economic_dispatch / DC-OPF
        self.Sb = Sb
        self.Buses = Buses
        self.Lines = Lines
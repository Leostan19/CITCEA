import numpy
import pandas


######################### Classes #########################


class ClientEVClass:
    '''
    Class that stores the inputs of the EV
    '''
    def __init__(self, client_DataFrame):  # EV data input will change
        '''
        Class that stores the inputs of the EV
        :param client_DataFrame: pandas DataFrame with the EV inputs defined by the customer, excel format
        '''
        # General EV data
        self.hay = client_DataFrame.loc['EV (1: yes, 0: no)'][1]  # binary that indicates if there is EV in the microgrid. 1: yes, 0: no
        self.immediate0_smart1 = client_DataFrame.loc['Smart charging (1) or Immediate charging (0)'][1]  # binary that indicates the charging pode of the EV. 1: smart charging, 0: immediate charging
        # EV data to define the load
        # self.type = client_DataFrame.loc['Model EV'][1]  # model of the EV
        self.n_EV = client_DataFrame.loc['Number of vehicles'][1]
        self.n_charging_points = client_DataFrame.loc['Number of charging points'][1]
        self.Pmax_battery = client_DataFrame.loc['Maximum charging power of the EV battery'][1]  # kW
        self.Pmax_charging_point = client_DataFrame.loc['Maximum power of the charging point'][1]  # kW
        self.Pmax_station = client_DataFrame.loc['Maximum power of the charging station'][1]  # kW
        self.arrival_distribution = client_DataFrame.loc['Probability distribution arrivals (1: Normal, 0: Uniform)'][1]  # binary that indicates the EV arrival probability distribution. 1: Normal, 0: Uniform
        self.arrival_parameter1 = client_DataFrame.loc['1st parameter arrivals'][1]  # 1st parameter value of the arrival probability distribution. Normal: mean hour, Uniform: minimum hour
        self.arrival_parameter2 = client_DataFrame.loc['2nd parameter arrivals'][1]  # 2nd parameter value of the arrival probability distribution. Normal: standard deviation, Uniform: maximum hour
        self.days_repeat = client_DataFrame.loc['Days'][1]  # string that indicates the days that the load is repeated: 'todos los dias', 'Lu-Vi', 'fin de semana'
        self.parked_distribution = client_DataFrame.loc['Probability distribution parked (1: Normal, 0: Uniform)'][1]  # binary that indicates the EV parked time probability distribution. 1: Normal, 0: Uniform
        self.parked_parameter1 = client_DataFrame.loc['1st parameter parked'][1]  # 1st parameter value of the parked time probability distribution. Normal: mean hour, Uniform: minimum hour
        self.parked_parameter2 = client_DataFrame.loc['2nd parameter parked'][1]  # 2nd parameter value of the parked time probability distribution. Normal: standard deviation, Uniform: maximum hour
        self.flexibility_cost = client_DataFrame.loc['Flexibility cost'][1]  # €


class ClientEVProcesadoClass:  # contiene los datos procesados de EV
    def __init__(self, dict_t_llegada, dict_t_duracion_aparcado, P_max, E_ini, E_fin, P_estacion):
        self.t_llegada = dict_t_llegada
        self.t_aparcado = dict_t_duracion_aparcado
        self.P_max = P_max
        self.E_ini = E_ini
        self.E_fin = E_fin
        self.P_estacion = P_estacion


class CargasFlexiblesEVClass:  # flexibilidad
    def __init__(self, type, n_Mev, l_Mev, K_request_evMev, K_evMev_t, E_evMev, Pmax_evMev, P_estacion, nn, Pbaseline_evMev_t, Cost_evMev):
        '''

        :param type:
        :param n_Mev:
        :param l_Mev:
        :param K_request_evMev:
        :param K_evMev_t:
        :param E_evMev:
        :param Pmax_evMev:
        :param P_estacion:
        :param nn:
        '''
        self.type = type  # 'EV'
        self.n_Mev = n_Mev  # numero de cargas flexibles (en total)
        self.n_M = nn  # "numero de veces que se repite la misma carga"
        self.l_Mev = l_Mev  # set (del nº de cargas)
        self.K_request_evMev = K_request_evMev  # indica si la carga M se puede utilizar para flexibility request (1) o no (0)
        self.E_evMev = E_evMev
        self.Pmax_evMev = Pmax_evMev
        self.K_evMev_t = K_evMev_t
        self.P_estacion = P_estacion
        self.Pbaseline_evMev_t = Pbaseline_evMev_t
        self.Cost_evMev = Cost_evMev
    def empty(self):
        '''
        If no EV smart, then call this function.
        If all variables and parameters are a function of the number of EVs, then they will be empty dictionaries
        '''
        self.n_Mev = 0
        self.l_Mev = []


class EVClass:
    def __init__(self, hay, l_t):
        self.hay = hay
        self.immediate0_smart1 = 0
        self.immediate = {t: 0 for t in l_t}
        self.smart = CargasFlexiblesEVClass('EV', 0, list(range(1)), {}, {}, {}, {}, {}, {}, {}, {})

    def add(self, l_t, inc_t, client_EV, total_EV_immediate_load, nombre_dias, l_bus):
        EV_inputs = ClientEVClass(client_EV)  # pasa los inputs de DataFrame a Class
        D_EV_immediate = EV_immediate(l_t, inc_t, EV_inputs, nombre_dias)  # EV se calcula a partir de los datos
        # D_EV_immediate = EV_immediate2(l_t, time_data)  # EV introducido directamente como un input anual
        # D_EV_immediate = total_EV_immediate_load  # EV introducido mediante Loads class
        EV_smart = flexibilidad_EV(l_t, inc_t, EV_inputs, nombre_dias)

        self.hay = EV_inputs.hay
        self.immediate0_smart1 = EV_inputs.immediate0_smart1
        self.immediate = D_EV_immediate
        self.smart = EV_smart

        pos = {bus_aux: 0 for bus_aux in l_bus}
        pos[client_EV.loc['Bus'][1]] = 1
        self.pos_bus = pos


######################### Input #########################

def procesa_input_EV(l_t, inc_t, client_EV2):
    '''
    Esta función procesa los inputs de EV introducidos por el cliente para tenerlos en el formato adecuado para definir los EV posteriormente
    :param l_t: ``list`` containing all time-steps
    :param inc_t: time-step magnitude [h]
    :param client_EV2: clase que contiene los datos de EV definidos por el cliente
    :return: clase con los datos de EV definidos por el cliente procesados para su posterior uso
    '''

    '''numpy.random.seed(0) <-- if probability results wants to be fixed in all runs'''
    if client_EV2.arrival_distribution == 1:
        h_arrival_vehicles = numpy.random.normal(loc=client_EV2.arrival_parameter1, scale=client_EV2.arrival_parameter2, size=client_EV2.n_EV)
    else:
        h_arrival_vehicles = numpy.random.uniform(low=client_EV2.arrival_parameter1, high=client_EV2.arrival_parameter2, size=client_EV2.n_EV)

    if client_EV2.parked_distribution == 1:
        h_parked_vehicles = numpy.random.normal(loc=client_EV2.parked_parameter1, scale=client_EV2.parked_parameter2, size=client_EV2.n_EV)
    else:
        h_parked_vehicles = numpy.random.uniform(low=client_EV2.parked_parameter1, high=client_EV2.parked_parameter2, size=client_EV2.n_EV)

    h_arrival_vehicles = h_arrival_vehicles.tolist()
    h_arrival_vehicles.sort()  # order the vehicles by arrival time
    h_parked_vehicles = h_parked_vehicles.tolist()

    P_max = min(client_EV2.Pmax_battery, client_EV2.Pmax_charging_point)
    E_fin = 554.2/0.95  # SOC_i*kWh # energy that the vehicle has to have when leaving (40-100 kWh)
    E_ini = 0  # SOC_f*kWh # energy that the vehicle has when arrives
    P_estacion = client_EV2.Pmax_station

    t_llegada = [None]*client_EV2.n_EV
    t_aparcado = [None]*client_EV2.n_EV
    for i in range(client_EV2.n_EV):
        t_llegada[i] = h_arrival_vehicles[i] / inc_t  # time-step at which the vehicle i arrives
        t_aparcado[i] = h_parked_vehicles[i] / inc_t  # the vehicle i parked time expressed as time-step length

    n_dias = (l_t[-1]+1)*inc_t/24

    caracteristicas_EV = ClientEVProcesadoClass(t_llegada,t_aparcado, P_max, E_ini, E_fin, P_estacion)
    return caracteristicas_EV


######################### Immediate charging #########################
'''En este caso, nos darian ya la curva de demanda horaria.
Pero de momento, la creamos con el siguiente codigo:'''

def get_demanda_diaria_EV(l_t, inc_t, EV_inputs):
    '''

    :param l_t: ``list`` containing all time-steps
    :param inc_t: time-step magnitude [h]
    :param EV_inputs: clase que contiene los datos de EV definidos por el cliente
    :return:
    '''
    # se obtiene una lista con la demanda total de EV en 1 dia,
    # suponiendo que el comportamiento de los vehiculos es el mismo todos los dias

    t_list = numpy.arange(0, 24/inc_t, 1)
    t_list = t_list.tolist()  # lista con los instantes t de un dia
    t_P_matrix = numpy.zeros((EV_inputs.n_EV + 2, t_list.__len__()))
        # la primera línea son las t de un dia
        # las líneas intermedias son las P que requiere cada vehiculo en cada t
        # la última línea es la P total consumida por la estación de carga en cada t
    t_P_matrix = t_P_matrix.tolist()
    t_P_matrix[0] = t_list

    # procesamos los datos de EV
    caracteristicas_EV = procesa_input_EV(l_t, inc_t, EV_inputs)
    t_llegada = caracteristicas_EV.t_llegada
    t_aparcado = caracteristicas_EV.t_aparcado
    P_max = caracteristicas_EV.P_max
    E_ini = caracteristicas_EV.E_ini
    E_fin = caracteristicas_EV.E_fin
    P_estacion = caracteristicas_EV.P_estacion

    for i in range(EV_inputs.n_EV):  # para cada vehiculo aparcado
        for t in range(int(t_llegada[i]), int(t_llegada[i]+t_aparcado[i])):
            # al inicio, el vehiculo tiene la energia E_ini --> E_ti = E_ini
            # inc_t_EV indica el tiempo que el vehiculo está cargando en entre ese instante y el siguiente
            if t_llegada[i] >= t:
                inc_t_EV = (t+1-t_llegada[i]) * inc_t
                E_ti = E_ini
            elif t_llegada[i]+t_aparcado[i] < t+1:
                inc_t_EV = (t_llegada[i]+t_aparcado[i]-t) * inc_t
            else:
                inc_t_EV = inc_t

            if E_fin > E_ti:
                P_ti = min(P_max, (E_fin-E_ti)/inc_t_EV)  # potencia de carga del vehiculo en ese instante:
                    # es el minimo entre la potencia maxima de carga y la potencia necesaria para la carga completa
                if t_P_matrix[-1][t]+P_ti > P_estacion:
                    # si la potencia de carga anterior provoca una saturación en la estacion de carga,
                    # la potencia real de carga sera tan grande como la estacion de carga permita
                    P_ti = P_estacion - t_P_matrix[-1][t]
                E_ti = E_ti + P_ti * inc_t_EV  # calculo de la energia inicial en el siguiente instante
                t_P_matrix[i+1][t] = P_ti
                t_P_matrix[-1][t] = t_P_matrix[-1][t] + P_ti
            else:
                break  # cuando el vehiculo esta completamente cargado
    return t_P_matrix[-1]


def get_demanda_diaria_EV2(l_t, inc_t, EV_inputs, caracteristicas_EV):
    '''
    Diferencias con la funcion anterior:
        - caracteristicas_EV=procesa_input_EV(...) es externo a esta función
        - el output está desglosado. Es un array donde la 1a linea son las t de un dia, la ultima linea es la P total consumida, y cada una de las lineas intermedias es la P consumida por un EV
    :param l_t: lista con los diferentes instantes de tiempo (nº de períodos) a considerar
    :param inc_t: incremento de la t entre dos instantes consecutivos de la simulación, inc_t=Xh (1 período = Xh)
    :param EV_inputs: clase que contiene los datos de EV definidos por el cliente
    :return:
    '''
    # se obtiene una lista con la demanda total de EV en 1 dia,
    # suponiendo que el comportamiento de los vehiculos es el mismo todos los dias

    t_list = numpy.arange(0, 24/inc_t, 1)
    t_list = t_list.tolist()  # lista con los instantes t de un dia
    t_P_matrix = numpy.zeros((EV_inputs.n_EV + 2, t_list.__len__()))
        # la primera línea son las t de un dia
        # las líneas intermedias son las P que requiere cada vehiculo en cada t
        # la última línea es la P total consumida por la estación de carga en cada t
    t_P_matrix = t_P_matrix.tolist()
    t_P_matrix[0] = t_list

    # procesamos los datos de EV
    t_llegada = caracteristicas_EV.t_llegada
    t_aparcado = caracteristicas_EV.t_aparcado
    P_max = caracteristicas_EV.P_max
    E_ini = caracteristicas_EV.E_ini
    E_fin = caracteristicas_EV.E_fin
    P_estacion = caracteristicas_EV.P_estacion

    for i in range(EV_inputs.n_EV):  # para cada vehiculo aparcado
        for t in range(int(t_llegada[i]), int(t_llegada[i]+t_aparcado[i])):
            # al inicio, el vehiculo tiene la energia E_ini --> E_ti = E_ini
            # inc_t_EV indica el tiempo que el vehiculo está cargando en entre ese instante y el siguiente
            if t_llegada[i] >= t:
                inc_t_EV = (t+1-t_llegada[i]) * inc_t
                E_ti = E_ini
            elif t_llegada[i]+t_aparcado[i] < t+1:
                inc_t_EV = (t_llegada[i]+t_aparcado[i]-t) * inc_t
            else:
                inc_t_EV = inc_t

            if E_fin > E_ti:
                P_ti = min(P_max, (E_fin-E_ti)/inc_t_EV)  # potencia de carga del vehiculo en ese instante:
                    # es el minimo entre la potencia maxima de carga y la potencia necesaria para la carga completa
                if t_P_matrix[-1][t]+P_ti > P_estacion:
                    # si la potencia de carga anterior provoca una saturación en la estacion de carga,
                    # la potencia real de carga sera tan grande como la estacion de carga permita
                    P_ti = P_estacion - t_P_matrix[-1][t]
                E_ti = E_ti + P_ti * inc_t_EV  # calculo de la energia inicial en el siguiente instante
                t_P_matrix[i+1][t] = P_ti
                t_P_matrix[-1][t] = t_P_matrix[-1][t] + P_ti
            else:
                break  # cuando el vehiculo esta completamente cargado
    return t_P_matrix


def dias_EV(cuando_EV_client, dia):
    '''

    :param cuando_EV_client: 'Lu-Vi' or 'fin de semana' or 'todos los dias'
    :param dia: 'Lunes' or 'Martes' 'Miércoles' or 'Jueves' or 'Viernes'
    :return: boolean que indica si dia está contenido en cuando_EV_client
    '''
    # indica si "dia" pertenece al conjunto "EV_client"
    if cuando_EV_client == 'Lu-Vi':
        return dia == 'Lunes' or dia == 'Martes' or dia == 'Miércoles' or dia == 'Jueves' or dia == 'Viernes'
    elif cuando_EV_client == 'fin de semana':
        return dia == 'Sábado' or dia == 'Domingo'
    else:
        return True


def EV_immediate(l_t, inc_t, EV_inputs, nombre_dias):
    '''

    :param l_t: lista con los diferentes instantes de tiempo (nº de períodos) a considerar
    :param inc_t: incremento de la t entre dos instantes consecutivos de la simulación, inc_t=Xh (1 período = Xh)
    :param EV_inputs:
    :param nombre_dias:
    :return:
    '''

    n_dias = (l_t[-1] + 1) * inc_t / 24
    D_EV = {}
    for dia in range(int(n_dias)):
        t = dia * 24 / inc_t
        # si el dia del instante t pertenece al conjunto de dias en los que hay EVs,
        # la demanda es la calculada anteriormente, sino es 0
        if dias_EV(EV_inputs.days_repeat, nombre_dias['dia'][t]):
            D_EV_dia = get_demanda_diaria_EV(l_t, inc_t, EV_inputs)
        else:
            D_EV_dia = numpy.zeros((1, int(24 / inc_t)))
            D_EV_dia = D_EV_dia.tolist()[0]
        # se crea el diccionario de demanda anual de EV a partir de la demanda diaria
        for tt in range(int(24 / inc_t)):
            D_EV[t + tt] = D_EV_dia[tt]
    return D_EV


def EV_immediate2(l_t, file_data):
    ''' pasa del input del excel a dict '''
    D_EV={t: file_data['EV immediate charging [kW]'][t] for t in l_t}
    return D_EV


'''
si Immediate charging, importar D_EV como inicializador del parámetro correspondiente:
model.D_EV = pyo.Param(model.t, within=pyo.NonNegativeReals, initialize=D_EV)
'''


######################### Smart charging #########################
def flexibilidad_EV(l_t, inc_t, client_EV2, nombre_dias):
    '''

    :param l_t: lista con los diferentes instantes de tiempo (nº de períodos) a considerar
    :param inc_t: incremento de la t entre dos instantes consecutivos de la simulación, inc_t=Xh (1 período = Xh)
    :param client_EV2:
    :param nombre_dias:
    :return:
    '''

    # procesamos los datos de EV
    caracteristicas_EV = procesa_input_EV(l_t, inc_t, client_EV2)
    t_llegada = caracteristicas_EV.t_llegada
    t_aparcado = caracteristicas_EV.t_aparcado
    P_max = caracteristicas_EV.P_max
    E_ini = caracteristicas_EV.E_ini
    E_fin = caracteristicas_EV.E_fin
    P_estacion = caracteristicas_EV.P_estacion

    # caso concreto de carga shiftable modular
    n_dias = (l_t[-1] + 1) * inc_t / 24
    if client_EV2.hay == 1 and client_EV2.immediate0_smart1 == 1:
        n_Mev = client_EV2.n_EV  # numero de EVs en smart charging

        E_ev = E_fin-E_ini  # energia total de carga de cada vehiculo

        D_EV_dia_matrix = get_demanda_diaria_EV2(l_t, inc_t, client_EV2,
                                                 caracteristicas_EV)  # consumo diario de potencia de cada vehiculo (si fuera immediate charging)

        K_evMev_t = {}  # binaria que indica la disponibilidad de cada carga en cada instante
        D_evMev_t = {}  # potencia consumida por cada vehiculo en cada instante, si fuera immediate charging (se supone que esto es el baseline)
        Cost_evMev = {}  # flexibility cost
        nn_Mev = {}
        n2_Mev = 0
        for Mev in list(range(n_Mev)):
            nn_Mev[Mev] = 0
            for dia in range(int(n_dias)):
                if dias_EV(client_EV2.days_repeat, nombre_dias['dia'][dia * 24]):
                    tt=0
                    # cada vehiculo cada dia, representa una carga flexible independiente
                    for t in l_t:
                        # cada vehiculo electrico solo estará disponible entre la hora de llegada y de salida de cada dia
                        if (t - 24*dia >= t_llegada[Mev]) and (t - 24*dia <= t_llegada[Mev] + t_aparcado[Mev]):
                            K_evMev_t[n2_Mev, t] = 1
                        else:
                            K_evMev_t[n2_Mev, t] = 0
                        # el dia que se debe aplicar el perfil baseline calculado
                        if t >= dia*24 and t < (dia+1)*24:
                            D_evMev_t[n2_Mev, t] = D_EV_dia_matrix[Mev+1][tt]
                            tt = tt+1
                        else:
                            D_evMev_t[n2_Mev, t] = 0
                    Cost_evMev[n2_Mev] = client_EV2.flexibility_cost
                    nn_Mev[Mev] = nn_Mev[Mev] + 1
                    n2_Mev = n2_Mev + 1  # numero total de cargas flexibles EV independientes
        l_Mev = list(range(n2_Mev))

        Pmax_evMev = {Mev: P_max for Mev in l_Mev}  # potencia maxima de carga de cada vehiculo
        E_evMev = {Mev: E_ev for Mev in l_Mev}  # energia a cargar en cada vehiculo

        K_request_evMev = {Mev: 1 for Mev in l_Mev}  # indica si la carga Mev se puede utilizar para flexibility request (1) o no (0)

    else:
        n_Mev = 0
        l_Mev = list(range(1))
        Pmax_evMev = {}
        E_evMev = {}
        K_evMev_t = {}
        K_request_evMev = {}
        D_evMev_t = {}
        Cost_evMev = {}
        nn_Mev = {}

    EV_smart = CargasFlexiblesEVClass('EV', n_Mev, l_Mev, K_request_evMev, K_evMev_t, E_evMev, Pmax_evMev, P_estacion, nn_Mev, D_evMev_t, Cost_evMev)
    return EV_smart


####################################################################################################################



def dataframe_from_dict(dict, columns=[], filas=[]):
    '''
    Esta función crea un DataFrame (para escribir en excel) a partir de un diccionario
    :param dict: diccionario expresado como {(index_column, index_fila): valor}
    :param columns: lista con los indices de las columnas
    :param filas: lista con los indices de las filas
    :return: DataFrame con los valores del diccionario
    '''
    if type(list(dict.keys())[0]) is tuple:
        dict_fin = {}
        for col in columns:
            lista = []
            for i in filas:
                lista.insert(i, dict[col, i])
            dict_fin[col] = lista
        tabla = pandas.DataFrame(dict_fin, index=filas)
    elif type(list(dict.keys())[0]) is int:
        tabla = pandas.DataFrame(dict, index=[0])
    return tabla


##### Flexibilidad: carga shiftable modular: EV smart charging #####
# esta parte se ha quedado igual que estaba
def save_EV_inputs(directory_Flexibilidad, EV_smart, l_t):
    '''
    A partir de los EV procesados, guarda los datos desglosados en un excel
    :param directory_Flexibilidad: dirección del directorio en el que guardar los excels
    :param EV_smart: clase con todos los datos de los EV
    :param l_t: --> list(range(24*365))
    :return:
    '''
    if EV_smart.n_Mev > 0:
        tabla_K_t = dataframe_from_dict(EV_smart.K_evMev_t, EV_smart.l_Mev, l_t)
        tabla_Pmax_t = dataframe_from_dict(EV_smart.Pmax_evMev, EV_smart.l_Mev, l_t)
        tabla_K_request = dataframe_from_dict(EV_smart.K_request_evMev)
        tabla_E = dataframe_from_dict(EV_smart.E_evMev)
        tabla_Pbaseline_t = dataframe_from_dict(EV_smart.Pbaseline_evMev_t, EV_smart.l_Mev, l_t)
        tabla_precio = dataframe_from_dict(EV_smart.Cost_evMev)
        if os.path.exists(directory_Flexibilidad) == False:
            os.mkdir(directory_Flexibilidad)
        with pandas.ExcelWriter(directory_Flexibilidad + 'EV.xlsx') as writer:
            # print('OK shiftable modular')
            tabla_K_t.to_excel(writer, sheet_name='K')
            tabla_Pmax_t.to_excel(writer, sheet_name='Pmax')
            tabla_K_request.to_excel(writer, sheet_name='K_request')
            tabla_E.to_excel(writer, sheet_name='E')
            tabla_Pbaseline_t.to_excel(writer, sheet_name='Pbaseline')
            tabla_precio.to_excel(writer, sheet_name='precios')
    return

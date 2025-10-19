import csv
import math
import requests
import os
import pandas
'''
Comentarios:
    - si time-step diferente de 1h, el input de forecast de PVGIS debe modificarse
    - podemos introducir tantos modelos de PV como queramos
    - podemos hacer sizing y/o existente para un mismo modelo
    - alternativamente a realizar el sizing se puede fijar la capacidad instalada a añadir. Si esto no se fija, debe de ser nan --> math.isnan(PV.fix_kW[id]) = True
    - si no se introduce ningun modelo, no se considera
'''


class PVClass:
    '''Class with all the inputs of the PV system'''

    def __init__(self, available_surface):
        '''
        Class with all the inputs of the PV system
        :param available_surface: available surface for all PVs
        '''
        self.id = 0  # number of the PV system
        self.id_list = []  # list with all PV system numbers
        self.name = {}  # name of the PV system
        self.pos_bus = {}  # binary that indicates the bus to which the load is connected --> [id_load,id_bus]=1

        # General data
        self.available_surface = available_surface  # available surface for all PV (add, existent, and fix, and for all models)
        self.model = {}  # model of the PV panel, from the database
        self.sizing = {}  # binary that indicates if PV should be sized (to add). 1: yes, 0: no
        self.existent_kW = {}  # PV installed capacity [kW] already in the system. This will have operation and replacement costs
        self.fix_kW = {}  # if the sizing is fixed, PV installed capacity [kW]. This will have investment, operation and replacement costs
        self.capex_incentives = {}  # economic incentives on the capex for PV [€/kW]
        self.forecast = {}  # PV generation availability [kW/kWp = pu]

        # Costs of the selected model
        self.capital = {}  # investment cost --> [€/kW] for PV and genset and converter, [€/u] for battery
        self.replacement = {}  # replacement cost --> [€/kW] for PV and genset and converter, [€/u] for battery
        self.om = {}  # operation and maintenance cost --> [€/kW/year] for PV and converter, [€/kW/h] for genset, [€/u/year] for battery
        self.lifetime = {}  # lifetime [years]

        # Performance characteristics of the selected model
        self.DNI = {}  # ratio between installed power and surface required [kW/m2]
        self.derating = {}  # %
        self.tempEff = {}  # %/ºC
        self.nomTemp = {}  # ºC
        self.nomEff = {}  # %

    def add(self, id, name, bus, l_bus, model, sizing, existent, fix, incentives, forecast_type, PVGIS_data, leap_year, forecast_DataFrame, database_DataFrame, cash_exchange, l_t):
        '''
        Add a PV set
        :param id: number of the PV system
        :param name: name of the PV system
        :param bus: bus id to which the PV is connected
        :param l_bus: list with the id of all the buses
        :param model: model of the PV panel, from the database
        :param sizing: binary that indicates if PV should be sized (to add). 1: yes, 0: no
        :param existent: PV installed capacity already in the system. This will have operation and replacement costs
        :param fix: if the sizing is fixed, PV installed capacity. This will have investment, operation and replacement costs
        :param incentives: economic incentives on the capex for PV [€/kW]
        :param forecast_type: 1: from PVGIS, 0: from excel
        :param PVGIS_data: excel regarding PVGIS inputs (DataFrame)
        :param leap_year: binary that indicates if it's a leap year (1) or not (0). Normal year has 365 days, leap year has 366 days (29th February)
        :param forecast_DataFrame: excel with the PV forecast (DataFrame)
        :param database_DataFrame: excel with the parameters for all PV models (DataFrame)
        :param cash_exchange: €/$
        :param l_t: list(range(24*365)), PVGIS only gives hourly data!!!
        :return: Class with all the inputs of the PV system updated
        '''
        self.id = id  # number of the PV system
        self.id_list.append(id)  # list with all PV system numbers
        self.name[id] = name  # name of the PV system

        pos = {(self.id, bus_aux): 0 for bus_aux in l_bus}
        pos[self.id, bus] = 1
        self.pos_bus.update(pos)

        # General data
        self.model[id] = model  # model of the PV panel, from the database
        self.sizing[id] = sizing  # binary that indicates if PV should be sized (to add). 1: yes, 0: no
        self.existent_kW[id] = existent  # PV installed capacity [kW] already in the system. This will have operation and replacement costs
        self.fix_kW[id] = fix  # if the sizing is fixed, PV installed capacity [kW]. This will have investment, operation and replacement costs
        self.capex_incentives[id] = incentives  # economic incentives on the capex for PV [€/kW]

        # extract characteristics of the selected model from the database, and add the row Model PV
        component_DataFrame = pandas.concat([pandas.Series({'Model PV': model}),
                                             database_DataFrame.loc[model]])

        # Costs of the selected model
        self.capital[id] = component_DataFrame.loc['Capital'] * cash_exchange  # investment cost --> [€/kW] for PV and genset and converter, [€/u] for battery
        self.replacement[id] = component_DataFrame.loc['Replacement'] * cash_exchange  # replacement cost --> [€/kW] for PV and genset and converter, [€/u] for battery
        self.om[id] = component_DataFrame.loc['O&M'] * cash_exchange  # operation and maintenance cost --> [€/kW/year] for PV and converter, [€/kW/h] for genset, [€/u/year] for battery
        self.lifetime[id] = component_DataFrame.loc['Lifetime']  # lifetime [years]

        # Performance characteristics of the selected model
        self.DNI[id] = component_DataFrame.loc['DNI rating']  # relación entre la potencia instalada y la superficie ocupada [kW/m2]
        self.derating[id] = component_DataFrame.loc['Derating']  # %
        self.tempEff[id] = component_DataFrame.loc['Temp. Effect']  # %/ºC
        self.nomTemp[id] = component_DataFrame.loc['Nomin. Temp.']  # ºC
        self.nomEff[id] = component_DataFrame.loc['Nomin. Effic.']  # %

        # Forecast
        if forecast_type == 1:  # forecast comes from PVGIS, it is calculated with the global irradiance ant ambient temperature
            forecast = get_PV_forecast(l_t, leap_year, PVGIS_data, self.derating[id], self.tempEff[id], self.nomTemp[id],
                                       self.nomEff[id])
        elif forecast_type == 0:  # power forecast is directly introduced by excel, and a dictionary is created from this data
            forecast = {t: forecast_DataFrame[t] for t in l_t}
        else:
            print('Error on PV forecast input')
        self.forecast.update({(id, t): forecast[t] for t in l_t})

    def empty(self):
        '''
        If no PV, then call this function.
        If all variables and parameters are a function of the number of assets, then they will be empty dictionaries
        '''
        self.id = 0  # number of the PV system
        self.id_list = []  # list with all PV system numbers



####################   PVGIS API   ####################

def PVGIS_API(save_location, lat, lon, raddatabase=None, startyear=None, endyear=None, pvtechchoice=None, trackingtype=None,
              angle=None, aspect=None, optimalinclination=None, optimalangles=None, outputformat=None):
    '''
    More information in https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en
    :param lat: Latitude, in decimal degrees, south is negative. Type = float
    :param lon: Longitude, in decimal degrees, west is negative. Type = float
    :param raddatabase: Name of the radiation database (DB): "PVGIS-SARAH" (Europe, Africa and Asia), "PVGIS-NSRDB"
            (the Americas between 60°N and 20°S), "PVGIS-ERA5" and "PVGIS-COSMO" for Europe (including high-latitudes),
            and "PVGIS-CMSAF" for Europe and Africa (will be deprecated).
            The default DBs are PVGIS-SARAH, PVGIS-NSRDB and PVGIS-ERA5 based on the chosen location.
    :param startyear: First year of the output of hourly averages.
            Availability varies with the temporal coverage of the radiation DB chosen.
            The default value is the first year of the DB. Type = int
    :param endyear: Final year of the output of hourly averages.
            Availability varies with the temporal coverage of the radiation DB chosen.
            The default value is the last year of the DB. Type = int
    :param pvtechchoice: PV technology. Choices are: "crystSi", "CIS", "CdTe" and "Unknown". Default = "crystSi"
    :param trackingtype: Type of suntracking used, 0=fixed, 1=single horizontal axis aligned north-south,
            2=two-axis tracking, 3=vertical axis tracking, 4=single horizontal axis aligned east-west,
            5=single inclined axis aligned north-south. Type = int
    :param angle: Inclination angle from horizontal plane. Not relevant for 2-axis tracking. Type = float
    :param aspect: Orientation (azimuth) angle of the (fixed) plane, 0=south, 90=west, -90=east.
            Not relevant for tracking planes. Type = float
    :param optimalinclination: Calculate the optimum inclination angle. Value of 1 for "yes".
            All other values (or no value) mean "no". Not relevant for 2-axis tracking. Type = int
    :param optimalangles: Calculate the optimum inclination AND orientation angles. Value of 1 for "yes".
            All other values (or no value) mean "no". Not relevant for tracking planes. Type = int
    :param outputformat: Type of output. Choices are: "csv" for the normal csv output with text explanations,
            "basic" to get only the data output with no text, and "json". Default = "csv"
    :return:
    '''
    csv_url = 'https://re.jrc.ec.europa.eu/api/seriescalc?'+'lat='+str(lat)+'&'+'lon='+str(lon)
    if raddatabase != None:
        csv_url += '&' + 'raddatabase=' + str(raddatabase)
    if startyear != None:
        csv_url += '&' + 'startyear=' + str(startyear)
    if endyear != None:
        csv_url += '&' + 'endyear=' + str(endyear)
    if pvtechchoice != None:
        csv_url += '&' + 'pvtechchoice=' + str(pvtechchoice)
    if trackingtype != None:
        csv_url += '&' + 'trackingtype=' + str(trackingtype)
    if angle != None:
        csv_url += '&' + 'angle=' + str(angle)
    if aspect != None:
        csv_url += '&' + 'aspect=' + str(aspect)
    if optimalinclination != None:
        csv_url += '&' + 'optimalinclination=' + str(optimalinclination)
    if optimalangles != None:
        csv_url += '&' + 'aspect=' + str(optimalangles)
    if outputformat != None:
        csv_url += '&' + 'aspect=' + str(outputformat)

    with requests.Session() as s:
        download = s.get(csv_url)
        decoded_content = download.content.decode('utf-8')

        cr = csv.reader(decoded_content.splitlines(), delimiter=',')
        my_list = list(cr)

        # for row in my_list:
        #     print(row)

    # dir_path = 'CSV/DATA/'  #os.path.dirname(os.path.realpath(__file__))
    # save_location = dir_path + '/PV_Wm2.xlsx'
    df = pandas.DataFrame(my_list)  # seems to work!
    df.to_excel(save_location)
    # print(df)

    return



####################   forecast from PVGIS   ####################

'''
some data is extracted from PVGIS:
    - G[t] = global irradiance, expressed in W/m2
    - Ta[t] = air temperature, expressed in ºC
data from PV components database:
    - D = derating, expressed in %
    - eff_T = temperature coefficient, expressed in %/ºC
    - Tn = nominal temperature, expressed in ºC
    - eff_n = nominal efficiency, expressed in %
suppositions based on HOMER:
    - Ta_noct = ambient temperature at thich the NOCT is defined = 20 ºC
    - G_noct = solar radiation at which the NOCT is defined = 0.8 kW/m2
    - tau_alfa = 0.9
    - G_stc = global irradiance in standard conditions = 1 kW/m2
    - T_stc = PV cell tamperature in standard conditions = 25 ºC
'''


def calc_PV_temp(Ta, G, Tn, Ta_noct, G_noct, eff_n, tau_alfa):
    '''
    Calculates the PV cell temperature, according to HOMER formulation
    :param Ta: air temperature, expressed in ºC
    :param G: global irradiance, expressed in W/m2
    :param Tn: nominal temperature, expressed in ºC
    :param Ta_noct: ambient temperature at thich the NOCT is defined = 20 ºC (HOMER)
    :param G_noct: solar radiation at which the NOCT is defined = 0.8 kW/m2 (HOMER)
    :param eff_n: nominal efficiency, expressed in %
    :param tau_alfa: 0.9 (HOMER)
    :return: PV cell temperature, expressed in ºC
    '''
    T = Ta + (G / 1000) * (Tn - Ta_noct) / G_noct * (1 - (eff_n / 100) / tau_alfa)
    return T


def calc_PV_forecast(D, G, G_stc, eff_T, T_stc, Ta, Tn, Ta_noct, G_noct, eff_n, tau_alfa):
    '''
    Calculates the PV forecast, according to homer formulation
    :param D: derating, expressed in %
    :param G: global irradiance (time series), expressed in W/m2
    :param G_stc: global irradiance in standard conditions = 1 kW/m2 (HOMER)
    :param eff_T: temperature coefficient, expressed in %/ºC
    :param T_stc: PV cell tamperature in standard conditions = 25 ºC (HOMER)
    :param Ta: air temperature (time series), expressed in ºC
    :param Tn: nominal temperature, expressed in ºC
    :param Ta_noct: ambient temperature at thich the NOCT is defined = 20 ºC (HOMER)
    :param G_noct: solar radiation at which the NOCT is defined = 0.8 kW/m2 (HOMER)
    :param eff_n: nominal efficiency, expressed in %
    :param tau_alfa: 0.9 (HOMER)
    :return: PV forecast [kW/kW installed]
    '''
    T = calc_PV_temp(Ta, G, Tn, Ta_noct, G_noct, eff_n, tau_alfa)
    f = (D / 100) * (G / 1000) / G_stc * (1 + (eff_T / 100) * (T - T_stc))
    # calculate actual forecast for a PV cell:
    #       F = f * Pn   where Pn = nominal power of the PV array in standard conditions
    return f


def PVGIS_forecast_dict(PVGIS_excel_location, derating, tempEff, nomTemp, nomEff, l_t):
    '''
    Obtains the PV forecast from the PVGIS excel and component data
    :param PVGIS_excel_location: directory and name of the data file obtained from PVGIS
    :param PV_data: object which contains the data of the PV component, based on PVDataClass()
    :param derating: derating of the PV module, expressed in %
    :param tempEff: temperature coefficient of the PV module, expressed in %/ºC
    :param nomTemp: nominal temperature of the PV module, expressed in ºC
    :param nomEff: nominal efficiency of the PV module, expressed in %
    :param l_t: --> list(range(24*365))
    :return: PV forecast [kW/kW installed]
    '''
    PVGIS_excel = pandas.read_excel(PVGIS_excel_location, sheet_name='Sheet1', header=0, index_col=0)  # importa excel PVGIS
    G = {t: float(PVGIS_excel[1][9 + t]) for t in l_t}
    Ta = {t: float(PVGIS_excel[3][9 + t]) for t in l_t}

    forecast = {}
    for t in l_t:
        f = calc_PV_forecast(derating, G[t], 1, tempEff, 25, Ta[t], nomTemp, 20, 0.8, nomEff, 0.9)
        forecast[t] = f
    return forecast


class ClientPVGISClass:
    '''Class to store the inputs given by the client for PVGIS'''

    def __init__(self, PVGIS_DataFrame, leap_year):
        '''
        Class to store the inputs given by the client for PVGIS
        :param PVGIS_DataFrame: excel filled by the client
        :param leap_year: binary that indicates if it's a leap year (1) or not (0)
        '''
        self.latitude = PVGIS_DataFrame['Latitude']  # [degrees]
        self.longitude = PVGIS_DataFrame['Longitude']  # [degrees]
        if math.isnan(PVGIS_DataFrame['Radiation database']):
            self.radiation_database = None
        else:
            self.radiation_database = PVGIS_DataFrame['Radiation database']  # PVGIS-SARAH (Europe, Africa and Asia), PVGIS-NSRDB (the Americas between 60°N and 20°S), PVGIS-ERA5 and PVGIS-COSMO for Europe (including high-latitudes), and PVGIS-CMSAF for Europe and Africa (will be deprecated)
        if leap_year == 1:
            self.start_year = 2016
        else:
            self.start_year = 2015
        self.end_year = None
        if math.isnan(PVGIS_DataFrame['PV technology']):
            self.PV_tech = None
        else:
            self.PV_tech = PVGIS_DataFrame['PV technology']  # crystSi, CIS, CdTe, Unknown
        if math.isnan(PVGIS_DataFrame['Suntracking type']):
            self.suntracking = None
        else:
            self.suntracking = int(PVGIS_DataFrame['Suntracking type'])  # 0=fixed, 1=single horizontal axis aligned north-south, 2=two-axis tracking, 3=vertical axis tracking, 4=single horizontal axis aligned east-west, 5=single inclined axis aligned north-south
        if math.isnan(PVGIS_DataFrame['Slope']):
            self.slope = None
        else:
            self.slope = PVGIS_DataFrame['Slope']  # [degrees]
        if math.isnan(PVGIS_DataFrame['Azimuth']):
            self.azimuth = None
        else:
            self.azimuth = PVGIS_DataFrame['Azimuth']  # [degrees]
        if math.isnan(PVGIS_DataFrame['Optimal slope']):
            self.optimal_slope = None
        else:
            self.optimal_slope = int(PVGIS_DataFrame['Optimal slope'])  # 1=yes, 0=no
        if math.isnan(PVGIS_DataFrame['Optimal slope and azimuth']):
            self.optimal_slope_azimuth = None
        else:
            self.optimal_slope_azimuth = int(PVGIS_DataFrame['Optimal slope and azimuth'])  # 1=yes, 0=no


def get_PV_forecast(l_t, leap_year, PVGIS_data, derating, tempEff, nomTemp, nomEff):
    '''
    Full procedure to get the PVGIS forecast from the input of the client
    :param l_t: --> list(range(24*365)), PVGIS only gives hourly data!!!
    :param leap_year: binary that indicates if it's a leap year (1) or not (0)
    :param PVGIS_data: excel filled by the client (DataFrame)
    :param derating: derating of the PV module, expressed in %
    :param tempEff: temperature coefficient of the PV module, expressed in %/ºC
    :param nomTemp: nominal temperature of the PV module, expressed in ºC
    :param nomEff: nominal efficiency of the PV module, expressed in %
    :return: PV forecast (dict) [kW/kW installed]
    '''
    PVGIS_excel_location = 'CSV/DATA/PV_Wm2.xlsx'
    # 1) Input: latitude and longitude (in degrees), and year
    PVGIS_input = ClientPVGISClass(PVGIS_data, leap_year)
    # 2) Obtain data from PVGIS --> script Josep, it is necessary to indicate the year
    PVGIS_API(PVGIS_excel_location, PVGIS_input.latitude, PVGIS_input.longitude,
              raddatabase=PVGIS_input.radiation_database, startyear=PVGIS_input.start_year,
              endyear=PVGIS_input.end_year, pvtechchoice=PVGIS_input.PV_tech,
              trackingtype=PVGIS_input.suntracking, angle=PVGIS_input.slope, aspect=PVGIS_input.azimuth,
              optimalinclination=PVGIS_input.optimal_slope, optimalangles=PVGIS_input.optimal_slope_azimuth)  #, outputformat=None)
    # 3) Calculate forecast dictionary
    forecast = PVGIS_forecast_dict(PVGIS_excel_location, derating, tempEff, nomTemp, nomEff, l_t)
    return forecast


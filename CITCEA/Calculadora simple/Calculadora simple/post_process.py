import pandas
import math
from post_processing.get_Results import *
from post_processing.KPIs import *
from post_processing.BESS_aging import *


def post_processing(instance, save_folder, AllInputs):
    '''
    Analyse the optimization results and saves them in excel files, from the inputs and the solved model.
    :param instance: pyomo solved Grid model (instance.EV)
    :param save_folder: string with the path in which the operation results file will be saved
    :param AllInputs: data class which contains all inputs
    '''

    l_t = AllInputs.System.l_t
    inc_t = AllInputs.System.inc_t
    l_PV = AllInputs.PV.id_list
    l_BESS = AllInputs.BESS.id_list
    L_prj = int(AllInputs.System.lifetime)

    # Extract results
    allResults = allResultsClass(l_t, AllInputs, instance)

    # Save results
    save_sizing(allResults, AllInputs, save_folder)
    save_operation(allResults, AllInputs, save_folder)
    save_economics(allResults, AllInputs, save_folder)
    save_network(allResults, AllInputs, save_folder)

    # BESS degradation
    if len(AllInputs.BESS.id_list) != 0:
        cycles = BESS_cycles(allResults, AllInputs)
        n_peaks = count_peaks(cycles)
    else:
        n_peaks = math.nan

    return allResults, n_peaks


def dataframe_from_dict_loads(dict, columns, rows):
    dict_fin = {}
    for col in columns:
        lista = []
        for i in rows:
            lista.insert(i, dict[col, i])
        dict_fin[col] = lista
    tabla = pandas.DataFrame(dict_fin, index=rows)
    return tabla


def save_sizing(allResults, AllInputs, save_folder):
    l_PV = AllInputs.PV.id_list
    dict_PV = {'name': [], 'PV installed power (new) [kW]': []}
    for i_PV in l_PV:
        dict_PV['name'].append(AllInputs.PV.name[i_PV])
        dict_PV['PV installed power (new) [kW]'].append(allResults.PV.G[i_PV])
    table_PV = pandas.DataFrame(dict_PV, index=l_PV)

    l_BESS = AllInputs.BESS.id_list
    dict_BESS = {
        'name': [],
        'Number of BESS installed (new) [u]': [],
        'BESS storage capacity installed (new) [kWh]': [],
        'BESS charging power installed (new) [kW]': [],
        'BESS discharging power installed (new) [kW]': [],
    }
    for i_BESS in l_BESS:
        dict_BESS['name'].append(AllInputs.BESS.name[i_BESS])
        dict_BESS['Number of BESS installed (new) [u]'].append(allResults.BESS.k_bat[i_BESS])
        dict_BESS['BESS storage capacity installed (new) [kWh]'].append(allResults.BESS.C[i_BESS])
        dict_BESS['BESS charging power installed (new) [kW]'].append(allResults.BESS.Pn_char[i_BESS])
        dict_BESS['BESS discharging power installed (new) [kW]'].append(allResults.BESS.Pn_disch[i_BESS])
    table_BESS = pandas.DataFrame(dict_BESS, index=l_BESS)

    other = [['Power is injected to the grid? (1: yes, 0: no)', allResults.Grid.lambda_inj, '']]
    table_other = pandas.DataFrame(other, columns=['Variable', 'Value', 'Units'])

    l_Grid = AllInputs.Grid.id_list
    dict_Grid = {'name': [], 'P1 [kW]': [], 'P2 [kW]': [], 'P3 [kW]': [], 'P4 [kW]': [], 'P5 [kW]': [], 'P6 [kW]': []}
    for i_Grid in l_Grid:
        dict_Grid['name'].append(AllInputs.Grid.name[i_Grid])
        for N in range(6):
            dict_Grid[f'P{N+1} [kW]'].append(allResults.Grid.P_hired_N[i_Grid, N])
    table_P_hired = pandas.DataFrame(dict_Grid, index=l_Grid)

    with pandas.ExcelWriter(save_folder + 'Sizing.xlsx') as writer:
        table_PV.to_excel(writer, sheet_name='PV', float_format="%.2f")
        table_BESS.to_excel(writer, sheet_name='Battery', float_format="%.2f")
        table_other.to_excel(writer, sheet_name='other', float_format="%.2f", header=False, index=False)
        table_P_hired.to_excel(writer, sheet_name='P_hired', float_format="%.2f")


def list_from_dict(dict_i_t, i, l_t):
    dict_t = {t: dict_i_t[i, t] for t in l_t}
    l = list(dict_t.values())
    return l


def save_operation(allResults, AllInputs, save_folder):
    l_t = AllInputs.System.l_t

    # Grid
    l_Grid = AllInputs.Grid.id_list
    dict_Grid = {}
    for i_Grid in l_Grid:
        dict_Grid[AllInputs.Grid.name[i_Grid] + ': P_buy [kW]'] = list_from_dict(allResults.Grid.P_buy, i_Grid, l_t)
        dict_Grid[AllInputs.Grid.name[i_Grid] + ': P_sell [kW]'] = list_from_dict(allResults.Grid.P_sell, i_Grid, l_t)
    table_all = pandas.DataFrame(dict_Grid, index=l_t)

    l_Mev = AllInputs.EV.smart.l_Mev
    if AllInputs.EV.hay == 1 and AllInputs.EV.immediate0_smart1 == 1:
        table_EV = dataframe_from_dict_loads(allResults.EV.P, l_Mev, l_t)
    else:
        table_EV = pandas.DataFrame()

    dict_cL = {}
    if AllInputs.EV.hay == 1 and AllInputs.EV.immediate0_smart1 == 0:
        dict_cL['EV immediate'] = list(AllInputs.EV.immediate.values())
    table_cL = pandas.DataFrame(dict_cL, index=l_t)

    with pandas.ExcelWriter(save_folder + 'Operation.xlsx') as writer:
        table_all.to_excel(writer, sheet_name='General', float_format="%.2f")
        if not table_EV.empty:
            table_EV.to_excel(writer, sheet_name='EV smart charging', float_format="%.2f")
        table_cL.to_excel(writer, sheet_name='critical load', float_format="%.2f")

        # ----- EV detailed results: P_net, P_ch, P_dis, SOC -----
        if hasattr(allResults, "EV") and hasattr(allResults.EV, "P"):
            rows = []
            for Mev in AllInputs.EV.smart.l_Mev:
                for t in l_t:
                    rows.append({
                        "EV id": Mev,
                        "timestep": t,
                        "P_net [kW]": allResults.EV.P.get((Mev, t), 0),
                        "P_ch [kW]": allResults.EV.P_ch.get((Mev, t), 0),
                        "P_dis [kW]": allResults.EV.P_dis.get((Mev, t), 0),
                    })

            ev_detail_df = pandas.DataFrame(rows)
            ev_detail_pivot = ev_detail_df.pivot(index="timestep", columns="EV id",
                                                 values=["P_net [kW]", "P_ch [kW]", "P_dis [kW]"])
            ev_detail_pivot.to_excel(writer, sheet_name="EV detailed_P", float_format="%.3f")

        # ----- EV aggregated summary -----
        if hasattr(allResults, "EV") and hasattr(allResults.EV, "P"):
            ev_summary = {}
            for Mev in AllInputs.EV.smart.l_Mev:
                P_ch = [allResults.EV.P_ch.get((Mev, t), 0) for t in l_t]
                P_dis = [allResults.EV.P_dis.get((Mev, t), 0) for t in l_t]
                P_net = [allResults.EV.P.get((Mev, t), 0) for t in l_t]

                E_ch = sum(P_ch) * AllInputs.System.inc_t
                E_dis = sum(P_dis) * AllInputs.System.inc_t
                E_net = sum(P_net) * AllInputs.System.inc_t

                ev_summary[Mev] = {
                    "Energy charged [kWh]": E_ch,
                    "Energy discharged [kWh]": E_dis,
                    "Net energy [kWh]": E_net,
                }

            ev_summary_df = pandas.DataFrame(ev_summary).transpose()
            ev_summary_df.index.name = "EV id"
            ev_summary_df.to_excel(writer, sheet_name="EV summary_totals", float_format="%.2f")


def save_economics(allResults, AllInputs, save_folder):
    l_t = AllInputs.System.l_t
    inc_t = AllInputs.System.inc_t
    L_prj = int(AllInputs.System.lifetime)
    l_PV = AllInputs.PV.id_list
    l_BESS = AllInputs.BESS.id_list
    l_Grid = AllInputs.Grid.id_list

    dict_equipment_cost = {
        'CAPEX [€]': [],
        'incentives [€]': [],
        'OPEX [€/year]': [],
        'replacement [€]': [],
        'total [€]': [],
    }
    components = []
    for i_PV in l_PV:
        components.append(AllInputs.PV.name[i_PV])
        dict_equipment_cost['CAPEX [€]'].append(allResults.PV.C_capex[i_PV])
        dict_equipment_cost['incentives [€]'].append(allResults.PV.C_incentives[i_PV])
        dict_equipment_cost['OPEX [€/year]'].append(allResults.PV.C_opex[i_PV])
        dict_equipment_cost['replacement [€]'].append(allResults.PV.C_replacement[i_PV])
        total = (
            allResults.PV.C_capex[i_PV]
            - allResults.PV.C_incentives[i_PV]
            + allResults.PV.C_opex[i_PV] * L_prj
            + allResults.PV.C_replacement[i_PV]
        )
        dict_equipment_cost['total [€]'].append(total)
    table_equipment_cost = pandas.DataFrame(dict_equipment_cost, index=components)

    with pandas.ExcelWriter(save_folder + 'Economic.xlsx') as writer:
        table_equipment_cost.to_excel(writer, sheet_name='equipment', float_format="%.2f")


def save_network(allResults, AllInputs, save_folder):
    l_bus = AllInputs.Network.Buses.id_list
    l_t = AllInputs.System.l_t

    def dataframe_from_dict(dict, columns, filas):
        dict_fin = {}
        for col in columns:
            list = []
            for i in filas:
                list.insert(i, dict[col, i])
            dict_fin[col] = list
        table = pandas.DataFrame(dict_fin, index=filas)
        return table

    table_Pinj = dataframe_from_dict(allResults.Network.Pinj, l_bus, l_t)
    with pandas.ExcelWriter(save_folder + 'Network.xlsx') as writer:
        table_Pinj.to_excel(writer, sheet_name='Pinj', float_format="%.6f")

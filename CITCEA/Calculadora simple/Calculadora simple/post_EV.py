import pandas
import pyomo.environ as pyo


def post_processing(instance, save_folder, AllInputs):
    """
    ======================================================================
    Post-processing for EV-only optimization
    ======================================================================
    Extracts results for all EVs:
    - Pch (charging)
    - Pdis (discharging)
    - Pnet (net power)
    - Prices and cost summary
    Saves them in separate Excel sheets.
    ======================================================================
    """

    l_t = AllInputs.System.l_t
    l_Mev = AllInputs.EV.smart.l_Mev


    #  Extract values safely

    results = {
        'Pch': {(Mev, t): pyo.value(instance.Pch[Mev, t]) for Mev in l_Mev for t in l_t},
        'Pdis': {(Mev, t): pyo.value(instance.Pdis[Mev, t]) for Mev in l_Mev for t in l_t},
        'Pnet': {(Mev, t): pyo.value(instance.Pnet[Mev, t]) for Mev in l_Mev for t in l_t},
    }

    # Prices
    price_buy = [pyo.value(instance.price_buy[t]) for t in l_t]
    price_sell = [pyo.value(instance.price_sell[t]) for t in l_t]


    #  EV operation results

    rows = []
    for Mev in l_Mev:
        for t in l_t:
            rows.append({
                "EV_id": Mev,
                "timestep": t,
                "Pch [kW]": results['Pch'][(Mev, t)],
                "Pdis [kW]": results['Pdis'][(Mev, t)],
                "Pnet [kW]": results['Pnet'][(Mev, t)],
                "Buy_price [€/kWh]": price_buy[t],
                "Sell_price [€/kWh]": price_sell[t],
            })
    df_ev = pandas.DataFrame(rows)

    # Pivot: timesteps × EVs
    df_pivot = df_ev.pivot(index="timestep", columns="EV_id",
                           values=["Pch [kW]", "Pdis [kW]", "Pnet [kW]"])


    #  Summary per EV

    ev_summary = []
    inc_t = AllInputs.System.inc_t
    for Mev in l_Mev:
        total_charge = sum(results['Pch'][(Mev, t)] * inc_t for t in l_t)
        total_dis = sum(results['Pdis'][(Mev, t)] * inc_t for t in l_t)
        net_energy = total_charge - total_dis
        ev_summary.append({
            "EV_id": Mev,
            "Total charged [kWh]": total_charge,
            "Total discharged [kWh]": total_dis,
            "Net energy [kWh]": net_energy
        })
    df_summary = pandas.DataFrame(ev_summary)


    #  Save to Excel

    with pandas.ExcelWriter(save_folder + "EV_Results.xlsx") as writer:
        df_pivot.to_excel(writer, sheet_name="EV_Power", float_format="%.3f")
        df_ev.to_excel(writer, sheet_name="EV_Detailed", float_format="%.3f", index=False)
        df_summary.to_excel(writer, sheet_name="EV_Summary", float_format="%.3f", index=False)

    print("EV-only results saved to 'EV_Results.xlsx' in", save_folder)
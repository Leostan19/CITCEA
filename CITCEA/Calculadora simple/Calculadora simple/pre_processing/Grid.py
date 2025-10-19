'''
Name of the territory, name of the month, day of the week, and holidays are in Spanish.
The tariff periods for both energy and power are only defined for inc_t = 1 for now.
'''

import math


def dict_periods(tariff_periods, territory, l_t, inc_t, name_days):
    '''
    This function translates the Spanish regulation of tariff periods to a variable (dictionary) that implements them in the optimization
    :param tariff_periods: 2 or 3 or 6 // indicates the number of periors that the corresponding power or energy term considers
    :param territory: 'Peninsula' or 'Canarias' or 'Baleares' or 'Ceuta' or 'Melilla'
    :param l_t: ``list`` containing all time-steps
    :param inc_t: time-step magnitude [h]
    :param name_days: DataFrame with the month, day of the week and (national) holiday in each time-step
        // filas = l_t
        // column 'mes': 'Enero', 'Febrero', ...
        // column 'dia': 'Lunes', 'Martes', ...
        // column 'festivo': 'Sí', 'No'
    :return: dictionary that indicates the tariff period N to be applied in the time-step t. dict_K[N,t]=value. 1: yes, 0: no
    '''

    # -------------------------------------------------------------------------------------------- #

    if tariff_periods == 2:
        dict_K_peak = {}  # punta
        dict_K_offpeak = {}  # valle

        n_days = (l_t[-1] + 1) * inc_t / 24
        for dia in range(int(n_days)):  # day from 0 to 364
            t_previous = dia * 24 / inc_t  # t at which the previous day ends
            if name_days['dia'][t_previous] == 'Sábado' or name_days['dia'][t_previous] == 'Domingo':
                # current day is weekend
                for t in range(int(24 / inc_t)):
                    dict_K_offpeak[t_previous + t] = 1
                    dict_K_peak[t_previous + t] = 0
            elif name_days['festivo'][t_previous] == 'Sí':  # the current day is holiday
                for t in range(int(24 / inc_t)):
                    dict_K_offpeak[t_previous + t] = 1
                    dict_K_peak[t_previous + t] = 0
            else:  # Monday to Friday and working days
                for t in range(int(24/inc_t)):
                    if t < 8/inc_t:  # for the current day, before 8 in the morning
                        dict_K_offpeak[t_previous + t] = 1
                        dict_K_peak[t_previous + t] = 0
                    else:
                        dict_K_offpeak[t_previous + t] = 0
                        dict_K_peak[t_previous + t] = 1
        dict_K_P1 = dict_K_peak
        dict_K_P2 = dict_K_offpeak
        dict_K_P3 = {t: 0 for t in l_t}
        dict_K_P4 = {t: 0 for t in l_t}
        dict_K_P5 = {t: 0 for t in l_t}
        dict_K_P6 = {t: 0 for t in l_t}

    # -------------------------------------------------------------------------------------------- #

    elif tariff_periods == 3:
        dict_K_peak = {}
        dict_K_llano = {}
        dict_K_offpeak = {}

        n_days = (l_t[-1] + 1) * inc_t / 24
        for dia in range(int(n_days)):  # day from 0 to 364
            t_previous = dia * 24 / inc_t  # t at which the previous day ends
            if name_days['dia'][t_previous] == 'Sábado' or name_days['dia'][t_previous] == 'Domingo':
                # current day is weekend
                for t in range(int(24/inc_t)):
                    dict_K_peak[t_previous + t] = 0
                    dict_K_llano[t_previous + t] = 0
                    dict_K_offpeak[t_previous + t] = 1
            elif name_days['festivo'][t_previous] == 'Sí':  # the current day is holiday
                for t in range(int(24/inc_t)):
                    dict_K_peak[t_previous + t] = 0
                    dict_K_llano[t_previous + t] = 0
                    dict_K_offpeak[t_previous + t] = 1
            else:  # Monday to Friday and working days
                if territory == 'Ceuta' or territory == 'Melilla':
                    for t in range(int(24/inc_t)):
                        if t < 8/inc_t:  # for the current day, before 8 in the morning
                            dict_K_peak[t_previous + t] = 0
                            dict_K_llano[t_previous + t] = 0
                            dict_K_offpeak[t_previous + t] = 1
                        elif t < 11/inc_t:
                            dict_K_peak[t_previous + t] = 0
                            dict_K_llano[t_previous + t] = 1
                            dict_K_offpeak[t_previous + t] = 0
                        elif t < 15/inc_t:
                            dict_K_peak[t_previous + t] = 1
                            dict_K_llano[t_previous + t] = 0
                            dict_K_offpeak[t_previous + t] = 0
                        elif t < 19/inc_t:
                            dict_K_peak[t_previous + t] = 0
                            dict_K_llano[t_previous + t] = 1
                            dict_K_offpeak[t_previous + t] = 0
                        elif t < 23/inc_t:
                            dict_K_peak[t_previous + t] = 1
                            dict_K_llano[t_previous + t] = 0
                            dict_K_offpeak[t_previous + t] = 0
                        else:
                            dict_K_peak[t_previous + t] = 0
                            dict_K_llano[t_previous + t] = 1
                            dict_K_offpeak[t_previous + t] = 0
                else:  # territory == 'Peninsula' or territorio == 'Baleares' or territorio == 'Canarias':
                    for t in range(int(24 / inc_t)):
                        if t < 8 / inc_t:  # for the current day, before 8 in the morning
                            dict_K_peak[t_previous + t] = 0
                            dict_K_llano[t_previous + t] = 0
                            dict_K_offpeak[t_previous + t] = 1
                        elif t < 10 / inc_t:
                            dict_K_peak[t_previous + t] = 0
                            dict_K_llano[t_previous + t] = 1
                            dict_K_offpeak[t_previous + t] = 0
                        elif t < 14 / inc_t:
                            dict_K_peak[t_previous + t] = 1
                            dict_K_llano[t_previous + t] = 0
                            dict_K_offpeak[t_previous + t] = 0
                        elif t < 18 / inc_t:
                            dict_K_peak[t_previous + t] = 0
                            dict_K_llano[t_previous + t] = 1
                            dict_K_offpeak[t_previous + t] = 0
                        elif t < 22 / inc_t:
                            dict_K_peak[t_previous + t] = 1
                            dict_K_llano[t_previous + t] = 0
                            dict_K_offpeak[t_previous + t] = 0
                        else:
                            dict_K_peak[t_previous + t] = 0
                            dict_K_llano[t_previous + t] = 1
                            dict_K_offpeak[t_previous + t] = 0

        dict_K_P1 = dict_K_peak
        dict_K_P2 = dict_K_llano
        dict_K_P3 = dict_K_offpeak
        dict_K_P4 = {t: 0 for t in l_t}
        dict_K_P5 = {t: 0 for t in l_t}
        dict_K_P6 = {t: 0 for t in l_t}
        ...

    # -------------------------------------------------------------------------------------------- #

    elif tariff_periods == 6:
        dict_temporada = {}

        if territory == 'Canarias':
            for t in l_t:
                mes_actual = name_days['mes'][t]
                if mes_actual == 'Enero' or mes_actual == 'Febrero' or mes_actual == 'Marzo':
                    dict_temporada[t] = 'media'
                elif mes_actual == 'Abril' or mes_actual == 'Mayo' or mes_actual == 'Junio':
                    dict_temporada[t] = 'baja'
                elif mes_actual == 'Noviembre' or mes_actual == 'Diciembre':
                    dict_temporada[t] = 'media-alta'
                else:  # Julio, Agosto, Septiembre, Octubre
                    dict_temporada[t] = 'alta'
        elif territory == 'Baleares':
            for t in l_t:
                mes_actual = name_days['mes'][t]
                if mes_actual == 'Marzo' or mes_actual == 'Abril' or mes_actual == 'Noviembre':
                    dict_temporada[t] = 'baja'
                elif mes_actual == 'Diciembre' or mes_actual == 'Enero' or mes_actual == 'Febrero':
                    dict_temporada[t] = 'media'
                elif mes_actual == 'Mayo' or mes_actual == 'Octubre':
                    dict_temporada[t] = 'media-alta'
                else:   # Junio, Julio, Agosto, Septiembre
                    dict_temporada[t] = 'alta'
        elif territory == 'Ceuta':
            for t in l_t:
                mes_actual = name_days['mes'][t]
                if mes_actual == 'Abril' or mes_actual == 'Mayo' or mes_actual == 'Junio':
                    dict_temporada[t] = 'baja'
                elif mes_actual == 'Marzo' or mes_actual == 'Noviembre' or mes_actual == 'Diciembre':
                    dict_temporada[t] = 'media'
                elif mes_actual == 'Julio' or mes_actual == 'Octubre':
                    dict_temporada[t] = 'media-alta'
                else:  # Enero, Febrero, Agosto, Septiembre
                    dict_temporada[t] = 'alta'
        elif territory == 'Melilla':
            for t in l_t:
                mes_actual = name_days['mes'][t]
                if mes_actual == 'Marzo' or mes_actual == 'Abril' or mes_actual == 'Mayo':
                    dict_temporada[t] = 'baja'
                elif mes_actual == 'Junio' or mes_actual == 'Octubre' or mes_actual == 'Noviembre':
                    dict_temporada[t] = 'media'
                elif mes_actual == 'Febrero' or mes_actual == 'Diciembre':
                    dict_temporada[t] = 'media-alta'
                else:  # Enero, Julio, Agosto, Septiembre
                    dict_temporada[t] = 'alta'
        else:  # territorio == 'Peninsula'
            for t in l_t:
                mes_actual = name_days['mes'][t]
                if mes_actual == 'Abril' or mes_actual == 'Mayo' or mes_actual == 'Octubre':
                    dict_temporada[t] = 'baja'
                elif mes_actual == 'Junio' or mes_actual == 'Agosto' or mes_actual == 'Septiembre':
                    dict_temporada[t] = 'media'
                elif mes_actual == 'Marzo' or mes_actual == 'Noviembre':
                    dict_temporada[t] = 'media-alta'
                else:  # Enero, Febrero, Julio, Diciembre
                    dict_temporada[t] = 'alta'

        dict_K_P1 = {t: 0 for t in l_t}
        dict_K_P2 = {t: 0 for t in l_t}
        dict_K_P3 = {t: 0 for t in l_t}
        dict_K_P4 = {t: 0 for t in l_t}
        dict_K_P5 = {t: 0 for t in l_t}
        dict_K_P6 = {t: 0 for t in l_t}

        n_days = (l_t[-1] + 1) * inc_t / 24
        for dia in range(int(n_days)):  # day from 0 to 364
            t_previous = dia * 24 / inc_t
            if name_days['dia'][t_previous] == 'Sábado' or name_days['dia'][t_previous] == 'Domingo':
                for t in range(int(24 / inc_t)):
                    dict_K_P6[t_previous + t] = 1
            elif name_days['festivo'][t_previous] == 'Sí':  # holidays
                for t in range(int(24 / inc_t)):
                    dict_K_P6[t_previous + t] = 1
            else:  # Monday to Friday and working days
                if territory == 'Canarias':
                    if dict_temporada[t_previous] == 'baja':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P5[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 18/inc_t:
                                dict_K_P5[t_previous + t] = 1
                            elif t < 22/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            else:
                                dict_K_P5[t_previous + t] = 1
                    elif dict_temporada[t_previous] == 'media':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            elif t < 18/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 22/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            else:
                                dict_K_P4[t_previous + t] = 1
                    elif dict_temporada[t_previous] == 'media-alta':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            elif t < 18/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 22/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            else:
                                dict_K_P3[t_previous + t] = 1
                    else:  # alta
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P1[t_previous + t] = 1
                            elif t < 18/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 22/inc_t:
                                dict_K_P1[t_previous + t] = 1
                            else:
                                dict_K_P3[t_previous + t] = 1
                elif territory == 'Baleares':
                    if dict_temporada[t_previous] == 'baja':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P5[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 18/inc_t:
                                dict_K_P5[t_previous + t] = 1
                            elif t < 22/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            else:
                                dict_K_P5[t_previous + t] = 1
                    elif dict_temporada[t_previous] == 'media':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 18/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 22/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            else:
                                dict_K_P4[t_previous + t] = 1
                    elif dict_temporada[t_previous] == 'media-alta':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            elif t < 18/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 22/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            else:
                                dict_K_P3[t_previous + t] = 1
                    else:  # alta
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P1[t_previous + t] = 1
                            elif t < 18/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            elif t < 22/inc_t:
                                dict_K_P1[t_previous + t] = 1
                            else:
                                dict_K_P2[t_previous + t] = 1
                elif territory == 'Ceuta':
                    if dict_temporada[t_previous] == 'baja':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P5[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 19/inc_t:
                                dict_K_P5[t_previous + t] = 1
                            elif t < 23/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            else:
                                dict_K_P5[t_previous + t] = 1
                    elif dict_temporada[t_previous] == 'media':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            elif t < 19/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 23/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            else:
                                dict_K_P4[t_previous + t] = 1
                    elif dict_temporada[t_previous] == 'media-alta':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            elif t < 19/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 23/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            else:
                                dict_K_P3[t_previous + t] = 1
                    else:  # alta
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P1[t_previous + t] = 1
                            elif t < 19/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 23/inc_t:
                                dict_K_P1[t_previous + t] = 1
                            else:
                                dict_K_P4[t_previous + t] = 1
                elif territory == 'Melilla':
                    if dict_temporada[t_previous] == 'baja':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P5[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 19/inc_t:
                                dict_K_P5[t_previous + t] = 1
                            elif t < 23/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            else:
                                dict_K_P5[t_previous + t] = 1
                    elif dict_temporada[t_previous] == 'media':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 19/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 23/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            else:
                                dict_K_P4[t_previous + t] = 1
                    elif dict_temporada[t_previous] == 'media-alta':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            elif t < 19/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 23/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            else:
                                dict_K_P3[t_previous + t] = 1
                    else:  # alta
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 10/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            elif t < 15/inc_t:
                                dict_K_P1[t_previous + t] = 1
                            elif t < 19/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            elif t < 23/inc_t:
                                dict_K_P1[t_previous + t] = 1
                            else:
                                dict_K_P2[t_previous + t] = 1
                else:  # Peninsula
                    if dict_temporada[t_previous] == 'baja':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 9/inc_t:
                                dict_K_P5[t_previous + t] = 1
                            elif t < 14/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 18/inc_t:
                                dict_K_P5[t_previous + t] = 1
                            elif t < 22/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            else:
                                dict_K_P5[t_previous + t] = 1
                    elif dict_temporada[t_previous] == 'media':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 9/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 14/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 18/inc_t:
                                dict_K_P4[t_previous + t] = 1
                            elif t < 22/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            else:
                                dict_K_P4[t_previous + t] = 1
                    elif dict_temporada[t_previous] == 'media-alta':
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 9/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 14/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            elif t < 18/inc_t:
                                dict_K_P3[t_previous + t] = 1
                            elif t < 22/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            else:
                                dict_K_P3[t_previous + t] = 1
                    else:  # alta
                        for t in range(int(24 / inc_t)):
                            if t < 8/inc_t:
                                dict_K_P6[t_previous + t] = 1
                            elif t < 9/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            elif t < 14/inc_t:
                                dict_K_P1[t_previous + t] = 1
                            elif t < 18/inc_t:
                                dict_K_P2[t_previous + t] = 1
                            elif t < 22/inc_t:
                                dict_K_P1[t_previous + t] = 1
                            else:
                                dict_K_P2[t_previous + t] = 1

    # -------------------------------------------------------------------------------------------- #

    else:  # other tariffs can be added
        dict_K_P1 = {t: 0 for t in l_t}
        dict_K_P2 = {t: 0 for t in l_t}
        dict_K_P3 = {t: 0 for t in l_t}
        dict_K_P4 = {t: 0 for t in l_t}
        dict_K_P5 = {t: 0 for t in l_t}
        dict_K_P6 = {t: 0 for t in l_t}

    dict_K_P = {}
    for t in l_t:
        dict_K_P[(0, t)] = dict_K_P1[t]
        dict_K_P[(1, t)] = dict_K_P2[t]
        dict_K_P[(2, t)] = dict_K_P3[t]
        dict_K_P[(3, t)] = dict_K_P4[t]
        dict_K_P[(4, t)] = dict_K_P5[t]
        dict_K_P[(5, t)] = dict_K_P6[t]

    # -------------------------------------------------------------------------------------------- #

    return dict_K_P


##################################################################################


def dict_K_P_hired(Tariff, territory, l_t, inc_t, name_days):
    '''
    This function translates the Spanish regulation of hired power tariff periods to a variable (dictionary) that implements them in the optimization
    :param Tariff: '2.0TD' or '3.0TD' or '6.1TD' or '6.2TD' or '6.3TD' or '6.4TD' // indicates the contracted tariff
    :param territory: 'Peninsula' or 'Canarias' or 'Baleares' or 'Ceuta' or 'Melilla'
    :param l_t: ``list`` containing all time-steps
    :param inc_t: time-step magnitude [h]
    :param name_days: DataFrame with the month, day of the week and (national) holiday in each time-step
        // filas = l_t
        // column 'mes': 'Enero', 'Febrero', ...
        // column 'dia': 'Lunes', 'Martes', ...
        // column 'festivo': 'Sí', 'No'
    :return: dictionary that indicates the tariff period N to be applied in the time-step t. dict_K_P[N,t]=value. 1: yes, 0: no
    '''

    if Tariff == '2.0TD':
        power_periods = 2
    else:
        power_periods = 6
    dict_K_P = dict_periods(power_periods, territory, l_t, inc_t, name_days)

    return dict_K_P


def dict_K_Energia(Tariff, territory, l_t, inc_t, name_days):
    '''
    This function translates the Spanish regulation of energy (access) tariff periods to a variable (dictionary) that implements them in the optimization
    :param Tariff: '2.0TD' or '3.0TD' or '6.1TD' or '6.2TD' or '6.3TD' or '6.4TD' // indicates the contracted tariff
    :param territory: 'Peninsula' or 'Canarias' or 'Baleares' or 'Ceuta' or 'Melilla'
    :param l_t: ``list`` containing all time-steps
    :param inc_t: time-step magnitude [h]
    :param name_days: DataFrame with the month, day of the week and (national) holiday in each time-step
        // filas = l_t
        // column 'mes': 'Enero', 'Febrero', ...
        // column 'dia': 'Lunes', 'Martes', ...
        // column 'festivo': 'Sí', 'No'
    :return: dictionary that indicates the tariff period N to be applied (energy access cost) in the time-step t. dict_K_E[N,t]=value. 1: yes, 0: no
    '''

    if Tariff == '2.0TD':
        energy_periods = 3
    else:
        energy_periods = 6
    dict_K_E = dict_periods(energy_periods, territory, l_t, inc_t, name_days)

    return dict_K_E


##################################################################################


def Cost_buy_grid(Tariff, type_,
                  fix_cost, period_cost, annual_market_cost_DataFrame, market_fee, annual_cost_DataFrame,
                  access_cost_DataFrame, l_t, dict_K_E):
    '''
    Obtains the buy energy price for the optimization
    :param Tariff: '2.0TD' or '3.0TD' or '6.1TD' or '6.2TD' or '6.3TD' or '6.4TD' // indicates the contracted tariff
    :param type_: 'Fix' or 'By period' or 'Annual' or 'Upload'
    :param fix_cost: fixed energy price for all time-steps
    :param period_cost: pandas Series with the energy price for each tariff period
    :param annual_market_cost_DataFrame: pandas Series with the market energy price for each time-step
    :param market_fee: extra cost from the market, applied to each time-step
    :param annual_cost_DataFrame: pandas Series with the energy price defined by the user for each time-step
    :param access_cost_DataFrame: pandas DataFrame with the energy access prices for each tariff period defined in the Spanish regulation
    :param l_t: ``list`` containing all time-steps
    :param dict_K_E: dictionary that indicates the tariff period N to be applied (energy access cost) in the time-step t. dict_K_E[N,t]=value. 1: yes, 0: no
    :return: dictionary with the total energy buy price for each time-step [€/kWh]
    '''
    l_N = range(6)
    if type_ == 'Fix':
        cost_buy = {t: fix_cost for t in l_t}
    elif type_ == 'By period':
        cost_buy = {t: sum(period_cost[N]*dict_K_E[N, t] for N in l_N) for t in l_t}  # period_cost = client_periods['P1':'P6']['Energy Cost [€/kWh]']
    elif type_ == 'Annual':  # market cost
        cost_buy = {t: annual_market_cost_DataFrame[t]/1000 + market_fee for t in l_t}  # cost_buy = market price [€/MWh] + fee [€/kWh]
    else:  # Upload
        cost_buy = {t: annual_cost_DataFrame[t] for t in l_t}  # annual_DataFrame = time_data['Energy Purchase Price [€/kWh]']
    access_cost = {t: sum(access_cost_DataFrame.loc['Cost P1':'Cost P6'][Tariff][N] * dict_K_E[N, t] for N in l_N) for t in l_t}
    cost_total = {t: cost_buy[t]+access_cost[t] for t in l_t}
    return cost_total


def Cost_venta_grid(type_, fix_cost, period_cost, annual_market_cost_DataFrame, market_fee, annual_cost_DataFrame, l_t, dict_K_E):
    '''
    Obtains the sell energy price for the optimization
    :param type_: 'Fix' or 'By period' or 'Annual' or 'Upload'
    :param fix_cost: fixed energy price for all time-steps
    :param period_cost: pandas Series with the energy price for each tariff period
    :param annual_market_cost_DataFrame: pandas Series with the market energy price for each time-step
    :param market_fee: extra cost from the market, applied to each time-step
    :param annual_cost_DataFrame: pandas Series with the energy price defined by the user for each time-step
    :param l_t: ``list`` containing all time-steps
    :param dict_K_E: dictionary that indicates the tariff period N to be applied (energy access cost) in the time-step t. dict_K_E[N,t]=value. 1: yes, 0: no
    :return: dictionary with the total energy sell price for each time-step [€/kWh]
    '''
    l_N = range(6)
    if type_ == 'Fix':
        cost_sell = {t: fix_cost for t in l_t}
    elif type_ == 'By period':
        cost_sell = {t: sum(period_cost[N] * dict_K_E[N, t] for N in l_N) for t in l_t}  # period_cost = client_periods['P1':'P6']['Energy Revenues [€/kWh]']
    elif type_ == 'Annual':  # market cost
        cost_sell = {t: annual_market_cost_DataFrame[t] / 1000 - market_fee for t in l_t}  # cost_sell = market price [€/MWh] - fee [€/kWh]
    else:  # Upload
        cost_sell = {t: annual_cost_DataFrame[t] for t in l_t}  # annual_DataFrame = time_data['Energy Sale Price [€/kWh]']
    return cost_sell


def add_dict_key(dict,new_key):
    new_dict = {}
    for k in dict.keys():
        if type(k) == int:
            k_tuple=(k,)
        else:
            k_tuple=k
        new_k = (new_key,)+k_tuple
        new_dict.update({new_k:dict[k]})
    return new_dict

##################################################################################


class GridClass:
    '''
    Class with all the inputs of the Grid connection
    '''
    def __init__(self, conected1_islanded0):
        self.id = 0  # number of the PV system
        self.id_list = []  # list with all PV system numbers
        self.name = {}  # name of the PV system
        self.pos_bus = {}  # binary that indicates the bus to which the load is connected --> [id_load,id_bus]=1

        self.conected1_islanded0 = conected1_islanded0  # binary that indicates if the microgrid is connected to the grid or islanded. 1: connected, 0: islanded
        self.l_N = list(range(6))

        # General data of the grid connection
        self.Territory = {}  # 'Peninsula' or 'Canarias' or 'Baleares' or 'Ceuta' or 'Melilla'
        self.Tariff = {}  # '2.0TD' or '3.0TD' or '6.1TD' or '6.2TD' or '6.3TD' or '6.4TD'
        self.meter_type = {}  # type of meter: 1 or 2 or 3 or 4 or 5
        self.injection = {}  # binary that indicates the client willingness to inject power to the grid. 1: yes under some conditions, 0: never
        self.Plim_injection = {}  # maximum PV power installed to enable grid injection [kW]

        # Excess power penalisations (Spanish regulation, BOE)
        self.cost_Pexcess45 = {}  # price of the excess power term with meters 4 and 5 [€/kW]
        self.cost_Pexcess123 = {}  # price of the excess power term with meters 1, 2 and 3 [€/kW]
        self.CoefK_cost_Pexcess = {}  # coefficient of the excess power term with meters 1, 2 and 3

        # Hired power term cost (Spanish regulation, BOE)
        self.Cost_power = {}  # price of the hired power term [€/(kW*year)]
        self.K_P = {}  # dictionary that indicates the tariff period N to be applied in the time-step t. dict_K_P[N,t]=value. 1: yes, 0: no

        # Fix hired power
        self.fix = {}  # 0:no, 1:yes
        self.fix_Hired_power = {}  # fixed hired power [kW]
        self.Hired_power = {}  # hired power currently [kW]

        # Energy cost (defined by the client or market + BOE access term)
        self.K_E = {}  # dictionary that indicates the tariff period N to be applied (energy access cost) in the time-step t. dict_K_E[N,t]=value. 1: yes, 0: no
        self.Cost_P_buy_grid = {}  # dictionary with the total energy buy price for each time-step [€/kWh]
        self.Cost_P_sell_grid = {}  # dictionary with the total energy sell price for each time-step [€/kWh]

        # Emissions and renewables
        self.emissions = {}  # emission factor [tCO2/MWh=kgCO2/kWh]
        self.renewable_factor = {}

        # Optional, grid hard power limit [kW]
        self.hard_Plim = {}


    def add(self, id, name, bus, l_bus,
            territory, tariff, meter_type,
            injection, Plim_injection,
            penalizaciones_DataFrame, costPotencia_DataFrame,
            l_t, inc_t, name_days,
            hired_power_DataFrame, hard_power_limit, fix_hired_power,
            buy_price_type, buy_price_fix, buy_price_fee, buy_price_periods_DataFrame, buy_price_DataFrame,
            sell_price_type, sell_price_fix, sell_price_fee, sell_price_periods_DataFrame, sell_price_DataFrame,
            market_cost, market_income, BOE_cost_energy,
            emissions_renewables_type, grid_emissions_DataFrame, grid_renewables_DataFrame,
            national_grid_emissions_DataFrame, national_renewable_generation_DataFrame, national_demand_DataFrame):
        '''
        Class with all the inputs of the Grid connection
        :param id:
        :param name:
        :param bus:
        :param l_bus: list with the id of all the buses
        :param territory:
        :param tariff:
        :param meter_type:
        :param injection:
        :param Plim_injection:
        :param penalizaciones_DataFrame:
        :param costPotencia_DataFrame:
        :param l_t: ``list`` containing all time-steps
        :param inc_t: time-step magnitude [h]
        :param name_days: DataFrame with the month, day of the week and (national) holiday in each time-step
            // filas = l_t
            // column 'mes': 'Enero', 'Febrero', ...
            // column 'dia': 'Lunes', 'Martes', ...
            // column 'festivo': 'Sí', 'No'
        :param hired_power_DataFrame:
        :param hard_power_limit:
        :param fix_hired_power:
        :param buy_price_type:
        :param buy_price_fix:
        :param buy_price_fee:
        :param buy_price_periods_DataFrame:
        :param buy_price_DataFrame:
        :param sell_price_type:
        :param sell_price_fix:
        :param sell_price_fee:
        :param sell_price_periods_DataFrame:
        :param sell_price_DataFrame:
        :param market_cost: pandas DataFrame with the market buy energy price for each time-step
        :param market_income: pandas DataFrame with the market sell energy price for each time-step
        :param BOE_cost_energy: pandas DataFrame with the energy access prices for each tariff period defined in the Spanish regulation
        :param emissions_renewables_type:
        :param grid_emissions_DataFrame: emission factor for each t [kgCO2/kWh]
        :param grid_renewables_DataFrame: renewables share for each t [pu]
        :param national_grid_emissions_DataFrame: emission factor for each t from the national grid [kgCO2/kWh]
        :param national_renewable_generation_DataFrame: total renewable generation [MWh]
        :param national_demand_DataFrame: total demand [MWh]
        :return:
        '''
        '''
        :param client_DataFrame: pandas Dataframe with general grid connection data (defined by the client), excel format
        :param penalizaciones_DataFrame: pandas DataFrame with the costs and coefficients for the hired power penalizations (BOE), excel format
        :param costPotencia_DataFrame: pands DataFrame with the hired power costs for each tariff period (BOE), excel format
        :param periods_DataFrame: pandas DataFrame with the current hired power and energy prices for each tariff period (defined by the client), excel format
        :param time_data: pandas DataFrame with several time-step data (defined by the client), excel format
        '''

        self.id = id  # number of the PV system
        self.id_list.append(id)  # list with all PV system numbers
        self.name[id] = name  # name of the PV system

        pos = {(self.id, bus_aux): 0 for bus_aux in l_bus}
        pos[self.id, bus] = 1
        self.pos_bus.update(pos)

        # General data of the grid connection
        self.Territory[id] = territory  # 'Peninsula' or 'Canarias' or 'Baleares' or 'Ceuta' or 'Melilla'
        self.Tariff[id] = tariff  # '2.0TD' or '3.0TD' or '6.1TD' or '6.2TD' or '6.3TD' or '6.4TD'
        self.meter_type[id] = meter_type  # type of meter: 1 or 2 or 3 or 4 or 5
        self.injection[id] = injection  # binary that indicates the client willingness to inject power to the grid. 1: yes under some conditions, 0: never
        self.Plim_injection[id] = Plim_injection  # maximum PV power installed to enable grid injection [kW]

        # Excess power penalisations (Spanish regulation, BOE)
        self.cost_Pexcess45[id] = penalizaciones_DataFrame.loc['Price of the excess power term (4,5)'][tariff]  # price of the excess power term with meters 4 and 5 [€/kW]
        self.cost_Pexcess123[id] = penalizaciones_DataFrame.loc['Price of the excess power term (1,2,3)'][tariff]  # price of the excess power term with meters 1, 2 and 3 [€/kW]
        # if self.Tariff == '2.0TD':
        #     self.l_N = list(range(2))
        # else:
        #     self.l_N = list(range(6))
        self.CoefK_cost_Pexcess.update({(id, N): penalizaciones_DataFrame.loc['Kp 1':'Kp 6'][tariff][N] for N in self.l_N})  # coefficient of the excess power term with meters 1, 2 and 3

        # Hired power term cost (Spanish regulation, BOE)
        self.Cost_power.update({(id, N): costPotencia_DataFrame.loc['Cost P1':'Cost P6'][tariff][N] for N in self.l_N})  # price of the hired power term [€/(kW*year)]
        self.Hired_power.update({(id, N): hired_power_DataFrame[N] for N in self.l_N})  # hired power currently [kW]
        K_P = dict_K_P_hired(tariff, territory, l_t, inc_t, name_days)  # dictionary that indicates the tariff period N to be applied in the time-step t. dict_K_P[N,t]=value. 1: yes, 0: no
        self.K_P.update(add_dict_key(K_P, id))  # dict_K_P[id,N,t]

        # Fix hired power
        self.fix[id] = fix_hired_power  # 0:no, 1:yes
        self.fix_Hired_power.update({(id, N): hired_power_DataFrame[N] for N in self.l_N})  # fixed hired power [kW]

        # Energy cost (defined by the client or market + BOE access term)
        K_E = dict_K_Energia(tariff, territory, l_t, inc_t, name_days)  # dictionary that indicates the tariff period N to be applied (energy access cost) in the time-step t. dict_K_E[N,t]=value. 1: yes, 0: no
        self.K_E.update(add_dict_key(K_E, id))  # dict_K_E[id,N,t]
        Cost_P_buy_grid = Cost_buy_grid(tariff, buy_price_type, buy_price_fix, buy_price_periods_DataFrame,
                                        market_cost['value'], buy_price_fee, buy_price_DataFrame, BOE_cost_energy, l_t,
                                        K_E)  # dictionary with the total energy buy price for each time-step [€/kWh]
        self.Cost_P_buy_grid.update(add_dict_key(Cost_P_buy_grid, id))
        Cost_P_sell_grid = Cost_venta_grid(sell_price_type, sell_price_fix, sell_price_periods_DataFrame,
                                           market_income['value'], sell_price_fee, sell_price_DataFrame, l_t,
                                           K_E)  # dictionary with the total energy sell price for each time-step [€/kWh]
        self.Cost_P_sell_grid.update(add_dict_key(Cost_P_sell_grid, id))

        # Emissions and renewables
        if emissions_renewables_type == 1: # spanish national grid
            self.emissions.update({(id,t): national_grid_emissions_DataFrame['value'][t] for t in l_t})  # emission factor [tCO2/MWh=kgCO2/kWh]
            self.renewable_factor.update({(id,t): national_renewable_generation_DataFrame['value'][t] / national_demand_DataFrame['value'][t] for t in l_t})
        else: # from time-series
            self.emissions.update({(id, t): grid_emissions_DataFrame[t] for t in l_t})
            self.renewable_factor.update({(id, t): grid_renewables_DataFrame[t] for t in l_t})

        # Optional, grid hard power limit [kW]
        if math.isnan(hard_power_limit):
            self.hard_Plim[id] = float('nan')
        else:
            self.hard_Plim[id] = hard_power_limit

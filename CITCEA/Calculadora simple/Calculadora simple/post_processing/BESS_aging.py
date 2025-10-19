def BESS_cycles(allResults, AllInputs):

    l_t = AllInputs.System.l_t
    l_BESS = AllInputs.BESS.id_list

    P = {(i_BESS, t): allResults.BESS.P_char[i_BESS, t] - allResults.BESS.P_disch[i_BESS, t] for i_BESS in l_BESS for t in l_t}
    state = {}
    for i_BESS in l_BESS:
        for t in l_t:
            if P[i_BESS, t] > 0:
                state[i_BESS, t] = 'carga'
            elif P[i_BESS, t] < 0:
                state[i_BESS, t] = 'descarga'
            else:
                if t == l_t[0]:
                    state[i_BESS, t] = 'carga'  # hipothesis: the first state is charging
                else:
                    state[i_BESS, t] = state[i_BESS, t-1]

    cycle = {}
    for i_BESS in l_BESS:
        for t in l_t[:-1]:
            if state[i_BESS, t] == 'carga' and state[i_BESS, t+1] == 'descarga':
                cycle[i_BESS, t] = 'pico'
            elif state[i_BESS, t] == 'descarga' and state[i_BESS, t+1] == 'carga':
                cycle[i_BESS, t] = 'valle'
            else:
                cycle[i_BESS, t] = 0
        if state[i_BESS, l_t[-1]] == 'carga' and state[i_BESS, l_t[0]] == 'descarga':
            cycle[i_BESS, t] = 'pico'
        elif state[i_BESS, l_t[-1]] == 'descarga' and state[i_BESS, l_t[0]] == 'carga':
            cycle[i_BESS, t] = 'valle'
        else:
            cycle[i_BESS, t] = 0

    return cycle


def count_peaks(cycles):
    n_peaks = sum(1 for v in cycles.values() if v == 'pico')
    n_valls = sum(1 for v in cycles.values() if v == 'valle')
    return n_peaks


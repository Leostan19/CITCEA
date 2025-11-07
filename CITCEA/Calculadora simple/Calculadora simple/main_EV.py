'''
Author: Paula Muñoz Peña / Modified for EV-only testing by Varun Venugopalan
Objective: Sizing and operation optimization of a microgrid (EV-only mode)
'''

import time
import os
import pyomo.environ as pyo

# IMPORT THE EV-ONLY MODULES
from opti_EV_1 import optimization
from post_EV import post_processing
from pre_process import AllInputs

if __name__ == '__main__':
    print('#####  OptuGrid: EV-only optimization mode #####')
    print()
    begin = time.time()

    # 1. Pre-processing
    print('Processing the inputs ... ', end='')
    # AllInputs is already initialized in pre_process
    print('OK')
    end = time.time()
    print('Time: ', format((end - begin) / 60, '.2f'), 'min')
    print()

    EV_smart = AllInputs.EV.smart
    l_t = AllInputs.System.l_t
    l_Mev = EV_smart.l_Mev

    # K_evMev_t is a dictionary {(Mev, t): 0/1}
    K = EV_smart.K_evMev_t

    # count how many timesteps each EV is connected
    for Mev in l_Mev[:35]:
        connected_hours = sum(K[Mev, t] for t in l_t)
        print(f"EV {Mev}: connected {connected_hours} hours out of {len(l_t)}")

    # optionally check one EV's connection pattern (first 50 timesteps)
    sample_Mev = l_Mev[0]
    availability = [K[sample_Mev, t] for t in l_t[:50]]
    print(f"\nEV {sample_Mev} first 50 timesteps:\n{availability}")

    # 2. Define solver
    solver = 'gurobi'

    # 3. Create results folder if missing
    folder_results = 'CSV/Results_EVonly/'
    if not os.path.exists(folder_results):
        os.mkdir(folder_results)

    # 4. Run optimization
    print('Running EV-only optimization ... ', end='')
    instance = optimization(AllInputs)
    opt = pyo.SolverFactory(solver)
    if solver == 'gurobi':
        opt.options['NonConvex'] = 2
    results = opt.solve(instance)

    # 5. Solver termination check
    termination_condition = str(results.solver.termination_condition)
    if termination_condition.lower().startswith('optimal'):
        print('OK (Optimal Solution Found)')
    else:
        print(f'Warning: Solver status - {termination_condition}')

    # 6. Post-processing
    print('Saving results ... ', end='')
    post_processing(instance, folder_results, AllInputs)
    print('OK')

    end = time.time()
    print('Total Time: ', format((end - begin) / 60, '.2f'), 'min')
    print()
    print('Finished the EV-only optimization complete.')
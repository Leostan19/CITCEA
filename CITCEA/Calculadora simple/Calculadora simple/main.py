'''
Author: Paula Muñoz Peña
Objective: Sizing and operation optimization of a microgrid
Contact: paula.munoz.pena@upc.edu
Office:
'''

# This is a sample Python script.

# Press Mayús+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

# Before begin, install Pyomo, pandas, openpyxl, requests

import time
import os
import copy
from optimization_model import *  # importa optimization(...)
from post_process import *  # importa post_processing(...)
import pyomo.environ as pyo
import pandas

# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    print('#####  OptuGrid: microgrid design optimization tool #####')  # print('#####  Herramienta de dimensionado #####')
    print()
    begin = time.time()

    ''' Scripts order: pre_process > optimization_model > post_process'''

    # 1. Import data:7 generals of the problem, the components (PV, Bat, Genset), and the customer
    print('Processing the inputs ... ', end='')
    from pre_process import AllInputs

    # if no economic constraints wants to be considered, add here "new_constraints = []",
    # otherwise economic constraints will be based on excel inputs
    print('OK')
    end = time.time()
    print('Time: ', format((end - begin) / 60, '.2f'), 'min')
    print()

    # define the solver to use: gurobi, mindtpy, highs, scip, ...
    solver = 'gurobi'

    # Directory where results will be saved:
    folder_results = 'CSV/Results/'
    if os.path.exists(folder_results) == False:
        os.mkdir(folder_results)

    print('Running optimization ... ', end='')

    # 2. Create the model
    instance = optimization(AllInputs)
    # with open('model', 'w') as f:
    #     instance.pprint(f)

    # 3. Solve the model
    opt = pyo.SolverFactory(solver)
    if solver == 'gurobi':
        opt.options['NonConvex'] = 2  # to solve Quadratic equality constraints
    results = opt.solve(instance)  # ,tee=True)
    # results.write()  # Access to the results
    if solver == 'gurobi':
        termination_condition = str(results['Solver']).split('\n')[4].split(': ')[1]
    elif solver == 'highs':
        termination_condition = str(results['Solver']).split('\n')[3].split(': ')[1]
    elif solver == 'scip':
        termination_condition = str(results['Solver']).split('\n')[3].split(': ')[1]
    else:
        termination_condition = ''
    if termination_condition == 'optimal':
        print('OK')
    elif termination_condition == 'infeasible':
        print('Optimization ERROR: '+termination_condition)

    # 4. Post-process and results saving
    print('Saving results ... ', end='')
    allResults, n_cycles = post_processing(instance, folder_results, AllInputs)
    print('OK')

    end = time.time()
    print('Time: ', format((end-begin)/60, '.2f'), 'min')
    print()


    print('Finished')


# See PyCharm help at https://www.jetbrains.com/help/pycharm/

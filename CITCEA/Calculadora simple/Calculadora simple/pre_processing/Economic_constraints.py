class AddConstraint:
    '''
    Class with an economic constraint definition
    '''
    def __init__(self, enable, variable, expression, value):
        '''
        Class with an economic constraint definition
        :param enable: binary that indicates if the constraint is applied. 1: yes, 0: no
        :param variable: 'ROI' or 'payback' or 'investment'
        :param expression: '>=' or '<=' or '=='
        :param value: float which limits the indicator
        '''
        self.enabled = enable
        self.variable = variable
        self.expression = expression
        self.value = value


'''
# imposes: ROI <= value
def_ROI_max = AddConstraint(0, 'ROI', '<=', 30)  # ROI <= 30 %

# imposes: ROI >= value (by definition, ROI could be negative)
def_ROI_min = AddConstraint(0, 'ROI', '>=', 0)  # ROI >= 0

# imposes: ROI == value
def_ROI_eq = AddConstraint(0, 'ROI', '==', 15)  # ROI == 15 %

# imposes: payback <= value
def_payback_max = AddConstraint(0, 'payback', '<=', 25)  # payback <= 25 years

# imposes: payback >= value (by definition, payback could be negative)
def_payback_min = AddConstraint(0, 'payback', '>=', 0)  # payback >= 0

# imposes: payback == value
def_payback_eq = AddConstraint(0, 'payback', '==', 15)  # payback == 15 years

# imposes: inversion <= value
def_investment_max = AddConstraint(0, 'investment', '<=', 25000)  # investment <= 25000 €

# imposes: inversion >= value (by definition, could be negative)
def_investment_min = AddConstraint(0, 'investment', '>=', 0)  # investment >= 0

# imposes: inversion == value
def_investment_eq = AddConstraint(0, 'investment', '==', 15000)  # investment == 15000 €

economic_constraints = [def_ROI_max, def_ROI_min, def_ROI_eq, def_payback_max, def_payback_min, def_payback_eq, def_investment_max, def_investment_min, def_investment_eq]
'''

def economic_constraints_list(economic_constraints_DataFrame, apply=True):
    '''
    Defines all economic constraint to use later in pyomo, according to data from excel
    :param economic_constraints_DataFrame: data from excel
    :return: class with all economic constraints
    '''

    new_constraints = []

    for row in range(len(economic_constraints_DataFrame)):
        row_constr = economic_constraints_DataFrame.loc[row]
        if apply == False:
            def_constraint = AddConstraint(0, row_constr['Variable'], row_constr['Expression'], row_constr['Value'])
        else:
            def_constraint = AddConstraint(row_constr['Enable'], row_constr['Variable'], row_constr['Expression'], row_constr['Value'])

        new_constraints.append(def_constraint)

    return new_constraints
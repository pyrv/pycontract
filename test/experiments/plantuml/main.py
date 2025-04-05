
#####################
# Trying things out #
#####################

import os

if __name__ == '__main__':
    path = '/Users/khavelun/Desktop/development/pycharmworkspace/pycontract-open-source/test/experiments/plantuml/'
    plantuml_jar = path + 'plantuml.jar'
    model_pu = path +'model.pu'
    os.system(f'java -jar {plantuml_jar} {model_pu}')
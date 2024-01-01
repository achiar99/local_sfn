
from copy import copy
import importlib
import json
import boto3
import datetime
from config import profile, region, event, sfn, resources, mocks
from parse import parse_states


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def fix_param(param, data):
    if not isinstance(param, dict):
        return
    keys_to_pop = []
    keys_to_add = {}
    for key, val in param.items():
        if key.endswith('.$'):
            keys_to_pop.append(key)
            if val.startswith('$.'):
                val = data.get(val[2:])
            keys_to_add[key[:-2]] = val

    for key in keys_to_pop:
        param.pop(key)

    for key, val in keys_to_add.items():
        param[key] = val

    for key, val in param.items():
        fix_param(val, data)

    return param


def fix_var(var, data):
    if var.startswith('$.'):
        var = var[2:]
    splits = var.split('.')
    
    temp = data
    for split in splits:
        temp = temp.get(split)
    
    return temp
    

def run_sfn(definition, data):
    states = parse_states(definition)
    start_at = definition.get('StartAt')

    current_data = data
    current_state = states[start_at]
    
    start_time = datetime.datetime.now()
    start = True
    while True:
        if not start:
            now = datetime.datetime.now()
            print(bcolors.OKCYAN + str((now-start_time).total_seconds()) + ' seconds'+ bcolors.OKCYAN)
            start_time = now
        start = False
        print(bcolors.OKBLUE + '-----------------------' + bcolors.OKBLUE)
        if current_state.type == 'Succeed':
            print(bcolors.OKGREEN + current_state.name + bcolors.OKBLUE)
        elif current_state.type == 'Fail':
            print(bcolors.FAIL + current_state.name + bcolors.OKBLUE)
        else:
            print(bcolors.OKBLUE + current_state.name + bcolors.OKBLUE)
        if current_state.type == 'Task':
            if current_state.debug:
                module_path_splits = resources[current_state.resource].split('.')
                func_name = module_path_splits[-1]
                module_path = '.'.join(module_path_splits[0:-1])
                imported_module = importlib.import_module(module_path)
                handler = getattr(imported_module, func_name)
                result = handler(current_data)
            elif current_state.mock:
                current_data = mocks[current_state.resource]
            else:
                resource = resources[current_state.resource]
                session = boto3.Session(profile_name=profile, region_name=region)
                lambda_client = session.client('lambda')
                lambda_name = resource.split(':function:')[1]
                payload = fix_param(current_state.parameters, current_data)
                lambda_response = lambda_client.invoke(FunctionName=lambda_name, Payload=json.dumps(payload))
                result = json.loads(lambda_response['Payload'].read())
            if current_state.result_path:
                current_data[current_state.result_path[2:]] = result

        if current_state.type == 'Pass':
            if current_state.result_path and current_state.result:
                current_data[current_state.result_path[2:]] = current_state.result

        if current_state.type == 'Map':
            try:
                new_data = []
                for item in fix_var(current_state.item_path, current_data):
                    p = fix_param(copy(current_state.item_selector), current_data)
                    for key, val in p.items():
                        if val == '$$.Map.Item.Value':
                            p[key] = item
                    new_data.append(run_sfn(current_state.item_processor, p))
                
                current_data = new_data
            except Exception as e:
                if current_state.catch:
                    can_continue = False
                    for cat in current_state.catch:
                        current_state = states[cat.get('Next')]
                        can_continue = True
                        break
                    if can_continue:
                        continue

        if current_state.type == 'Choice':
            can_continue = False
            for choice in current_state.choices:
                var = fix_var(choice.get('Variable'), current_data)
                if 'BooleanEquals' in choice:
                    if var == choice.get('BooleanEquals'):
                        current_state = states[choice.get('Next')]
                        can_continue = True
                        break
            if can_continue:
                continue
            current_state = states[current_state.default]
            continue

        if current_state.next:
            current_state = states[current_state.next]
            continue
        
        if current_state.end:
            break
    return current_data


if __name__ == "__main__":
    print('\n\n')
    print(bcolors.WARNING + "Input: " + str(event) +  bcolors.WARNING)
    with open(sfn) as f:
        d = json.load(f)

    output = run_sfn(d, event)
    print(bcolors.WARNING + "Output: " + str(output) +  bcolors.WARNING)
    print('\n\n')
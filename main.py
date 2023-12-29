
from copy import copy
import importlib
import json
import boto3
from resources_map import resources_map

profile = 'dev8'
region='us-west-2'


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



class State:
    def __init__(self, name, type) -> None:
        self.name = name
        self.type = type
        self.next = ''
        self.end = False
        self.debug = False


class Task(State):
    def __init__(self, name, type, resource, result_path, parameters) -> None:
        super().__init__(name, type)
        self.resource = resource
        self.result_path = result_path
        self.parameters = parameters


class Choice(State):
    def __init__(self, name, type, choices, default) -> None:
        super().__init__(name, type)
        self.choices = choices
        self.default = default


class Pass(State):
    def __init__(self, name, type) -> None:
        super().__init__(name, type)
        self.result = None
        self.result_path = None


class Success(State):
    def __init__(self, name, type) -> None:
        super().__init__(name, type)


class Fail(State):
    def __init__(self, name, type) -> None:
        super().__init__(name, type)


class Map(State):
    def __init__(self, name, type,) -> None:
        super().__init__(name, type)
        self.item_path = None
        self.item_selector = None
        self.item_processor = None
        self.catch = False


def parse_states(definition):
    states = {}
    for name, state in definition.get('States').items():
        state_type = state.get('Type')
        if state_type == 'Task':
            states[name] = Task(name=name, type=state_type, resource=state.get('Resource'), result_path=state.get('ResultPath'), parameters=state.get('Parameters'))
            states[name].next = state.get('Next', '')
            states[name].end = state.get('End', False)
            states[name].debug = state.get('Debug', False)
        if state_type == 'Choice':
            states[name] = Choice(name=name, type=state_type, choices=state.get('Choices'), default=state.get('Default'))
        if state_type == 'Pass':
            states[name] = Pass(name=name, type=state_type)
            states[name].result = state.get('Result')
            states[name].result_path = state.get('ResultPath')
            states[name].next = state.get('Next', '')
        if state_type == 'Fail':
            states[name] = Fail(name=name, type=state_type)
            states[name].end = True
        if state_type == 'Succeed':
            states[name] = Success(name=name, type=state_type)
            states[name].end = True
        if state_type == 'Map':
            states[name] = Map(name=name, type=state_type)
            states[name].item_path = state.get('ItemsPath')
            states[name].item_selector = state.get('ItemSelector')
            states[name].item_processor = state.get('ItemProcessor')
            states[name].catch = state.get('Catch')
            states[name].next = state.get('Next', '')
    return states



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
    while True:
        if current_state.type == 'Succeed':
            print(bcolors.OKGREEN + current_state.name + bcolors.OKBLUE)
        elif current_state.type == 'Fail':
            print(bcolors.FAIL + current_state.name + bcolors.OKBLUE)
        else:
            print(current_state.name)
        if current_state.type == 'Task':
            if current_state.debug:
                module_path_splits = resources_map[current_state.resource].split('.')
                func_name = module_path_splits[-1]
                module_path = '.'.join(module_path_splits[0:-1])
                imported_module = importlib.import_module(module_path)
                handler = getattr(imported_module, func_name)
                return handler(current_data)
            else:
                resource = resources_map[current_state.resource]
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
    with open('sfnDefinition.json') as f:
        d = json.load(f)

    run_sfn(d, {'customerName': 'arosenfeld85'})

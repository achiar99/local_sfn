from states import Task, Choice, Pass, Fail, Success, Map

def parse_states(definition):
    states = {}
    for name, state in definition.get('States').items():
        state_type = state.get('Type')
        if state_type == 'Task':
            states[name] = Task(name=name, type=state_type, resource=state.get('Resource'), result_path=state.get('ResultPath'), parameters=state.get('Parameters'))
            states[name].next = state.get('Next', '')
            states[name].end = state.get('End', False)
            states[name].debug = state.get('Debug', False)
            states[name].mock = state.get('Mock', False)
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

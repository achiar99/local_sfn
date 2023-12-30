class State:
    def __init__(self, name, type) -> None:
        self.name = name
        self.type = type
        self.next = ''
        self.end = False
        self.debug = False
        self.mock = False


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


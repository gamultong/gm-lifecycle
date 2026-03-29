from lifecycle import TracerManager, LifeCycle

class EXMPLifeCycle(LifeCycle[[int, int], int]):
    def __init__(self, arg:tuple):
        self.arg = arg
        self.return_value:int
        self.other_trace:str
    
    @classmethod
    def create(cls, arg1:int, arg2:int):
        return cls((arg1, arg2))
    
    def mm_return(self, return_value:int):
        self.return_value = return_value

TM = TracerManager[[int, int], int, EXMPLifeCycle](EXMPLifeCycle)

@TM.tracing
def some_func(arg1:int, arg2:int) -> int:
    instance = some_func.here()
    instance.other_trace = "trace"
    print(instance)
    print(instance.arg)

    return arg1+arg2

@some_func.add_hook
def hook(lifecycle:EXMPLifeCycle):
    print(lifecycle)
    print(lifecycle.other_trace)
    print(lifecycle.arg)
    print(lifecycle.return_value)

some_func(3, 5)

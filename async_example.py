# async_example.py
import asyncio
from lifecycle import TracerManager, LifeCycle, App

class EXMPLifeCycle(LifeCycle[[int, int], int]):
    def __init__(self):
        super().__init__()
        self.arg: tuple
        self.return_value: int
        self.trace: str
    
    @classmethod
    def create(cls, caller, arg1: int, arg2: int):
        instance = cls()
        instance.arg = (arg1, arg2)
        return instance
    
    def mm_return(self, return_value: int):
        self.return_value = return_value

app = App()
TM = TracerManager[[int, int], int, EXMPLifeCycle](EXMPLifeCycle, app)

@TM.tracing
async def outer_func(arg1: int, arg2: int) -> int:
    instance = outer_func.here()
    instance.trace = "outer"

    await asyncio.sleep(0.1)
    result = await inner_func(arg1, arg2)
    return result

@TM.tracing
async def inner_func(arg1: int, arg2: int) -> int:
    instance = inner_func.here()
    instance.trace = "inner"

    await asyncio.sleep(0.1)

    print(f"[inner] caller: {instance.caller}")
    print(f"[inner] caller.trace: {instance.caller.trace}")
    print(f"[inner] caller.arg: {instance.caller.arg}")

    return arg1 / arg2

@outer_func.add_hook
def outer_hook(lifecycle: EXMPLifeCycle):
    print(f"\n[outer_hook] arg: {lifecycle.arg}")
    print(f"[outer_hook] trace: {lifecycle.trace}")
    print(f"[outer_hook] return_value: {lifecycle.return_value}")
    print(f"[outer_hook] caller: {lifecycle.caller}")
    print(f"[outer_hook] callees: {lifecycle.callees}")
    print(f"[outer_hook] callees[0].trace: {lifecycle.callees[0].trace}")

@inner_func.add_hook
def inner_hook(lifecycle: EXMPLifeCycle):
    print(f"\n[inner_hook] arg: {lifecycle.arg}")
    print(f"[inner_hook] trace: {lifecycle.trace}")
    print(f"[inner_hook] return_value: {lifecycle.return_value}")
    print(f"[inner_hook] caller: {lifecycle.caller}")
    print(f"[inner_hook] caller.trace: {lifecycle.caller.trace}")
    print(f"[inner_hook] callees: {lifecycle.callees}")

@outer_func.add_exception_hook
def outer_exception_hook(lifecycle: EXMPLifeCycle):
    print(f"\n[outer_exception_hook] arg: {lifecycle.arg}")
    print(f"[outer_exception_hook] trace: {lifecycle.trace}")
    print(f"[outer_exception_hook] exception: {lifecycle.exception}")
    print(f"[outer_exception_hook] caller: {lifecycle.caller}")
    print(f"[outer_exception_hook] callees: {lifecycle.callees}")
    print(f"[outer_exception_hook] callees[0].trace: {lifecycle.callees[0].trace}")

@inner_func.add_exception_hook
def inner_exception_hook(lifecycle: EXMPLifeCycle):
    print(f"\n[inner_exception_hook] arg: {lifecycle.arg}")
    print(f"[inner_exception_hook] trace: {lifecycle.trace}")
    print(f"[inner_exception_hook] exception: {lifecycle.exception}")
    print(f"[inner_exception_hook] caller: {lifecycle.caller}")
    print(f"[inner_exception_hook] caller.trace: {lifecycle.caller.trace}")
    print(f"[inner_exception_hook] callees: {lifecycle.callees}")

@outer_func.add_async_exception_hook
async def outer_async_exception_hook(lifecycle: EXMPLifeCycle):
    await asyncio.sleep(0.01)
    print(f"\n[outer_async_exception_hook] exception: {lifecycle.exception}")
    print(f"[outer_async_exception_hook] trace: {lifecycle.trace}")

@inner_func.add_async_exception_hook
async def inner_async_exception_hook(lifecycle: EXMPLifeCycle):
    await asyncio.sleep(0.01)
    print(f"\n[inner_async_exception_hook] exception: {lifecycle.exception}")
    print(f"[inner_async_exception_hook] trace: {lifecycle.trace}")

print("=== 정상 케이스 ===")
asyncio.run(outer_func(3, 5))
print("\n=== 예외 케이스 ===")
asyncio.run(outer_func(3, 0))
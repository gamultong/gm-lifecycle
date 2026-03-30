from __future__ import annotations
from typing import Callable, Any, ParamSpec, TypeVar, Generic, Type, Self
from contextvars import ContextVar
from abc import abstractmethod, ABC
import asyncio
import inspect

P = ParamSpec("P")
R = TypeVar("R")

class App:
    def __init__(self):
        self.trace_managers: list[TracerManager] = []
        self._prev_lifecycle: ContextVar[LifeCycle|None] = ContextVar("__caller")
        self._prev_lifecycle.set(None)


class LifeCycle(Generic[P, R], ABC):
    def __init__(self):
        self.caller: LifeCycle|None = None
        self.callees: list[LifeCycle] = []
        self.exception: Exception|None = None
    
    @classmethod
    @abstractmethod
    def create(cls, caller: LifeCycle|None, *args: P.args, **kwds: P.kwargs) -> Self:
        pass

    @abstractmethod
    def mm_return(self, return_value: R):
        pass

LIFECYCLE = TypeVar("LIFECYCLE", bound=LifeCycle)

class Tracer(Generic[P, R, LIFECYCLE]):
    def __init__(self, func: Callable[P, R], 
                 manager: TracerManager[P, R, LIFECYCLE]
        ) -> None:
        self.func = func
        self.hooks: list[Callable[[LIFECYCLE], Any]] = []
        self.manager = manager

    def add_hook(self, func: Callable[[LIFECYCLE], Any]):
        self.hooks.append(func)

    def here(self) -> LIFECYCLE:
        prev_lifecycle = self.manager.app._prev_lifecycle
        caller = prev_lifecycle.get()
        assert caller is not None, "이는 반드시 tracer 함수 실행 중 존재하며, 실행 내부에서만 가져올 수 있다."
        return caller

    def _setup(self, *args, **kwds) -> tuple[LIFECYCLE, ContextVar]:
        lifecycle_type = self.manager.lifecycle_type
        prev_lifecycle = self.manager.app._prev_lifecycle
        caller = prev_lifecycle.get()

        lifecycle = lifecycle_type.create(caller, *args, **kwds)
        lifecycle.caller = caller
        if caller is not None:
            caller.callees.append(lifecycle)

        prev_lifecycle.set(lifecycle)
        return lifecycle, prev_lifecycle

    def _run_hooks(self, lifecycle: LIFECYCLE):
        for hook in self.hooks:
            hook(lifecycle)

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> Any:
        if inspect.iscoroutinefunction(self.func):
            return self._async_call(*args, **kwds)
        return self._sync_call(*args, **kwds)

    def _sync_call(self, *args, **kwds) -> Any:
        lifecycle, prev_lifecycle = self._setup(*args, **kwds)
        try:
            return_value = self.func(*args, **kwds)
            lifecycle.mm_return(return_value)
        except Exception as e:
            lifecycle.exception = e
            raise
        finally:
            prev_lifecycle.set(lifecycle.caller)
        self._run_hooks(lifecycle)

        return return_value

    async def _async_call(self, *args, **kwds) -> Any:
        lifecycle, prev_lifecycle = self._setup(*args, **kwds)
        try:
            return_value = await self.func(*args, **kwds)
            lifecycle.mm_return(return_value)
        except Exception as e:
            lifecycle.exception = e
            raise
        finally:
            prev_lifecycle.set(lifecycle.caller)
        self._run_hooks(lifecycle)

        return return_value


class TracerManager(Generic[P, R, LIFECYCLE]):
    def __init__(self, lifecycle_type: Type[LIFECYCLE], app: App) -> None:
        self.tracer: list[Tracer[P, R, LIFECYCLE]] = []
        self.lifecycle_type = lifecycle_type
        self.app = app
        app.trace_managers.append(self)
        
    def tracing(self, func: Callable[P, R]) -> Tracer[P, R, LIFECYCLE]:
        tracer = Tracer(func, self)
        self.tracer.append(tracer)
        return tracer
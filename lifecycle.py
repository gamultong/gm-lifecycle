from __future__ import annotations
from typing import Callable, Any, ParamSpec, TypeVar, Generic, Type, Self
from abc import abstractmethod

P = ParamSpec("P")
R = TypeVar("R")

class LifeCycle(Generic[P, R]):
    @classmethod
    @abstractmethod
    def create(cls, *args: P.args, **kwds: P.kwargs) -> Self:
        pass

    @abstractmethod
    def mm_return(self, return_value:R):
        pass

LIFECYCLE = TypeVar("LIFECYCLE", bound=LifeCycle)

class Tracer(Generic[P, R, LIFECYCLE]):
    def __init__(self, func:Callable[P, R], 
                 manager:TracerManager[P, R, LIFECYCLE]
        ) -> None:
        self.func = func
        self.hooks:list[Callable[[LIFECYCLE], Any]] = []
        self.manager = manager
        self.__here = None # ContextVar로 변환 필요

    def add_hook(self, func:Callable[[LIFECYCLE], Any]):
        self.hooks.append(func)

    def here(self):
        assert self.__here is not None
        return self.__here

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> Any:
        lifecycle_type = self.manager.lifecycle_type
        lifecycle = lifecycle_type.create(
            *args,
            **kwds
        )
        self.__here = lifecycle
        
        return_value = self.func(*args, **kwds)
        lifecycle.mm_return(return_value)
        
        self.__here = None
        for hook in self.hooks:
            hook(lifecycle)

        return return_value

class TracerManager(Generic[P, R, LIFECYCLE]):
    def __init__(self, lifecycle_type:Type[LIFECYCLE]) -> None:
        self.tracer:list[Tracer[P, R, LIFECYCLE]] = []
        self.lifecycle_type = lifecycle_type
        
    def tracing(self, func: Callable[P, R]) -> Tracer[P, R, LIFECYCLE]:
        tracer = Tracer(func, self)
        self.tracer.append(tracer)

        return tracer

from __future__ import annotations
from typing import Callable, Any, ParamSpec, TypeVar, Generic, Type, Awaitable, Coroutine
from contextvars import ContextVar

P = ParamSpec("P")
R = TypeVar("R")


class App:
    def __init__(self):
        self.trace_managers: list[TracerManager] = []
        self._prev_lifecycle: ContextVar[LifeCycle | None] = ContextVar("__caller")
        self._prev_lifecycle.set(None)


class LifeCycle(Generic[P, R]):
    def __init__(self):
        self.caller: LifeCycle | None = None
        self.callees: list[LifeCycle] = []
        self.exception: Exception | None = None
        self.args: tuple = ()
        self.kwargs: dict = {}
        self.return_value: R

    def on_enter(self, *args: P.args, **kwargs: P.kwargs) -> None:
        pass

    def on_exit(self, return_value: R) -> None:
        pass

    async def async_on_enter(self, *args: P.args, **kwargs: P.kwargs) -> None:
        pass

    async def async_on_exit(self, return_value: R) -> None:
        pass


LIFECYCLE = TypeVar("LIFECYCLE", bound=LifeCycle)


class BaseTracer(Generic[LIFECYCLE]):
    def __init__(self, manager: TracerManager[LIFECYCLE]) -> None:
        self.hooks: list[Callable[[LIFECYCLE], Any]] = []
        self.exception_hooks: list[Callable[[LIFECYCLE], Any]] = []
        self.manager = manager

    def add_hook(self, func: Callable[[LIFECYCLE], Any]) -> Callable[[LIFECYCLE], Any]:
        self.hooks.append(func)
        return func

    def add_exception_hook(self, func: Callable[[LIFECYCLE], Any]) -> Callable[[LIFECYCLE], Any]:
        self.exception_hooks.append(func)
        return func

    def here(self) -> LIFECYCLE:
        prev_lifecycle = self.manager.app._prev_lifecycle
        lc = prev_lifecycle.get()
        assert lc is not None, "이는 반드시 tracer 함수 실행 중 존재하며, 실행 내부에서만 가져올 수 있다."
        return lc  # type: ignore[return-value]

    def _setup(self, *args: Any, **kwds: Any) -> tuple[LIFECYCLE, ContextVar[LifeCycle | None]]:
        lifecycle_type = self.manager.lifecycle_type
        prev_lifecycle = self.manager.app._prev_lifecycle
        caller = prev_lifecycle.get()

        lifecycle = lifecycle_type()
        lifecycle.caller = caller
        lifecycle.args = args
        lifecycle.kwargs = kwds
        if caller is not None:
            caller.callees.append(lifecycle)

        prev_lifecycle.set(lifecycle)
        return lifecycle, prev_lifecycle


class Tracer(BaseTracer[LIFECYCLE], Generic[P, R, LIFECYCLE]):
    def __init__(self, func: Callable[P, R],
                 manager: TracerManager[LIFECYCLE]
                 ) -> None:
        super().__init__(manager)
        self.func = func

    def _run_hooks(self, lifecycle: LIFECYCLE) -> None:
        for hook in self.hooks:
            hook(lifecycle)

    def _run_exception_hooks(self, lifecycle: LIFECYCLE) -> None:
        for hook in self.exception_hooks:
            hook(lifecycle)

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> R:
        lifecycle, prev_lifecycle = self._setup(*args, **kwds)
        lifecycle.on_enter(*args, **kwds)
        try:
            return_value = self.func(*args, **kwds)
            lifecycle.return_value = return_value
            lifecycle.on_exit(return_value)
            self._run_hooks(lifecycle)
            return return_value
        except Exception as e:
            lifecycle.exception = e
            self._run_exception_hooks(lifecycle)
            raise
        finally:
            prev_lifecycle.set(lifecycle.caller)


class AsyncTracer(BaseTracer[LIFECYCLE], Generic[P, R, LIFECYCLE]):
    def __init__(self, func: Callable[P, Awaitable[R]],
                 manager: TracerManager[LIFECYCLE]
                 ) -> None:
        super().__init__(manager)
        self.func = func
        self.async_hooks: list[Callable[[LIFECYCLE], Awaitable[Any]]] = []
        self.async_exception_hooks: list[Callable[[LIFECYCLE], Awaitable[Any]]] = []

    def add_async_hook(self, func: Callable[[LIFECYCLE], Awaitable[Any]]) -> Callable[[LIFECYCLE], Awaitable[Any]]:
        self.async_hooks.append(func)
        return func

    def add_async_exception_hook(self, func: Callable[[LIFECYCLE], Awaitable[Any]]) -> Callable[[LIFECYCLE], Awaitable[Any]]:
        self.async_exception_hooks.append(func)
        return func

    async def _run_hooks(self, lifecycle: LIFECYCLE) -> None:
        for hook in self.hooks:
            hook(lifecycle)
        for hook in self.async_hooks:
            await hook(lifecycle)

    async def _run_exception_hooks(self, lifecycle: LIFECYCLE) -> None:
        for hook in self.exception_hooks:
            hook(lifecycle)
        for hook in self.async_exception_hooks:
            await hook(lifecycle)

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> Coroutine[Any, Any, R]:
        return self._async_call(*args, **kwds)

    async def _async_call(self, *args: Any, **kwds: Any) -> R:
        lifecycle, prev_lifecycle = self._setup(*args, **kwds)
        await lifecycle.async_on_enter(*args, **kwds)
        try:
            return_value = await self.func(*args, **kwds)
            lifecycle.return_value = return_value
            await lifecycle.async_on_exit(return_value)
            await self._run_hooks(lifecycle)
            return return_value
        except Exception as e:
            lifecycle.exception = e
            await self._run_exception_hooks(lifecycle)
            raise
        finally:
            prev_lifecycle.set(lifecycle.caller)


class TracerManager(Generic[LIFECYCLE]):
    def __init__(self, lifecycle_type: Type[LIFECYCLE], app: App) -> None:
        self.tracer: list[BaseTracer[LIFECYCLE]] = []
        self.lifecycle_type = lifecycle_type
        self.app = app
        app.trace_managers.append(self)

    def tracing(self, func: Callable[P, R]) -> Tracer[P, R, LIFECYCLE]:
        tracer = Tracer(func, self)
        self.tracer.append(tracer)
        return tracer

    def async_tracing(self, func: Callable[P, Awaitable[R]]) -> AsyncTracer[P, R, LIFECYCLE]:
        tracer = AsyncTracer(func, self)
        self.tracer.append(tracer)
        return tracer

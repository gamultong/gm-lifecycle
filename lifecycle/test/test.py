import pytest
import asyncio
from lifecycle import TracerManager, LifeCycle, App, Tracer, AsyncTracer


# ── Fixture ──────────────────────────────────────────────────────────────────

class SampleLifeCycle(LifeCycle[[int, int], int]):
    trace: str = ""


@pytest.fixture
def app_and_tm():
    app = App()
    tm = TracerManager(SampleLifeCycle, app)
    return app, tm


# ── Sync Tests ────────────────────────────────────────────────────────────────

class TestSync:
    def test_tracing_returns_tracer(self, app_and_tm):
        _, tm = app_and_tm

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        assert isinstance(func, Tracer)

    def test_basic_return(self, app_and_tm):
        _, tm = app_and_tm

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        assert func(3, 5) == 8

    def test_args_captured(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            captured["lc"] = func.here()
            return arg1 + arg2

        func(3, 5)
        assert captured["lc"].args == (3, 5)

    def test_return_value_captured(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        @func.add_hook
        def hook(lc: SampleLifeCycle):
            captured["return_value"] = lc.return_value

        func(3, 5)
        assert captured["return_value"] == 8

    def test_kwargs_captured(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            captured["lc"] = func.here()
            return arg1 + arg2

        func(arg1=3, arg2=5)
        assert captured["lc"].kwargs == {"arg1": 3, "arg2": 5}

    def test_on_enter_called(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        class EnterLC(LifeCycle[[int, int], int]):
            def on_enter(self, arg1: int, arg2: int) -> None:
                captured["entered"] = (arg1, arg2)

        enter_tm = TracerManager(EnterLC, tm.app)

        @enter_tm.tracing
        def func(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        func(3, 5)
        assert captured["entered"] == (3, 5)

    def test_on_enter_caller_already_set(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        class CallerCheckLC(LifeCycle[[int, int], int]):
            def on_enter(self, arg1: int, arg2: int) -> None:
                captured["caller_in_enter"] = self.caller

        outer_tm = TracerManager(CallerCheckLC, tm.app)

        @outer_tm.tracing
        def outer(arg1: int, arg2: int) -> int:
            return inner(arg1, arg2)

        @outer_tm.tracing
        def inner(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        outer(3, 5)
        assert captured["caller_in_enter"] is not None

    def test_on_exit_called(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        class ExitLC(LifeCycle[[int, int], int]):
            def on_exit(self, return_value: int) -> None:
                captured["exited"] = return_value

        exit_tm = TracerManager(ExitLC, tm.app)

        @exit_tm.tracing
        def func(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        func(3, 5)
        assert captured["exited"] == 8

    def test_caller_callee_link(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.tracing
        def outer(arg1: int, arg2: int) -> int:
            outer.here().trace = "outer"
            return inner(arg1, arg2)

        @tm.tracing
        def inner(arg1: int, arg2: int) -> int:
            captured["inner_lc"] = inner.here()
            return arg1 + arg2

        @outer.add_hook
        def outer_hook(lc: SampleLifeCycle):
            captured["outer_lc"] = lc

        outer(3, 5)
        assert captured["inner_lc"].caller is captured["outer_lc"]
        assert captured["inner_lc"] in captured["outer_lc"].callees

    def test_caller_is_none_at_root(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            captured["lc"] = func.here()
            return arg1 + arg2

        func(3, 5)
        assert captured["lc"].caller is None

    def test_hook_called_after_return(self, app_and_tm):
        _, tm = app_and_tm
        order = []

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            order.append("func")
            return arg1 + arg2

        @func.add_hook
        def hook(lc: SampleLifeCycle):
            order.append("hook")

        func(3, 5)
        assert order == ["func", "hook"]

    def test_multiple_hooks(self, app_and_tm):
        _, tm = app_and_tm
        order = []

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        @func.add_hook
        def hook1(lc: SampleLifeCycle):
            order.append("hook1")

        @func.add_hook
        def hook2(lc: SampleLifeCycle):
            order.append("hook2")

        func(3, 5)
        assert order == ["hook1", "hook2"]

    def test_hook_not_called_on_exception(self, app_and_tm):
        _, tm = app_and_tm
        called = []

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            raise ValueError("oops")

        @func.add_hook
        def hook(lc: SampleLifeCycle):
            called.append("hook")

        with pytest.raises(ValueError):
            func(3, 5)

        assert called == []

    def test_exception_hook_called(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            raise ValueError("oops")

        @func.add_exception_hook
        def exc_hook(lc: SampleLifeCycle):
            captured["lc"] = lc

        with pytest.raises(ValueError):
            func(3, 5)

        assert isinstance(captured["lc"].exception, ValueError)

    def test_exception_hook_not_called_on_success(self, app_and_tm):
        _, tm = app_and_tm
        called = []

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        @func.add_exception_hook
        def exc_hook(lc: SampleLifeCycle):
            called.append("exc_hook")

        func(3, 5)
        assert called == []

    def test_exception_reraise(self, app_and_tm):
        _, tm = app_and_tm

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            return arg1 / arg2

        with pytest.raises(ZeroDivisionError):
            func(3, 0)

    def test_prev_lifecycle_restored_after_exception(self, app_and_tm):
        app, tm = app_and_tm

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            return arg1 / arg2

        with pytest.raises(ZeroDivisionError):
            func(3, 0)

        assert app._prev_lifecycle.get() is None

    def test_here_outside_tracer_raises(self, app_and_tm):
        _, tm = app_and_tm

        @tm.tracing
        def func(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        with pytest.raises(AssertionError):
            func.here()

    def test_nested_callees(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.tracing
        def outer(arg1: int, arg2: int) -> int:
            return inner_a(arg1, arg2) + inner_b(arg1, arg2)

        @tm.tracing
        def inner_a(arg1: int, arg2: int) -> int:
            return arg1

        @tm.tracing
        def inner_b(arg1: int, arg2: int) -> int:
            return arg2

        @outer.add_hook
        def hook(lc: SampleLifeCycle):
            captured["outer_lc"] = lc

        outer(3, 5)
        assert len(captured["outer_lc"].callees) == 2

    def test_exception_propagates_through_nested(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.tracing
        def outer(arg1: int, arg2: int) -> int:
            return inner(arg1, arg2)

        @tm.tracing
        def inner(arg1: int, arg2: int) -> int:
            return arg1 / arg2

        @outer.add_exception_hook
        def outer_exc(lc: SampleLifeCycle):
            captured["outer_exc"] = lc.exception

        @inner.add_exception_hook
        def inner_exc(lc: SampleLifeCycle):
            captured["inner_exc"] = lc.exception

        with pytest.raises(ZeroDivisionError):
            outer(3, 0)

        assert isinstance(captured["outer_exc"], ZeroDivisionError)
        assert isinstance(captured["inner_exc"], ZeroDivisionError)

    def test_app_isolation(self):
        app1 = App()
        app2 = App()
        tm1 = TracerManager(SampleLifeCycle, app1)
        tm2 = TracerManager(SampleLifeCycle, app2)
        captured = {}

        @tm1.tracing
        def func1(arg1: int, arg2: int) -> int:
            captured["lc1"] = func1.here()
            func2(arg1, arg2)
            return arg1 + arg2

        @tm2.tracing
        def func2(arg1: int, arg2: int) -> int:
            captured["lc2"] = func2.here()
            return arg1 + arg2

        func1(3, 5)
        assert captured["lc2"].caller is None


# ── Async Tests ───────────────────────────────────────────────────────────────

class TestAsync:
    def test_async_tracing_returns_async_tracer(self, app_and_tm):
        _, tm = app_and_tm

        @tm.async_tracing
        async def func(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        assert isinstance(func, AsyncTracer)

    @pytest.mark.asyncio
    async def test_basic_return(self, app_and_tm):
        _, tm = app_and_tm

        @tm.async_tracing
        async def func(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        assert await func(3, 5) == 8

    @pytest.mark.asyncio
    async def test_args_captured(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.async_tracing
        async def func(arg1: int, arg2: int) -> int:
            captured["lc"] = func.here()
            return arg1 + arg2

        await func(3, 5)
        assert captured["lc"].args == (3, 5)
        assert captured["lc"].return_value == 8

    @pytest.mark.asyncio
    async def test_caller_callee_link(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.async_tracing
        async def outer(arg1: int, arg2: int) -> int:
            outer.here().trace = "outer"
            return await inner(arg1, arg2)

        @tm.async_tracing
        async def inner(arg1: int, arg2: int) -> int:
            captured["inner_lc"] = inner.here()
            return arg1 + arg2

        @outer.add_hook
        def hook(lc: SampleLifeCycle):
            captured["outer_lc"] = lc

        await outer(3, 5)
        assert captured["inner_lc"].caller is captured["outer_lc"]
        assert captured["inner_lc"] in captured["outer_lc"].callees

    @pytest.mark.asyncio
    async def test_hook_not_called_on_exception(self, app_and_tm):
        _, tm = app_and_tm
        called = []

        @tm.async_tracing
        async def func(arg1: int, arg2: int) -> int:
            raise ValueError("async oops")

        @func.add_hook
        def hook(lc: SampleLifeCycle):
            called.append("hook")

        with pytest.raises(ValueError):
            await func(3, 5)

        assert called == []

    @pytest.mark.asyncio
    async def test_exception_hook_called(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.async_tracing
        async def func(arg1: int, arg2: int) -> int:
            return arg1 / arg2

        @func.add_exception_hook
        def exc_hook(lc: SampleLifeCycle):
            captured["lc"] = lc

        with pytest.raises(ZeroDivisionError):
            await func(3, 0)

        assert isinstance(captured["lc"].exception, ZeroDivisionError)

    @pytest.mark.asyncio
    async def test_async_hook_called(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.async_tracing
        async def func(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        @func.add_async_hook
        async def hook(lc: SampleLifeCycle):
            captured["return_value"] = lc.return_value

        await func(3, 5)
        assert captured["return_value"] == 8

    @pytest.mark.asyncio
    async def test_async_exception_hook_called(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.async_tracing
        async def func(arg1: int, arg2: int) -> int:
            return arg1 / arg2

        @func.add_async_exception_hook
        async def exc_hook(lc: SampleLifeCycle):
            captured["exception"] = lc.exception

        with pytest.raises(ZeroDivisionError):
            await func(3, 0)

        assert isinstance(captured["exception"], ZeroDivisionError)

    @pytest.mark.asyncio
    async def test_sync_and_async_hooks_both_called(self, app_and_tm):
        _, tm = app_and_tm
        order = []

        @tm.async_tracing
        async def func(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        @func.add_hook
        def sync_hook(lc: SampleLifeCycle):
            order.append("sync")

        @func.add_async_hook
        async def async_hook(lc: SampleLifeCycle):
            order.append("async")

        await func(3, 5)
        assert order == ["sync", "async"]

    @pytest.mark.asyncio
    async def test_sync_and_async_exception_hooks_both_called(self, app_and_tm):
        _, tm = app_and_tm
        order = []

        @tm.async_tracing
        async def func(arg1: int, arg2: int) -> int:
            return arg1 / arg2

        @func.add_exception_hook
        def sync_exc_hook(lc: SampleLifeCycle):
            order.append("sync")

        @func.add_async_exception_hook
        async def async_exc_hook(lc: SampleLifeCycle):
            order.append("async")

        with pytest.raises(ZeroDivisionError):
            await func(3, 0)

        assert order == ["sync", "async"]

    @pytest.mark.asyncio
    async def test_exception_hook_not_called_on_success(self, app_and_tm):
        _, tm = app_and_tm
        called = []

        @tm.async_tracing
        async def func(arg1: int, arg2: int) -> int:
            return arg1 + arg2

        @func.add_async_exception_hook
        async def exc_hook(lc: SampleLifeCycle):
            called.append("exc_hook")

        await func(3, 5)
        assert called == []

    @pytest.mark.asyncio
    async def test_exception_propagates_through_nested(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.async_tracing
        async def outer(arg1: int, arg2: int) -> int:
            return await inner(arg1, arg2)

        @tm.async_tracing
        async def inner(arg1: int, arg2: int) -> int:
            return arg1 / arg2

        @outer.add_exception_hook
        def outer_exc(lc: SampleLifeCycle):
            captured["outer_exc"] = lc.exception

        @outer.add_async_exception_hook
        async def outer_async_exc(lc: SampleLifeCycle):
            captured["outer_async_exc"] = lc.exception

        @inner.add_exception_hook
        def inner_exc(lc: SampleLifeCycle):
            captured["inner_exc"] = lc.exception

        @inner.add_async_exception_hook
        async def inner_async_exc(lc: SampleLifeCycle):
            captured["inner_async_exc"] = lc.exception

        with pytest.raises(ZeroDivisionError):
            await outer(3, 0)

        assert isinstance(captured["outer_exc"], ZeroDivisionError)
        assert isinstance(captured["outer_async_exc"], ZeroDivisionError)
        assert isinstance(captured["inner_exc"], ZeroDivisionError)
        assert isinstance(captured["inner_async_exc"], ZeroDivisionError)

    @pytest.mark.asyncio
    async def test_prev_lifecycle_restored_after_exception(self, app_and_tm):
        app, tm = app_and_tm

        @tm.async_tracing
        async def func(arg1: int, arg2: int) -> int:
            return arg1 / arg2

        with pytest.raises(ZeroDivisionError):
            await func(3, 0)

        assert app._prev_lifecycle.get() is None

    @pytest.mark.asyncio
    async def test_concurrent_isolation(self, app_and_tm):
        _, tm = app_and_tm
        captured = {}

        @tm.async_tracing
        async def func(arg1: int, arg2: int) -> int:
            await asyncio.sleep(0.05)
            captured[arg1] = func.here()
            return arg1 + arg2

        await asyncio.gather(func(1, 2), func(3, 4))
        assert captured[1].args == (1, 2)
        assert captured[3].args == (3, 4)

"""
힌팅 개선 예시

변경 전: TracerManager[[int, int], int, EXMPLifeCycle]
변경 후: TracerManager[EXMPLifeCycle]

P, R은 LifeCycle에 이미 내포되어 있으므로 TracerManager에서 중복 선언 불필요.
"""
from lifecycle import TracerManager, BaseTracer, Tracer, LifeCycle, App


# ── 기본 사용 ────────────────────────────────────────────────────────────────

class CalcLifeCycle(LifeCycle[[int, int], int]):
    def __init__(self):
        super().__init__()
        self.args: tuple[int, int]
        self.return_value: int

    @classmethod
    def create(cls, caller, arg1: int, arg2: int):
        instance = cls()
        instance.args = (arg1, arg2)
        return instance

    def mm_return(self, return_value: int):
        self.return_value = return_value


app = App()

# P, R 없이 LIFECYCLE 하나만 지정
TM: TracerManager[CalcLifeCycle] = TracerManager(CalcLifeCycle, app)

@TM.tracing  # 반환: Tracer[[int, int], int, CalcLifeCycle] — IDE가 정확히 추론
def add(arg1: int, arg2: int) -> int:
    return arg1 + arg2

@add.add_hook  # lifecycle: CalcLifeCycle — IDE가 정확히 추론
def on_add(lifecycle: CalcLifeCycle):
    print(f"[add] args={lifecycle.args}, result={lifecycle.return_value}")


# ── TracerManager 상속 ───────────────────────────────────────────────────────

class ExtendedTM(TracerManager[CalcLifeCycle]):
    def tracing(self, func):  # 오버라이드 가능
        print(f"[ExtendedTM] tracing 등록: {func.__name__}")
        return super().tracing(func)


ext_app = App()
ext_tm = ExtendedTM(CalcLifeCycle, ext_app)

@ext_tm.tracing
def multiply(arg1: int, arg2: int) -> int:
    return arg1 * arg2


# ── Tracer 상속 ──────────────────────────────────────────────────────────────

class LoggingTracer(Tracer[[int, int], int, CalcLifeCycle]):
    def _run_hooks(self, lifecycle: CalcLifeCycle) -> None:
        print(f"[LoggingTracer] hook 실행 전 로깅: args={lifecycle.args}")
        super()._run_hooks(lifecycle)


# ── BaseTracer로 list 타입 표현 ──────────────────────────────────────────────

def print_all_tracers(tracers: list[BaseTracer[CalcLifeCycle]]) -> None:
    for t in tracers:
        print(f"  tracer: {t}")

print("=== 기본 사용 ===")
add(3, 5)

print("\n=== TracerManager 상속 ===")
multiply(4, 6)

print("\n=== TM에 등록된 tracer 목록 ===")
print_all_tracers(TM.tracer)

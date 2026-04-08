# lifecycle 모듈 API

`lifecycle`은 함수 호출 한 번을 하나의 객체(LifeCycle)로 표현합니다. 이를 통해 함수 실행 중 정보를 기록하고, 함수 간 호출 관계를 추적하며, 실행 완료나 예외 발생 시점에 동작을 추가할 수 있습니다.

## 기능

- **자동 캡처** - 함수 호출 시 인자(`args`, `kwargs`)와 반환값(`return_value`)을 자동으로 캡처합니다.
- **진입/종료 hook** - `on_enter` / `on_exit`를 오버라이드하여 함수 진입/종료 시점에 처리를 추가할 수 있습니다.
- **실행 중 기록** - `here()`로 현재 실행 중인 LifeCycle에 접근하여 원하는 데이터를 기록할 수 있습니다.
- **호출 관계 추적** - 함수 간 caller/callee 관계를 자동으로 연결하고 트리 형태로 참조할 수 있습니다.
- **Hook** - 실행 완료 또는 예외 발생 시점에 동기/비동기 hook을 등록할 수 있습니다.

## 구성 요소

### App

애플리케이션 단위입니다. 같은 `App`에 속한 Tracer들은 서로 호출 관계가 연결됩니다. 다른 `App`에 속한 Tracer들과는 컨텍스트가 완전히 격리됩니다.

### TracerManager

같은 LifeCycle 타입을 공유하는 Tracer들의 관리자입니다. `App`과 LifeCycle 타입을 받아 Tracer를 생성합니다. 동기 함수에는 `tracing`, 비동기 함수에는 `async_tracing`을 사용합니다.

```python
tm = TracerManager(MyLC, app)
```

### Tracer / AsyncTracer

추적할 함수를 감싸는 wrapper입니다. 함수 호출 시 LifeCycle을 생성하고, 호출 관계 연결 및 hook 실행을 담당합니다.

- `here()` - 함수 내부에서 현재 실행 중인 LifeCycle에 접근
- `add_hook` / `add_exception_hook` - 정상 완료 / 예외 발생 시 hook 등록
- `add_async_hook` / `add_async_exception_hook` - 비동기 hook 등록 (AsyncTracer 전용)

### LifeCycle

함수의 실행 주기를 나타내는 객체입니다. 서브클래싱하여 원하는 필드와 동작을 추가할 수 있습니다.

#### 자동 캡처 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `args` | `tuple` | 함수의 positional arguments |
| `kwargs` | `dict` | 함수의 keyword arguments |
| `return_value` | `R` | 함수의 반환값 (함수 종료 후 세팅) |
| `caller` | `LifeCycle \| None` | 이 함수를 호출한 상위 LifeCycle |
| `callees` | `list[LifeCycle]` | 이 함수가 호출한 하위 LifeCycle 목록 |
| `exception` | `Exception \| None` | 예외 발생 시 저장 |

#### 오버라이드 가능 메서드

**동기 (Tracer)**

```python
class MyLC(LifeCycle[[int, int], int]):
    def on_enter(self, arg1: int, arg2: int) -> None:
        # 함수 진입 시 호출. self.caller, self.args 이미 세팅됨.
        pass

    def on_exit(self, return_value: int) -> None:
        # 함수 종료 시 호출. self.return_value도 이미 세팅됨.
        pass
```

**비동기 (AsyncTracer)**

```python
class MyAsyncLC(LifeCycle[[str], bool]):
    async def async_on_enter(self, order_id: str) -> None:
        pass

    async def async_on_exit(self, return_value: bool) -> None:
        pass
```

#### 실행 흐름

**Tracer (동기)**
1. LifeCycle 생성, `caller`/`args`/`kwargs` 세팅
2. `on_enter(*args, **kwargs)` 호출
3. 함수 실행
4. `return_value` 세팅
5. `on_exit(return_value)` 호출
6. hooks 실행
7. (예외 시) `exception` 세팅 -> exception hooks 실행

**AsyncTracer (비동기)**
1. LifeCycle 생성, `caller`/`args`/`kwargs` 세팅
2. `await async_on_enter(*args, **kwargs)` 호출
3. 함수 실행
4. `return_value` 세팅
5. `await async_on_exit(return_value)` 호출
6. hooks 실행 (sync -> async 순서)
7. (예외 시) `exception` 세팅 -> exception hooks 실행

## 타입 힌팅

### LifeCycle - P, R 제네릭

`LifeCycle[P, R]`의 P(파라미터), R(반환값)을 지정하면 `on_enter`/`on_exit` 파라미터에 타입이 적용됩니다.

```python
class CalcLC(LifeCycle[[int, int], float]):
    def on_enter(self, a: int, b: int) -> None: ...     # IDE 힌팅 O
    def on_exit(self, return_value: float) -> None: ...  # IDE 힌팅 O
```

타입이 필요 없다면 생략 가능합니다.

```python
class MinimalLC(LifeCycle):
    pass
```

### TracerManager - 단일 제네릭

```python
tm: TracerManager[CalcLC] = TracerManager(CalcLC, app)
```

### caller / callee 힌팅

기본적으로 `caller`는 `LifeCycle | None`, `callees`는 `list[LifeCycle]`입니다.
호출 관계가 예측 가능한 경우, 서브클래스에서 annotation override로 타입을 좁힐 수 있습니다.

```python
class InnerLC(LifeCycle[[int], int]):
    caller: OuterLC  # IDE에서 caller가 OuterLC로 추론됨

    def on_enter(self, value: int) -> None:
        print(self.caller.some_field)  # OuterLC의 필드에 접근 가능
```

### Tracer 상속

Tracer를 상속할 때는 P, R, LIFECYCLE을 모두 지정합니다.

```python
class LoggingTracer(Tracer[[int, int], int, CalcLC]):
    def _run_hooks(self, lifecycle: CalcLC) -> None:
        print(f"hook 실행 전 로깅: args={lifecycle.args}")
        super()._run_hooks(lifecycle)
```

### BaseTracer - 컬렉션 타입

```python
def print_all(tracers: list[BaseTracer[CalcLC]]) -> None:
    for t in tracers:
        print(t)
```

## 튜토리얼

- [예제 (동기 + 비동기)](docs/example.py)

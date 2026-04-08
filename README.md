# gm-lifecycle

함수의 실행 주기를 객체로 추적하는 Python 라이브러리입니다.

## 설치

```bash
pip install gm-lifecycle
```

## 소개

`gm-lifecycle`은 함수 호출 한 번을 하나의 `LifeCycle` 객체로 표현합니다. 함수 실행 중 원하는 데이터를 기록하고, 함수 간 호출 관계를 자동으로 추적하며, 실행 완료나 예외 발생 시 hook을 실행할 수 있습니다.

## 빠른 시작

```python
from lifecycle import App, TracerManager, LifeCycle

class MyLC(LifeCycle[[int, int], int]):
    def on_enter(self, a: int, b: int) -> None:
        self.operands = (a, b)

    def on_exit(self, return_value: int) -> None:
        print(f"{self.operands[0]} + {self.operands[1]} = {return_value}")

app = App()
manager = TracerManager(MyLC, app)

@manager.tracing
def add(a: int, b: int) -> int:
    return a + b

add(1, 2)  # 1 + 2 = 3
```

## 문서

모듈 상세 API는 [lifecycle/README.md](lifecycle/README.md)를 참고하세요.

## 라이선스

MIT

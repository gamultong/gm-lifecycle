# lifecycle 모듈 API

`lifecycle`은 함수 호출 한 번을 하나의 객체(LifeCycle)로 표현합니다. 이를 통해 함수 실행 중 정보를 기록하고, 함수 간 호출 관계를 추적하며, 실행 완료나 예외 발생 시점에 동작을 추가할 수 있습니다.

## 기능

- **실행 정보 수집** — 함수 호출 시 인자, 반환값, 예외를 자동으로 캡처합니다.
- **실행 중 정보 기록** — 함수 내부에서 현재 실행 중인 LifeCycle 인스턴스에 접근하여 원하는 데이터를 기록할 수 있습니다.
- **호출 관계 추적** — 함수 간 caller/callee 관계를 자동으로 연결하고 트리 형태로 참조할 수 있습니다.
- **Hook** — 실행 완료 또는 예외 발생 시점에 동기/비동기 hook을 등록할 수 있습니다.

## 구성 요소

### App

애플리케이션 단위입니다. 같은 `App`에 속한 Tracer들은 서로 호출 관계가 연결됩니다. 다른 `App`에 속한 Tracer들과는 컨텍스트가 완전히 격리됩니다.

### TracerManager

같은 LifeCycle 타입을 공유하는 Tracer들의 관리자입니다. `App`과 LifeCycle 타입을 받아 Tracer를 생성합니다. 동기 함수에는 `tracing`, 비동기 함수에는 `async_tracing`을 사용합니다.

### Tracer / AsyncTracer

추적할 함수를 감싸는 wrapper입니다. 함수 호출 시 LifeCycle을 생성하고, 호출 관계 연결 및 hook 실행을 담당합니다. 함수 내부에서 `here()`를 통해 현재 실행 중인 LifeCycle에 접근할 수 있습니다.

`AsyncTracer`는 sync hook 외에 async hook도 지원합니다.

### LifeCycle

함수의 실행 주기를 나타내는 객체입니다. 함수 호출 시 자동으로 생성되며, 실행이 끝나면 hook에 전달됩니다. 서브클래싱하여 원하는 필드를 자유롭게 추가할 수 있습니다.

- `caller` — 이 함수를 호출한 상위 LifeCycle
- `callees` — 이 함수가 호출한 하위 LifeCycle 목록
- `exception` — 예외 발생 시 저장

## 튜토리얼

- [동기 함수 예제](docs/example.py)
- [비동기 함수 예제](docs/async_example.py)
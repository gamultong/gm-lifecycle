"""
gm-lifecycle 기능 데모

시나리오: 주문 처리 파이프라인
  sync  -receive_order → validate_order → charge_payment
  async -async_receive_order → async_validate → async_charge
"""
import asyncio
from lifecycle import TracerManager, LifeCycle, App

app = App()


# ════════════════════════════════════════════════════════════════
#  LifeCycle 정의
# ════════════════════════════════════════════════════════════════

class OrderLC(LifeCycle[[str, list], bool]):
    """on_enter / on_exit -진입·종료 시점 처리"""

    def on_enter(self, order_id: str, items: list) -> None:
        self.order_id = order_id
        self.items = items
        print(f"  [OrderLC.on_enter] 주문 수신: {order_id}, {len(items)}개 항목")

    def on_exit(self, return_value: bool) -> None:
        status = "성공" if return_value else "실패"
        print(f"  [OrderLC.on_exit]  처리 {status}: {self.order_id}")


class ValidateLC(LifeCycle[[str, list], bool]):
    """caller 타입 힌팅 + here() -두 가지 동시 활용"""
    caller: OrderLC  # 호출 관계가 예측 가능할 때 직접 힌팅

    def __init__(self):
        super().__init__()
        self.item_count: int  # here()로 세팅할 인스턴스 변수

    def on_enter(self, order_id: str, items: list) -> None:
        # on_enter 시점에 self.caller는 이미 세팅됨
        print(f"  [ValidateLC.on_enter] 검증 시작: {order_id}, {len(items)}개 항목"
              f" (호출자: {self.caller.order_id})")


class ChargeLC(LifeCycle[[str, int], bool]):
    """here() -함수 내부에서 lifecycle에 직접 접근"""
    caller: OrderLC

    def __init__(self):
        super().__init__()
        self.amount: int

    def on_exit(self, return_value: bool) -> None:
        print(f"  [ChargeLC.on_exit]  결제 완료: {self.amount}원")


# ════════════════════════════════════════════════════════════════
#  TracerManager
# ════════════════════════════════════════════════════════════════

order_tm    = TracerManager(OrderLC, app)
validate_tm = TracerManager(ValidateLC, app)
charge_tm   = TracerManager(ChargeLC, app)


# ════════════════════════════════════════════════════════════════
#  함수 등록
# ════════════════════════════════════════════════════════════════

@order_tm.tracing
def receive_order(order_id: str, items: list) -> bool:
    ok = validate_order(order_id, items)
    if ok:
        charge_payment(order_id, len(items) * 1000)
    return ok


@validate_tm.tracing
def validate_order(order_id: str, items: list) -> bool:
    lc = validate_order.here()  # here()로 lifecycle 접근
    lc.item_count = len(items)  # 추가 데이터 저장
    return lc.item_count > 0 and order_id.startswith("ORD")


@charge_tm.tracing
def charge_payment(order_id: str, amount: int) -> bool:
    lc = charge_payment.here()  # here()로 lifecycle 접근
    lc.amount = amount          # 추가 데이터 저장
    print(f"  [charge_payment]   결제 처리: {order_id}, {amount}원")
    return True


# ════════════════════════════════════════════════════════════════
#  Hook 등록
# ════════════════════════════════════════════════════════════════

@receive_order.add_hook
def on_order_done(lc: OrderLC):
    child_types = [type(c).__name__ for c in lc.callees]
    print(f"  [hook] 완료 -하위 lifecycle: {child_types}")

@receive_order.add_exception_hook
def on_order_error(lc: OrderLC):
    print(f"  [exception_hook] 오류: {lc.exception}")

@validate_order.add_hook
def on_validate_done(lc: ValidateLC):
    # caller가 OrderLC로 타입됨 → IDE 자동완성 지원
    print(f"  [hook] 검증 완료 -주문: {lc.caller.order_id}"
          f", 항목 수: {lc.item_count}, 결과: {lc.return_value}")

@charge_payment.add_hook
def on_charge_done(lc: ChargeLC):
    print(f"  [hook] 결제 완료 -{lc.amount}원, 상위 주문: {lc.caller.order_id}")


# ════════════════════════════════════════════════════════════════
#  Async
# ════════════════════════════════════════════════════════════════

class AsyncOrderLC(LifeCycle[[str], bool]):
    """async_on_enter / async_on_exit -비동기 진입·종료 처리"""

    async def async_on_enter(self, order_id: str) -> None:
        self.order_id = order_id
        print(f"  [AsyncOrderLC.async_on_enter] 비동기 주문: {order_id}")

    async def async_on_exit(self, return_value: bool) -> None:
        print(f"  [AsyncOrderLC.async_on_exit]  결과: {return_value}")


class AsyncStepLC(LifeCycle[[str], bool]):
    """caller 타입 힌팅 + here() -async 버전"""
    caller: AsyncOrderLC

    def __init__(self):
        super().__init__()
        self.step_result: str

    async def async_on_enter(self, order_id: str) -> None:
        print(f"  [AsyncStepLC.async_on_enter] 처리 시작: {order_id}"
              f" (상위 주문: {self.caller.order_id})")


async_order_tm = TracerManager(AsyncOrderLC, app)
async_step_tm  = TracerManager(AsyncStepLC, app)


@async_order_tm.async_tracing
async def async_receive_order(order_id: str) -> bool:
    ok = await async_validate(order_id)
    if ok:
        await async_charge(order_id)
    return ok


@async_step_tm.async_tracing
async def async_validate(order_id: str) -> bool:
    lc = async_validate.here()  # here() -async 함수에서도 동일하게 사용
    await asyncio.sleep(0.01)
    result = order_id.startswith("ORD")
    lc.step_result = "통과" if result else "거부"
    return result


@async_step_tm.async_tracing
async def async_charge(order_id: str) -> bool:
    lc = async_charge.here()
    await asyncio.sleep(0.01)
    lc.step_result = "결제완료"
    return True


@async_receive_order.add_async_hook
async def on_async_order_done(lc: AsyncOrderLC):
    print(f"  [async_hook] 완료: {lc.order_id}, 하위 호출 수: {len(lc.callees)}")

@async_receive_order.add_async_exception_hook
async def on_async_order_error(lc: AsyncOrderLC):
    print(f"  [async_exception_hook] 오류: {lc.exception}")

@async_validate.add_async_hook
async def on_async_validate_done(lc: AsyncStepLC):
    # caller가 AsyncOrderLC로 타입됨
    print(f"  [async_hook] 검증 결과: {lc.step_result} (상위: {lc.caller.order_id})")


# ════════════════════════════════════════════════════════════════
#  실행
# ════════════════════════════════════════════════════════════════

print("=" * 50)
print("  [SYNC] 정상 주문")
print("=" * 50)
receive_order("ORD-001", ["사과", "바나나"])

print()
print("=" * 50)
print("  [SYNC] 잘못된 주문 (빈 items)")
print("=" * 50)
receive_order("ORD-002", [])

print()
print("=" * 50)
print("  [ASYNC] 비동기 주문")
print("=" * 50)
asyncio.run(async_receive_order("ORD-003"))

"""Route-order bag packing with weight + volume caps and fragile isolation.

装袋规则（按现网路线 seq 顺序）：
1. 重量与体积双约束，任一超出路线限额即拒收，不能借易碎隔离规则装入。
2. 易碎站点与非易碎站点不得同袋：即使当前袋重量体积都还够，易碎性不同
   也必须新开袋（split_reason="fragile"）。
3. 因当前袋满（重量或体积装不下）而开新袋：split_reason="full"。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 拒收原因码
REJECT_OVER_LIMIT = "over_limit"

# 开新袋原因
SPLIT_START = "start"
SPLIT_FULL = "full"
SPLIT_FRAGILE = "fragile"

# 袋类型
KIND_FRAGILE = "fragile"
KIND_NORMAL = "normal"


@dataclass(frozen=True)
class StopItem:
    stop_id: int
    seq: int
    weight_kg: float
    volume_l: float
    label: str = ""
    is_fragile: bool = False


@dataclass
class Bag:
    bag_index: int
    kind: str = KIND_NORMAL
    split_reason: str | None = None
    items: list[StopItem] = field(default_factory=list)
    weight_kg: float = 0.0
    volume_l: float = 0.0

    def accepts_kind(self, item: StopItem) -> bool:
        return (item.is_fragile and self.kind == KIND_FRAGILE) or (
            not item.is_fragile and self.kind == KIND_NORMAL
        )


@dataclass(frozen=True)
class Reject:
    item: StopItem
    reason: str
    reason_code: str = REJECT_OVER_LIMIT


@dataclass(frozen=True)
class PackResult:
    bags: list[Bag]
    rejects: list[Reject]


def can_fit(bag: Bag, item: StopItem, max_weight: float, max_volume: float) -> bool:
    return (
        bag.weight_kg + item.weight_kg <= max_weight + 1e-9
        and bag.volume_l + item.volume_l <= max_volume + 1e-9
    )


def over_limit_reason(item: StopItem, max_weight: float, max_volume: float) -> str:
    parts = []
    if item.weight_kg > max_weight:
        parts.append(f"超重 {item.weight_kg}>{max_weight}")
    if item.volume_l > max_volume:
        parts.append(f"超体积 {item.volume_l}>{max_volume}")
    return "；".join(parts)


def pack_route(
    stops: list[StopItem],
    max_weight: float,
    max_volume: float,
) -> PackResult:
    ordered = sorted(stops, key=lambda s: s.seq)
    bags: list[Bag] = []
    rejects: list[Reject] = []
    current: Bag | None = None

    for item in ordered:
        # 1. 单站自身已超路线限额：走现网拒收，不能借隔离规则装进去
        if item.weight_kg > max_weight or item.volume_l > max_volume:
            rejects.append(
                Reject(item, over_limit_reason(item, max_weight, max_volume), REJECT_OVER_LIMIT)
            )
            continue

        # 2. 判断是否需要新开袋
        split_reason: str | None = None
        if current is None:
            split_reason = SPLIT_START
        elif not current.accepts_kind(item):
            # 易碎隔离：即使重量体积都还够也必须新开袋
            split_reason = SPLIT_FRAGILE
        elif not can_fit(current, item, max_weight, max_volume):
            split_reason = SPLIT_FULL

        if split_reason is not None:
            current = Bag(
                bag_index=len(bags) + 1,
                kind=KIND_FRAGILE if item.is_fragile else KIND_NORMAL,
                split_reason=split_reason,
            )
            bags.append(current)

        if not can_fit(current, item, max_weight, max_volume):
            # should not happen after single-item check, but keep safe
            rejects.append(Reject(item, "无法装入新袋", REJECT_OVER_LIMIT))
            continue

        current.items.append(item)
        current.weight_kg += item.weight_kg
        current.volume_l += item.volume_l

    return PackResult(bags=bags, rejects=rejects)

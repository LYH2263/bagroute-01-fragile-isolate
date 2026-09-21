from app.services.pack_engine import (
    KIND_FRAGILE,
    KIND_NORMAL,
    REJECT_OVER_LIMIT,
    SPLIT_FRAGILE,
    SPLIT_FULL,
    SPLIT_START,
    StopItem,
    pack_route,
)


def test_packs_in_route_order_splitting_bags():
    stops = [
        StopItem(1, 1, 2.0, 3.0),
        StopItem(2, 2, 2.5, 3.0),
        StopItem(3, 3, 1.0, 1.0),
    ]
    result = pack_route(stops, max_weight=4.0, max_volume=10.0)
    assert len(result.bags) == 2
    assert [i.stop_id for i in result.bags[0].items] == [1]
    assert [i.stop_id for i in result.bags[1].items] == [2, 3]
    assert not result.rejects
    assert result.bags[0].split_reason == SPLIT_START
    assert result.bags[1].split_reason == SPLIT_FULL


def test_reject_oversized_stop():
    stops = [StopItem(1, 1, 9.0, 1.0, "大件"), StopItem(2, 2, 1.0, 1.0)]
    result = pack_route(stops, max_weight=5.0, max_volume=5.0)
    assert len(result.rejects) == 1
    assert result.rejects[0].item.stop_id == 1
    assert result.rejects[0].reason_code == REJECT_OVER_LIMIT
    assert len(result.bags) == 1
    assert result.bags[0].items[0].stop_id == 2


def test_volume_cap_triggers_new_bag():
    stops = [StopItem(1, 1, 1.0, 4.0), StopItem(2, 2, 1.0, 4.0)]
    result = pack_route(stops, max_weight=10.0, max_volume=5.0)
    assert len(result.bags) == 2
    assert result.bags[1].split_reason == SPLIT_FULL


def stop_ids(bag):
    return [i.stop_id for i in bag.items]


def test_fragile_and_normal_never_share_bag_even_with_room():
    # 两站加总远低于限额：若是普通站会同袋，易碎性不同则必须分开
    stops = [
        StopItem(1, 1, 1.0, 1.0, "普通站", is_fragile=False),
        StopItem(2, 2, 1.0, 1.0, "易碎站", is_fragile=True),
    ]
    result = pack_route(stops, max_weight=10.0, max_volume=10.0)
    assert len(result.bags) == 2
    assert result.bags[0].kind == KIND_NORMAL
    assert result.bags[1].kind == KIND_FRAGILE
    # 新袋原因必须是易碎隔离，而不是满额
    assert result.bags[1].split_reason == SPLIT_FRAGILE
    for bag in result.bags:
        kinds = {i.is_fragile for i in bag.items}
        assert len(kinds) == 1
    assert not result.rejects


def test_two_fragile_stops_share_bag_when_room():
    stops = [
        StopItem(1, 1, 1.0, 1.0, is_fragile=True),
        StopItem(2, 2, 1.0, 1.0, is_fragile=True),
    ]
    result = pack_route(stops, max_weight=10.0, max_volume=10.0)
    assert len(result.bags) == 1
    assert result.bags[0].kind == KIND_FRAGILE
    assert stop_ids(result.bags[0]) == [1, 2]


def test_oversized_fragile_stop_is_rejected_not_isolated_into_bag():
    # 易碎站自身超重：不能借隔离规则装进任何袋，仍走现网拒收
    stops = [
        StopItem(1, 1, 1.0, 1.0, is_fragile=True),
        StopItem(2, 2, 9.0, 1.0, "超重易碎", is_fragile=True),
        StopItem(3, 3, 1.0, 1.0, is_fragile=False),
    ]
    result = pack_route(stops, max_weight=5.0, max_volume=10.0)
    assert len(result.rejects) == 1
    rej = result.rejects[0]
    assert rej.item.stop_id == 2
    assert rej.reason_code == REJECT_OVER_LIMIT
    assert "超重" in rej.reason
    # 拒收站不得出现在任何袋中
    all_ids = [sid for b in result.bags for sid in stop_ids(b)]
    assert 2 not in all_ids
    # 易碎袋(站1)与非易碎袋(站3)仍隔离
    assert {b.kind for b in result.bags} == {KIND_FRAGILE, KIND_NORMAL}


def test_oversized_normal_stop_between_fragile_runs_rejected():
    # 与种子一致的交错结构：普 易 普 [超重普] 易 易
    stops = [
        StopItem(11, 1, 2.2, 4.0, is_fragile=False),
        StopItem(12, 2, 3.5, 5.5, is_fragile=True),
        StopItem(13, 3, 1.8, 3.0, is_fragile=False),
        StopItem(14, 4, 9.5, 6.0, is_fragile=False),  # 9.5 > 8 拒收
        StopItem(15, 5, 2.0, 4.5, is_fragile=True),
        StopItem(16, 6, 2.5, 4.0, is_fragile=True),
    ]
    result = pack_route(stops, max_weight=8.0, max_volume=18.0)

    # 仅一笔超限拒收
    assert len(result.rejects) == 1
    assert result.rejects[0].item.stop_id == 14
    assert result.rejects[0].reason_code == REJECT_OVER_LIMIT

    # 四个袋：普|易|普|易(含两个易碎站)
    assert [b.kind for b in result.bags] == [
        KIND_NORMAL,
        KIND_FRAGILE,
        KIND_NORMAL,
        KIND_FRAGILE,
    ]
    assert stop_ids(result.bags[0]) == [11]
    assert stop_ids(result.bags[1]) == [12]
    assert stop_ids(result.bags[2]) == [13]
    assert stop_ids(result.bags[3]) == [15, 16]

    # 开新袋原因：首袋、三次隔离（满额均未触发）
    assert [b.split_reason for b in result.bags] == [
        SPLIT_START,
        SPLIT_FRAGILE,
        SPLIT_FRAGILE,
        SPLIT_FRAGILE,
    ]


def test_seq_order_preserved_through_fragile_splits():
    # 故意乱序传入；装袋与拒收都必须按 seq 走
    stops = [
        StopItem(3, 3, 1.0, 1.0, is_fragile=True),
        StopItem(1, 1, 1.0, 1.0, is_fragile=False),
        StopItem(4, 4, 9.0, 1.0, is_fragile=False),
        StopItem(2, 2, 1.0, 1.0, is_fragile=False),
    ]
    result = pack_route(stops, max_weight=5.0, max_volume=10.0)
    walked = [(b.bag_index, [i.seq for i in b.items]) for b in result.bags]
    flat_seq = [seq for _, seqs in walked for seq in seqs]
    assert flat_seq == sorted(flat_seq)
    assert flat_seq == [1, 2, 3]
    assert [r.item.seq for r in result.rejects] == [4]


def test_full_split_then_fragile_split_both_distinguishable():
    # 站1+站2 装满（重量上限 3，合计恰为 3），站3 非易碎满额开袋；站4 易碎再隔离开袋
    stops = [
        StopItem(1, 1, 1.5, 1.0, is_fragile=False),
        StopItem(2, 2, 1.5, 1.0, is_fragile=False),
        StopItem(3, 3, 1.0, 1.0, is_fragile=False),
        StopItem(4, 4, 1.0, 1.0, is_fragile=True),
    ]
    result = pack_route(stops, max_weight=3.0, max_volume=10.0)
    assert [b.split_reason for b in result.bags] == [
        SPLIT_START,
        SPLIT_FULL,
        SPLIT_FRAGILE,
    ]
    assert [b.kind for b in result.bags] == [
        KIND_NORMAL,
        KIND_NORMAL,
        KIND_FRAGILE,
    ]

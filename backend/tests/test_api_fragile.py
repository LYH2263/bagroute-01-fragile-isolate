"""API 层：易碎标记可改并落库，再次读回仍在；装袋据此隔离。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import DeliveryRoute, PackBag, SubscriberStop


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    db = TestSession()
    route = DeliveryRoute(name="测试线", max_weight_kg=8.0, max_volume_l=18.0)
    db.add(route)
    db.flush()
    db.add_all(
        [
            SubscriberStop(route_id=route.id, seq=1, name="普通站", weight_kg=1.0, volume_l=1.0, is_fragile=False),
            SubscriberStop(route_id=route.id, seq=2, name="易碎站", weight_kg=1.0, volume_l=1.0, is_fragile=False),
        ]
    )
    db.commit()
    route_id, fragile_stop_id = route.id, db.scalars(
        select(SubscriberStop.id).where(SubscriberStop.name == "易碎站")
    ).one()
    db.close()

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    # 不进入 with：跳过 lifespan 里的 Postgres 专用 ADD COLUMN DDL
    c = TestClient(app)
    c.route_id = route_id  # type: ignore[attr-defined]
    c.fragile_stop_id = fragile_stop_id  # type: ignore[attr-defined]
    yield c
    app.dependency_overrides.clear()


def test_patch_fragile_persists_and_is_read_back(client):
    sid = client.fragile_stop_id  # type: ignore[attr-defined]
    # 初始非易碎
    rows = client.get(f"/api/stops?route_id={client.route_id}").json()
    assert {s["name"]: s["is_fragile"] for s in rows} == {"普通站": False, "易碎站": False}

    # 标记为易碎并落库
    r = client.patch(f"/api/stops/{sid}", json={"is_fragile": True})
    assert r.status_code == 200
    assert r.json()["is_fragile"] is True

    # 再次进入站点页（重新 GET）仍能看到标记
    rows = client.get(f"/api/stops?route_id={client.route_id}").json()
    assert {s["name"]: s["is_fragile"] for s in rows} == {"普通站": False, "易碎站": True}


def test_pack_isolates_fragile_after_patch(client):
    sid = client.fragile_stop_id  # type: ignore[attr-defined]
    client.patch(f"/api/stops/{sid}", json={"is_fragile": True})
    bags = client.post("/api/pack", json={"route_id": client.route_id}).json()
    # 两个 1kg/1L 的站本可同袋，但易碎性不同 → 两袋
    assert len(bags) == 2
    assert [b["kind"] for b in bags] == ["normal", "fragile"]
    assert bags[1]["split_reason"] == "fragile"
    assert [i["stop_name"] for i in bags[1]["items"]] == ["易碎站"]
    assert bags[1]["items"][0]["is_fragile"] is True
    # 无拒收
    assert client.get("/api/rejects").json() == []


def test_pack_overweight_stop_rejected_not_smuggled(client):
    sid = client.fragile_stop_id  # type: ignore[attr-defined]
    client.patch(f"/api/stops/{sid}", json={"is_fragile": True})
    # 再加一个超重的非易碎站（9 > 8）
    db_gen = app.dependency_overrides[get_db]()
    s = next(db_gen)
    route = s.get(DeliveryRoute, client.route_id)
    s.add(SubscriberStop(route_id=route.id, seq=3, name="超重站", weight_kg=9.0, volume_l=1.0, is_fragile=False))
    s.commit()
    s.close()

    bags = client.post("/api/pack", json={"route_id": client.route_id}).json()
    rejects = client.get("/api/rejects").json()
    assert len(rejects) == 1
    assert rejects[0]["stop_name"] == "超重站"
    assert rejects[0]["reason_code"] == "over_limit"
    packed_names = [i["stop_name"] for b in bags for i in b["items"]]
    assert "超重站" not in packed_names

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeliveryRoute(Base):
    __tablename__ = "delivery_routes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    max_weight_kg: Mapped[float] = mapped_column(Float, default=8.0)
    max_volume_l: Mapped[float] = mapped_column(Float, default=20.0)
    stops: Mapped[list["SubscriberStop"]] = relationship(back_populates="route")


class SubscriberStop(Base):
    __tablename__ = "subscriber_stops"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("delivery_routes.id"))
    seq: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(80))
    weight_kg: Mapped[float] = mapped_column(Float)
    volume_l: Mapped[float] = mapped_column(Float)
    is_fragile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    route: Mapped[DeliveryRoute] = relationship(back_populates="stops")


class PackBag(Base):
    __tablename__ = "pack_bags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("delivery_routes.id"))
    bag_index: Mapped[int] = mapped_column(Integer)
    weight_kg: Mapped[float] = mapped_column(Float)
    volume_l: Mapped[float] = mapped_column(Float)
    # kind: "fragile"（仅易碎） | "normal"（仅非易碎）
    kind: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    # split_reason: 该袋为何新开 start | full | fragile
    split_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    items: Mapped[list["BagItem"]] = relationship(back_populates="bag")


class BagItem(Base):
    __tablename__ = "bag_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bag_id: Mapped[int] = mapped_column(ForeignKey("pack_bags.id"))
    stop_id: Mapped[int] = mapped_column(Integer)
    stop_name: Mapped[str] = mapped_column(String(80))
    weight_kg: Mapped[float] = mapped_column(Float)
    volume_l: Mapped[float] = mapped_column(Float)
    # 装袋时的易碎快照，保证袋明细即使站点标记事后变更也仍能识别
    is_fragile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bag: Mapped[PackBag] = relationship(back_populates="items")


class RejectRecord(Base):
    __tablename__ = "reject_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("delivery_routes.id"))
    stop_id: Mapped[int] = mapped_column(Integer)
    stop_name: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(String(200))
    # over_limit: 单站超路线限额拒收（现网拒收）
    reason_code: Mapped[str] = mapped_column(String(30), default="over_limit", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

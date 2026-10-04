import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.time import utcnow


class Base(DeclarativeBase):
    pass


def new_id() -> str:
    return str(uuid.uuid4())


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (CheckConstraint("status IN ('lobby', 'active', 'completed')", name="ck_sessions_status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    room_code: Mapped[str] = mapped_column(String(8), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    host_participant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="lobby", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    restaurant_links: Mapped[list["SessionRestaurant"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionRestaurant.position",
    )
    swipes: Mapped[list["Swipe"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("session_id", "nickname", name="uq_participants_session_nickname"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    session: Mapped[Session] = relationship(back_populates="participants")
    swipes: Mapped[list["Swipe"]] = relationship(back_populates="participant")


class Restaurant(Base):
    __tablename__ = "restaurants"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_restaurants_source_external"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cuisine: Mapped[str | None] = mapped_column(String(120), nullable=True)
    categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    session_links: Mapped[list["SessionRestaurant"]] = relationship(back_populates="restaurant")
    swipes: Mapped[list["Swipe"]] = relationship(back_populates="restaurant")


class SessionRestaurant(Base):
    __tablename__ = "session_restaurants"
    __table_args__ = (
        UniqueConstraint("session_id", "restaurant_id", name="uq_session_restaurants_pair"),
        UniqueConstraint("session_id", "position", name="uq_session_restaurants_position"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id: Mapped[str] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    session: Mapped[Session] = relationship(back_populates="restaurant_links")
    restaurant: Mapped[Restaurant] = relationship(back_populates="session_links")


class Swipe(Base):
    __tablename__ = "swipes"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "participant_id",
            "restaurant_id",
            name="uq_swipes_participant_restaurant",
        ),
        CheckConstraint("decision IN ('like', 'pass')", name="ck_swipes_decision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    restaurant_id: Mapped[str] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    session: Mapped[Session] = relationship(back_populates="swipes")
    participant: Mapped[Participant] = relationship(back_populates="swipes")
    restaurant: Mapped[Restaurant] = relationship(back_populates="swipes")

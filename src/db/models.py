from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    String, Integer, DateTime, Text, JSON, UniqueConstraint, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import LargeBinary



class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    source: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)

    # optional payloads
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # store raw source-specific metadata (score, author, tags, etc.)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("url", name="uq_items_url"),)


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)

    persona: Mapped[str] = mapped_column(String(50), nullable=False)  # GENAI_NEWS etc
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # keep/drop
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # full structured JSON from model
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    item: Mapped["Item"] = relationship(back_populates="evaluations")

class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    dim: Mapped[int] = mapped_column(Integer, nullable=False)
    vector: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # optional relationship (nice to have)
    item: Mapped["Item"] = relationship()



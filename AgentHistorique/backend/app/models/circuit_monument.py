from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.circuit import Circuit
    from app.models.monument import Monument


class CircuitMonument(Base, TimestampMixin):
    """Maps to Tab_circuit_monument.xlsx (normalized; denormalized names omitted)."""

    __tablename__ = "circuit_monuments"
    __table_args__ = (
        UniqueConstraint("circuit_id", "monument_id", name="uq_circuit_monument"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    circuit_id: Mapped[int] = mapped_column(
        ForeignKey("circuits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    monument_id: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        ForeignKey("monuments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)  # Ordre

    circuit: Mapped["Circuit"] = relationship(back_populates="monument_links")
    monument: Mapped["Monument"] = relationship(back_populates="circuit_links")

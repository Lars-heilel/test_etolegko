from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class CampaignOfferModel(Base):
    __tablename__ = "campaign_offer_states"
    # The unique index also covers campaign and campaign/stream lookups.
    __table_args__ = (
        UniqueConstraint("campaign_id", "stream_id", "offer_id", name="uq_campaign_stream_offer"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(Integer)
    stream_id: Mapped[int] = mapped_column(Integer)
    stream_name: Mapped[str] = mapped_column(String(255))
    offer_id: Mapped[int] = mapped_column(Integer)
    offer_name: Mapped[str] = mapped_column(String(255))
    share: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(16), default="active")
    locked: Mapped[bool] = mapped_column(Boolean, default=False)

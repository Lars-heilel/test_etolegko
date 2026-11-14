from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.keitaro.entities.campaign_offer import CampaignOffer
from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.snapshots import KeitaroFlowSnapshot
from app.domain.keitaro.value_objects.identifiers import CampaignId, OfferId, StreamId
from app.domain.keitaro.value_objects.offer_share import OfferShare, OfferState
from app.infrastructure.persistence.models import CampaignOfferModel


class SqlAlchemyCampaignOfferRepository:
    """Persist aggregates without committing the caller's unit of work."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_campaign(self, campaign_id: CampaignId) -> list[FlowOffers]:
        rows = await self._session.scalars(
            select(CampaignOfferModel)
            .where(CampaignOfferModel.campaign_id == campaign_id.value)
            .order_by(CampaignOfferModel.stream_id, CampaignOfferModel.id)
        )
        grouped: dict[int, list[CampaignOffer]] = {}
        names: dict[int, str] = {}
        for row in rows:
            names[row.stream_id] = row.stream_name
            grouped.setdefault(row.stream_id, []).append(
                CampaignOffer(
                    OfferId(row.offer_id),
                    row.offer_name,
                    OfferShare(row.share),
                    OfferState(row.state),
                    row.locked,
                )
            )
        return [
            FlowOffers.rehydrate(StreamId(stream_id), names[stream_id], offers)
            for stream_id, offers in grouped.items()
        ]

    async def save(self, campaign_id: CampaignId, flow: FlowOffers) -> None:
        existing = {
            row.offer_id: row
            for row in await self._session.scalars(
                select(CampaignOfferModel).where(
                    CampaignOfferModel.campaign_id == campaign_id.value,
                    CampaignOfferModel.stream_id == flow.stream_id.value,
                )
            )
        }
        for item in flow.offers:
            row = existing.pop(item.offer_id.value, None)
            if row is None:
                row = CampaignOfferModel(
                    campaign_id=campaign_id.value,
                    stream_id=flow.stream_id.value,
                    offer_id=item.offer_id.value,
                )
                self._session.add(row)
            row.stream_name = flow.name
            row.offer_name = item.name
            row.share = item.share.value
            row.state = item.state.value
            row.locked = item.locked
        for row in existing.values():
            await self._session.delete(row)
        await self._session.flush()

    async def sync_from_keitaro(
        self,
        campaign_id: CampaignId,
        flows: list[KeitaroFlowSnapshot],
        seen_stream_ids: list[int],
        offer_names: dict[int, str],
    ) -> None:
        # Check offers before touching any other content (FR-013).
        offer_flows = [flow for flow in flows if flow.offers]
        retained_ids = {flow.stream_id for flow in offer_flows}
        # Seen-but-empty and vanished streams must both disappear from the editor.
        # seen_stream_ids is retained in the port for callers that track all streams;
        # only nonempty snapshots can retain cache rows, regardless of that list.
        await self._session.execute(
            delete(CampaignOfferModel).where(
                CampaignOfferModel.campaign_id == campaign_id.value,
                CampaignOfferModel.stream_id.not_in(retained_ids),
            )
        )
        rows = list(
            await self._session.scalars(
                select(CampaignOfferModel).where(
                    CampaignOfferModel.campaign_id == campaign_id.value
                )
            )
        )
        by_key = {(row.stream_id, row.offer_id): row for row in rows}
        seen_keys: set[tuple[int, int]] = set()
        names = {flow.stream_id: flow.name for flow in offer_flows}
        for flow in offer_flows:
            for item in flow.offers:
                key = (flow.stream_id, item.offer_id)
                seen_keys.add(key)
                row = by_key.get(key)
                if row is None:
                    row = CampaignOfferModel(
                        campaign_id=campaign_id.value,
                        stream_id=flow.stream_id,
                        offer_id=item.offer_id,
                        offer_name=f"Offer {item.offer_id}",
                        locked=False,
                    )
                    self._session.add(row)
                    by_key[key] = row
                row.stream_name = flow.name
                row.offer_name = offer_names.get(item.offer_id, row.offer_name)
                # Refresh respects local locks without rebalancing remote weights.
                if not (row.state == OfferState.ACTIVE.value and row.locked):
                    row.share = item.share
                row.state = OfferState.ACTIVE.value
        for row in rows:
            row.stream_name = names[row.stream_id]
            if (row.stream_id, row.offer_id) not in seen_keys:
                row.share = 0
                row.state = OfferState.DELETED.value
                row.locked = False
        await self._session.flush()

from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.presentation.api.keitaro.schemas import (
    FlowOffersResponse,
    OfferResponse,
    OfferRotationResponse,
)


def to_rotation_response(campaign_id: int, flows: list[FlowOffers]) -> OfferRotationResponse:
    return OfferRotationResponse(
        campaign_id=campaign_id,
        flows=[
            FlowOffersResponse(
                stream_id=flow.stream_id.value,
                name=flow.name,
                offers=[
                    OfferResponse(
                        offer_id=item.offer_id.value,
                        name=item.name,
                        share=item.share.value,
                        state=item.state.value,
                        locked=item.locked,
                    )
                    for item in flow.offers
                ],
            )
            for flow in flows
        ],
    )

import { apiRequest } from "./client"

export type CampaignSummary = {
  id: number
  name: string
  state: string
  alias: string
}

export type CatalogItem = { id: number; name: string }

export type FormOptions = {
  domains: CatalogItem[]
  groups: CatalogItem[]
  traffic_sources: CatalogItem[]
}

export type OfferItem = {
  offer_id: number
  name: string
  share: number
  state: "active" | "deleted"
  locked: boolean
}

export type FlowOffers = {
  stream_id: number
  name: string
  offers: OfferItem[]
}

export type OfferRotation = {
  campaign_id: number
  flows: FlowOffers[]
}

export type CreateCampaignPayload = {
  name: string
  country_code: string
  offer_id: number
  domain_id: number
  group_id: number
  traffic_source_id: number
}

export const campaignsApi = {
  list: () => apiRequest<CampaignSummary[]>("/campaigns"),
  formOptions: () => apiRequest<FormOptions>("/campaigns/form-options"),
  offers: () => apiRequest<CatalogItem[]>("/offers"),
  create: (payload: CreateCampaignPayload) =>
    apiRequest<CampaignSummary>("/campaigns", { method: "POST", body: payload }),
  refreshOffers: (campaignId: number) =>
    apiRequest<OfferRotation>(`/campaigns/${campaignId}/offers`),
  addOffer: (campaignId: number, streamId: number, offerId: number) =>
    apiRequest<OfferRotation>(
      `/campaigns/${campaignId}/flows/${streamId}/offers`,
      { method: "POST", body: { offer_id: offerId } },
    ),
  deleteOffer: (campaignId: number, streamId: number, offerId: number) =>
    apiRequest<OfferRotation>(
      `/campaigns/${campaignId}/flows/${streamId}/offers/${offerId}`,
      { method: "DELETE" },
    ),
  restoreOffer: (campaignId: number, streamId: number, offerId: number) =>
    apiRequest<OfferRotation>(
      `/campaigns/${campaignId}/flows/${streamId}/offers/${offerId}/restore`,
      { method: "POST" },
    ),
  lockOffer: (campaignId: number, streamId: number, offerId: number, locked: boolean) =>
    apiRequest<OfferRotation>(
      `/campaigns/${campaignId}/flows/${streamId}/offers/${offerId}/lock`,
      { method: "PATCH", body: { locked } },
    ),
  saveOffers: (campaignId: number) =>
    apiRequest<OfferRotation>(`/campaigns/${campaignId}/offers`, { method: "PUT" }),
}

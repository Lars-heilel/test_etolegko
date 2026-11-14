import { useMutation } from "@tanstack/react-query"
import { useState } from "react"

import { campaignsApi, type OfferItem, type OfferRotation } from "@/shared/api"

// The editor owning this hook is keyed by campaign ID, isolating pending requests.
export function useCampaignOffers(campaignId: number) {
  const [rotation, setRotation] = useState<OfferRotation | null>(null)
  const refresh = useMutation({
    mutationFn: () => campaignsApi.refreshOffers(campaignId),
    onSuccess: setRotation,
    retry: false,
  })
  const add = useMutation({
    mutationFn: ({ streamId, offerId }: { streamId: number; offerId: number }) => campaignsApi.addOffer(campaignId, streamId, offerId),
    onSuccess: setRotation, retry: false,
  })
  const remove = useMutation({
    mutationFn: ({ streamId, offerId }: { streamId: number; offerId: number }) => campaignsApi.deleteOffer(campaignId, streamId, offerId),
    onSuccess: setRotation, retry: false,
  })
  const restore = useMutation({
    mutationFn: ({ streamId, offerId }: { streamId: number; offerId: number }) => campaignsApi.restoreOffer(campaignId, streamId, offerId),
    onSuccess: setRotation, retry: false,
  })
  const lock = useMutation({
    mutationFn: ({ streamId, offer }: { streamId: number; offer: OfferItem }) => campaignsApi.lockOffer(campaignId, streamId, offer.offer_id, !offer.locked),
    onSuccess: setRotation, retry: false,
  })
  const save = useMutation({
    mutationFn: () => campaignsApi.saveOffers(campaignId),
    onSuccess: setRotation, retry: false,
  })
  const pending = [refresh, add, remove, restore, lock, save].some((request) => request.isPending)
  return { rotation, refresh, add, remove, restore, lock, save, pending }
}

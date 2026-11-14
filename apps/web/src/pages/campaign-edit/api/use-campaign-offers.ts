import { useMutation } from "@tanstack/react-query"
import { useState } from "react"

import { campaignsApi, type OfferRotation } from "@/shared/api"

// The editor owning this hook is keyed by campaign ID, isolating pending requests.
export function useCampaignOffers(campaignId: number) {
  const [rotation, setRotation] = useState<OfferRotation | null>(null)
  const refresh = useMutation({
    mutationFn: () => campaignsApi.refreshOffers(campaignId),
    onSuccess: setRotation,
    retry: false,
  })
  return { rotation, setRotation, refresh }
}

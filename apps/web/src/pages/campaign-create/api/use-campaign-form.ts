import { useQuery } from "@tanstack/react-query"

import { campaignsApi } from "@/shared/api"

export function useCampaignForm() {
  return {
    offers: useQuery({ queryKey: ["offers"], queryFn: campaignsApi.offers, staleTime: 60_000 }),
  }
}

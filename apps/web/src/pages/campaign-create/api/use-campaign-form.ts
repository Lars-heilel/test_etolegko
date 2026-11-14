import { useQuery } from "@tanstack/react-query"

import { campaignsApi } from "@/shared/api"

export function useCampaignForm() {
  return {
    options: useQuery({ queryKey: ["campaign-form-options"], queryFn: campaignsApi.formOptions }),
    offers: useQuery({ queryKey: ["offers"], queryFn: campaignsApi.offers, staleTime: 60_000 }),
  }
}

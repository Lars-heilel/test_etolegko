import { useQuery } from "@tanstack/react-query"

import { campaignsApi } from "@/shared/api"

export function useCampaignForm() {
  return {
    formOptions: useQuery({ queryKey: ["campaign-form-options"], queryFn: campaignsApi.formOptions, staleTime: 60_000 }),
    offers: useQuery({ queryKey: ["offers"], queryFn: campaignsApi.offers, staleTime: 60_000 }),
  }
}

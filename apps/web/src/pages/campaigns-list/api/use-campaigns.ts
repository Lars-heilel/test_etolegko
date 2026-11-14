import { useQuery } from "@tanstack/react-query"

import { campaignsApi } from "@/shared/api"

export function useCampaigns() {
  return useQuery({
    queryKey: ["campaigns"],
    queryFn: campaignsApi.list,
    staleTime: 30_000,
  })
}

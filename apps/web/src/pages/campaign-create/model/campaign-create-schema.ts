import { z } from "zod"

import type { CatalogItem } from "@/shared/api"
import { countryOptions } from "@/shared/config"

export const campaignCreateSchema = z.object({
  name: z.string().trim().min(1, "Укажите название"),
  country_code: z.string().refine((code) => countryOptions.some((country) => country.code === code), "Выберите страну"),
  offer_id: z.number().int().positive("Выберите оффер"),
})

export type CampaignCreateValues = z.infer<typeof campaignCreateSchema>

export function campaignCreateCatalogSchema(offers: CatalogItem[]) {
  return campaignCreateSchema.superRefine((values, context) => {
    const catalogs = [
      ["offer_id", offers, "оффер"],
    ] as const
    for (const [field, items, label] of catalogs) {
      if (values[field] > 0 && !items.some((item) => item.id === values[field])) {
        context.addIssue({ code: "custom", path: [field], message: `Выберите ${label} из каталога` })
      }
    }
  })
}

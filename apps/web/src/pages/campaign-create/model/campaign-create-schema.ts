import { z } from "zod"

import type { CatalogItem, FormOptions } from "@/shared/api"
import { countryOptions } from "@/shared/config"

export const campaignCreateSchema = z.object({
  name: z.string().trim().min(1, "Укажите название"),
  country_code: z.string().refine((code) => countryOptions.some((country) => country.code === code), "Выберите страну"),
  offer_id: z.number().int().positive("Выберите оффер"),
  group_id: z.number().int().positive("Выберите группу"),
  traffic_source_id: z.number().int().positive("Выберите источник").optional(),
  domain_id: z.number().int().positive("Выберите домен").optional(),
})

export type CampaignCreateValues = z.infer<typeof campaignCreateSchema>

export function campaignCreateCatalogSchema(offers: CatalogItem[], options: FormOptions) {
  return campaignCreateSchema.superRefine((values, context) => {
    const catalogs = [
      ["offer_id", offers, "оффер"],
      ["group_id", options.groups, "группу"],
      ["traffic_source_id", options.traffic_sources, "источник"],
      ["domain_id", options.domains, "домен"],
    ] as const
    for (const [field, items, label] of catalogs) {
      const value = values[field]
      if (value !== undefined && value > 0 && !items.some((item) => item.id === value)) {
        context.addIssue({ code: "custom", path: [field], message: `Выберите ${label} из каталога` })
      }
    }
  })
}

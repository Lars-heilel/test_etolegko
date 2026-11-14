import { z } from "zod"

import type { CatalogItem, FormOptions } from "@/shared/api"
import { countryOptions } from "@/shared/config"

export const campaignCreateSchema = z.object({
  name: z.string().trim().min(1, "Укажите название"),
  country_code: z.string().refine((code) => countryOptions.some((country) => country.code === code), "Выберите страну"),
  offer_id: z.number().int().positive("Выберите оффер"),
  domain_id: z.number().int().positive("Выберите домен"),
  group_id: z.number().int().positive("Выберите группу"),
  traffic_source_id: z.number().int().positive("Выберите источник"),
})

export type CampaignCreateValues = z.infer<typeof campaignCreateSchema>

export function campaignCreateCatalogSchema(options: FormOptions | undefined, offers: CatalogItem[]) {
  return campaignCreateSchema.superRefine((values, context) => {
    const catalogs = [
      ["offer_id", offers, "оффер"],
      ["domain_id", options?.domains ?? [], "домен"],
      ["group_id", options?.groups ?? [], "группу"],
      ["traffic_source_id", options?.traffic_sources ?? [], "источник"],
    ] as const
    for (const [field, items, label] of catalogs) {
      if (values[field] > 0 && !items.some((item) => item.id === values[field])) {
        context.addIssue({ code: "custom", path: [field], message: `Выберите ${label} из каталога` })
      }
    }
  })
}

import { useRef, useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { useForm, useWatch } from "react-hook-form"
import { Link, useNavigate } from "react-router-dom"
import { ArrowLeftIcon } from "lucide-react"
import { toast } from "sonner"

import { campaignsApi, type CatalogItem } from "@/shared/api"
import { countryOptions } from "@/shared/config"
import { getApiErrorMessage } from "@/shared/lib/get-api-error-message"
import { Alert, AlertDescription, AlertTitle, Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from "@/shared/ui"

import { useCampaignForm } from "../api/use-campaign-form"
import { campaignCreateCatalogSchema, type CampaignCreateValues } from "../model/campaign-create-schema"

export function CampaignCreatePage() {
  const navigate = useNavigate()
  const { options, offers } = useCampaignForm()
  const [offerSearch, setOfferSearch] = useState("")
  const submitting = useRef(false)
  const form = useForm<CampaignCreateValues>({
    resolver: zodResolver(campaignCreateCatalogSchema(options.data, offers.data ?? [])),
    defaultValues: { name: "", country_code: "", offer_id: 0, domain_id: 0, group_id: 0, traffic_source_id: 0 },
  })
  const selectedOffer = useWatch({ control: form.control, name: "offer_id" })
  const filteredOffers = (offers.data ?? []).filter((offer) =>
    offer.id === selectedOffer || offer.name.toLowerCase().includes(offerSearch.trim().toLowerCase()),
  )
  const mutation = useMutation({
    mutationFn: (values: CampaignCreateValues) => campaignsApi.create(values),
    retry: false,
    onSuccess: (campaign) => {
      toast.success("Кампания создана")
      navigate(`/campaigns/${campaign.id}/edit`)
    },
  })
  const catalogs = [
    { name: "offer_id", label: "Оффер", items: offers.data ?? [], visible: filteredOffers, missing: "офферов" },
    { name: "domain_id", label: "Домен", items: options.data?.domains ?? [], missing: "доменов" },
    { name: "group_id", label: "Группа", items: options.data?.groups ?? [], missing: "групп" },
    { name: "traffic_source_id", label: "Источник", items: options.data?.traffic_sources ?? [], missing: "источников" },
  ] satisfies { name: keyof CampaignCreateValues; label: string; items: CatalogItem[]; visible?: CatalogItem[]; missing: string }[]
  const loaded = options.isSuccess && offers.isSuccess
  const blocked = !loaded || catalogs.some((catalog) => catalog.items.length === 0)
  const pending = mutation.isPending || form.formState.isSubmitting
  const error = (name: keyof CampaignCreateValues) => form.formState.errors[name]
  const validation = (name: keyof CampaignCreateValues) => error(name) ? (
    <p id={`${name}-error`} className="text-sm text-destructive">{error(name)?.message}</p>
  ) : null
  const selectClass = "h-9 rounded-md border bg-background px-3 text-sm"

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <Button asChild className="w-fit" size="sm" variant="ghost">
          <Link to="/campaigns">
            <ArrowLeftIcon data-icon="inline-start" />
            Назад к кампаниям
          </Link>
        </Button>
        <h1 className="text-2xl font-semibold tracking-tight">Новая кампания</h1>
        <p className="text-sm text-muted-foreground">
          Название, гео, оффер, домен, группа и источник трафика.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Форма создания</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" noValidate onSubmit={(event) => { void form.handleSubmit(async (values) => {
            if (blocked || submitting.current) return
            submitting.current = true
            try {
              await mutation.mutateAsync(values)
            } catch {
              // The mutation error is rendered below, including uncertain/partial outcomes.
            } finally {
              submitting.current = false
            }
          })(event) }}>
            {!loaded && !options.isError && !offers.isError && <p role="status">Загрузка каталогов…</p>}
            {(options.isError || offers.isError) && <Alert variant="destructive">
              <AlertTitle>Не удалось загрузить каталоги</AlertTitle>
              <AlertDescription>{getApiErrorMessage(options.error ?? offers.error)}</AlertDescription>
              <Button type="button" variant="outline" onClick={() => { void options.refetch(); void offers.refetch() }}>Повторить загрузку</Button>
            </Alert>}
            {loaded && catalogs.filter((catalog) => catalog.items.length === 0).map((catalog) => <Alert key={catalog.name}>
              <AlertTitle>Нет {catalog.missing} в каталоге Keitaro</AlertTitle>
              <AlertDescription>Добавьте записи в Keitaro и обновите каталоги. Для создания нужен существующий ID из каталога.</AlertDescription>
            </Alert>)}
            {loaded && blocked && <Button type="button" variant="outline" onClick={() => { void options.refetch(); void offers.refetch() }}>Обновить каталоги</Button>}
            <fieldset disabled={pending} className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="name">Название кампании</Label>
                <Input id="name" aria-required aria-invalid={!!error("name")} aria-describedby="name-error" {...form.register("name")} />
                {validation("name")}
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="country_code">Гео</Label>
                <select id="country_code" className={selectClass} aria-required aria-invalid={!!error("country_code")} aria-describedby="country_code-error" {...form.register("country_code")}>
                  <option value="">Выберите</option>
                  {countryOptions.map((country) => <option key={country.code} value={country.code}>{country.name} ({country.code})</option>)}
                </select>
                {validation("country_code")}
              </div>
              <Input aria-label="Поиск оффера" placeholder="Поиск оффера" value={offerSearch} onChange={(event) => setOfferSearch(event.target.value)} />
              {catalogs.map((catalog) => <div key={catalog.name} className="flex flex-col gap-2">
                <Label htmlFor={catalog.name}>{catalog.label}</Label>
                <select id={catalog.name} className={selectClass} disabled={!loaded || catalog.items.length === 0} aria-required aria-invalid={!!error(catalog.name)} aria-describedby={`${catalog.name}-error`} {...form.register(catalog.name, { valueAsNumber: true })}>
                  <option value="0">Выберите</option>
                  {(catalog.visible ?? catalog.items).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
                {validation(catalog.name)}
              </div>)}
            </fieldset>
            {mutation.error && <Alert variant="destructive">
              <AlertTitle>Создание не завершено</AlertTitle>
              <AlertDescription>{getApiErrorMessage(mutation.error)}</AlertDescription>
            </Alert>}
            <Button disabled={blocked || pending} type="submit">{pending ? "Создание…" : "Создать"}</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

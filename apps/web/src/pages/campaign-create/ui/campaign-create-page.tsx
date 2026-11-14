import { useRef, useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm, useWatch } from "react-hook-form"
import { Link, useNavigate } from "react-router-dom"
import { ArrowLeftIcon } from "lucide-react"
import { toast } from "sonner"

import { campaignsApi, type FormOptions } from "@/shared/api"
import { countryOptions } from "@/shared/config"
import { getApiErrorMessage } from "@/shared/lib/get-api-error-message"
import { Alert, AlertDescription, AlertTitle, Button, Card, CardContent, CardHeader, CardTitle, Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, Input, Label } from "@/shared/ui"

import { useCampaignForm } from "../api/use-campaign-form"
import { campaignCreateCatalogSchema, type CampaignCreateValues } from "../model/campaign-create-schema"

export function CampaignCreatePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { offers, formOptions } = useCampaignForm()
  const catalogs = formOptions.data ?? { domains: [], groups: [], traffic_sources: [] }
  const [offerSearch, setOfferSearch] = useState("")
  const [offerOpen, setOfferOpen] = useState(false)
  const [sourceOpen, setSourceOpen] = useState(false)
  const [sourceName, setSourceName] = useState("")
  const sourceSubmitting = useRef(false)
  const submitting = useRef(false)
  const form = useForm<CampaignCreateValues>({
    resolver: zodResolver(campaignCreateCatalogSchema(offers.data ?? [], catalogs)),
    defaultValues: { name: "", country_code: "", offer_id: 0, group_id: 0 },
  })
  const selectedSource = useWatch({ control: form.control, name: "traffic_source_id" })
  const mutation = useMutation({
    mutationFn: (values: CampaignCreateValues) => campaignsApi.create(values),
    retry: false,
    onSuccess: (campaign) => {
      toast.success("Кампания создана")
      navigate(`/campaigns/${campaign.id}/edit`)
    },
  })
  const sourceMutation = useMutation({
    mutationFn: campaignsApi.createTrafficSource,
    retry: false,
    onSuccess: async (source) => {
      await queryClient.cancelQueries({ queryKey: ["campaign-form-options"] })
      queryClient.setQueryData<FormOptions>(["campaign-form-options"], (current) => current ? {
        ...current,
        traffic_sources: [...current.traffic_sources.filter((item) => item.id !== source.id), source],
      } : undefined)
      form.setValue("traffic_source_id", source.id, { shouldDirty: true })
      form.clearErrors("traffic_source_id")
      setSourceOpen(false)
      setSourceName("")
      toast.success("Источник создан и выбран")
    },
  })
  const loaded = offers.isSuccess && formOptions.isSuccess
  const missing = [
    !offers.data?.length && "офферы",
    !catalogs.groups.length && "группы",
  ].filter(Boolean)
  const blocked = !loaded || missing.length > 0
  const catalogError = offers.error ?? formOptions.error
  const refreshing = offers.isFetching || formOptions.isFetching
  const refreshCatalogs = () => { void offers.refetch(); void formOptions.refetch() }
  const campaignPending = mutation.isPending || form.formState.isSubmitting
  const pending = campaignPending || sourceMutation.isPending
  const createSource = async () => {
    const name = sourceName.trim()
    if (!name || pending || sourceSubmitting.current || !loaded || refreshing) return
    sourceSubmitting.current = true
    try {
      await sourceMutation.mutateAsync(name)
    } catch {
      // Keep the name and upstream outcome visible; POST is never automatically retried.
    } finally {
      sourceSubmitting.current = false
    }
  }
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
           Название, гео, оффер и группа. Домен и источник — необязательно.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Форма создания</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" noValidate onSubmit={(event) => { void form.handleSubmit(async (values) => {
             if (blocked || submitting.current || sourceSubmitting.current) return
            submitting.current = true
            try {
              await mutation.mutateAsync(values)
            } catch {
              // The mutation error is rendered below, including uncertain/partial outcomes.
            } finally {
              submitting.current = false
            }
          })(event) }}>
            {!loaded && !catalogError && <p role="status">Загрузка каталогов…</p>}
            {catalogError && <Alert variant="destructive">
              <AlertTitle>Не удалось загрузить каталоги</AlertTitle>
              <AlertDescription>{getApiErrorMessage(catalogError)}</AlertDescription>
              <Button type="button" variant="outline" disabled={refreshing || pending} onClick={refreshCatalogs}>Повторить загрузку</Button>
            </Alert>}
            {loaded && blocked && <Alert>
              <AlertTitle>Нет доступных: {missing.join(", ")}</AlertTitle>
              <AlertDescription>Источник можно создать ниже в этой форме. Недостающие группы и офферы добавьте в Keitaro, затем обновите каталоги.</AlertDescription>
            </Alert>}
            {loaded && <Button type="button" variant="outline" disabled={refreshing || pending} onClick={refreshCatalogs}>Обновить каталоги</Button>}
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
              <div className="flex flex-col gap-2">
                <Label htmlFor="offer_id">Оффер</Label>
                <Command label="Оффер" onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOfferOpen(false) }}>
                  <CommandInput id="offer_id" aria-label="Оффер" placeholder="Поиск оффера" disabled={!offers.isSuccess || pending} aria-required aria-expanded={offerOpen} aria-invalid={!!error("offer_id")} aria-describedby="offer_id-error" value={offerSearch} onFocus={() => setOfferOpen(true)} onValueChange={(value) => {
                    setOfferSearch(value)
                    setOfferOpen(true)
                    form.setValue("offer_id", 0)
                  }} onKeyDown={(event) => { if (event.key === "Escape") setOfferOpen(false) }} />
                  {offerOpen && <CommandList>
                    <CommandEmpty>Офферы не найдены</CommandEmpty>
                    <CommandGroup>
                      {(offers.data ?? []).map((offer) => <CommandItem key={offer.id} value={String(offer.id)} keywords={[offer.name]} onSelect={() => {
                        form.setValue("offer_id", offer.id, { shouldValidate: true })
                        setOfferSearch(offer.name)
                        setOfferOpen(false)
                      }}>{offer.name}</CommandItem>)}
                    </CommandGroup>
                  </CommandList>}
                </Command>
                {validation("offer_id")}
              </div>
              {([
                ["group_id", "Группа", catalogs.groups],
                ["traffic_source_id", "Источник (необязательно)", catalogs.traffic_sources],
                ["domain_id", "Домен (необязательно)", catalogs.domains],
              ] as const).map(([field, label, items]) => (
                <div key={field} className="flex flex-col gap-2">
                  <Label htmlFor={field}>{label}</Label>
                  <select id={field} className={selectClass} value={field === "traffic_source_id" ? selectedSource || "" : undefined} disabled={!loaded} aria-required={field === "group_id"} aria-invalid={!!error(field)} aria-describedby={`${field}-error`} {...form.register(field, { setValueAs: (value: string) => value === "" ? (field === "group_id" ? 0 : undefined) : Number(value) })}>
                    <option value="">{field === "domain_id" ? "Без домена" : field === "traffic_source_id" ? "Без источника" : "Выберите"}</option>
                    {items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                  {validation(field)}
                  {field === "traffic_source_id" && <>
                    <Alert>
                      <AlertTitle>Почему источник необязателен?</AlertTitle>
                      <AlertDescription>В выданном трекере создание источника недоступно из-за ограничения прав API-ключа (HTTP 403). Поэтому временно можно создать кампанию без источника. Если источник уже есть, выберите его; для создания нового администратор должен предоставить права. Исходное требование о настроенном источнике будет выполнено после его подключения.</AlertDescription>
                    </Alert>
                    {!sourceOpen ? <Button type="button" variant="outline" disabled={!loaded || refreshing} onClick={() => { sourceMutation.reset(); setSourceOpen(true) }}>Создать источник</Button> : <div className="flex flex-col gap-2 rounded-md border p-3">
                      <Label htmlFor="source_name">Название источника</Label>
                      <Input id="source_name" value={sourceName} onChange={(event) => setSourceName(event.target.value)} onKeyDown={(event) => {
                        if (event.key === "Enter") { event.preventDefault(); void createSource() }
                      }} />
                      <p className="text-sm text-muted-foreground">Источник будет создан в Keitaro и выбран для этой кампании.</p>
                      <div className="flex gap-2">
                        <Button type="button" disabled={!sourceName.trim() || !loaded || refreshing || pending} onClick={() => { void createSource() }}>{sourceMutation.isPending ? "Создание источника…" : "Сохранить источник"}</Button>
                        <Button type="button" variant="ghost" disabled={pending} onClick={() => { setSourceOpen(false); sourceMutation.reset() }}>Отмена</Button>
                      </div>
                    </div>}
                    {sourceMutation.error && <Alert variant="destructive">
                      <AlertTitle>Не удалось подтвердить создание источника</AlertTitle>
                      <AlertDescription>{getApiErrorMessage(sourceMutation.error)}</AlertDescription>
                    </Alert>}
                  </>}
                </div>
              ))}
              <Alert>
                <AlertTitle>Почему домен необязателен?</AlertTitle>
                <AlertDescription>
                  При проверке выданного трекера 14.11.2026 список доменов был пуст, а создание домена с выданным API-ключом вернуло HTTP 403 — недостаточно прав. Поэтому временно разрешено создание кампании без домена. Для выполнения исходного требования администратор должен предоставить подключённый домен; после этого его можно выбрать из списка.
                </AlertDescription>
              </Alert>
              {loaded && catalogs.domains.length === 0 && <p className="text-sm text-muted-foreground">Нет доступных доменов в Keitaro. Кампанию можно создать без домена.</p>}
            </fieldset>
            {mutation.error && <Alert variant="destructive">
              <AlertTitle>Создание не завершено</AlertTitle>
              <AlertDescription>{getApiErrorMessage(mutation.error)}</AlertDescription>
            </Alert>}
            <Button disabled={blocked || pending} type="submit">{campaignPending ? "Создание…" : "Создать"}</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

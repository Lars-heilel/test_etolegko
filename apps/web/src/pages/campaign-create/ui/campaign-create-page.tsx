import { useRef, useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { Link, useNavigate } from "react-router-dom"
import { ArrowLeftIcon } from "lucide-react"
import { toast } from "sonner"

import { campaignsApi } from "@/shared/api"
import { countryOptions } from "@/shared/config"
import { getApiErrorMessage } from "@/shared/lib/get-api-error-message"
import { Alert, AlertDescription, AlertTitle, Button, Card, CardContent, CardHeader, CardTitle, Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, Input, Label } from "@/shared/ui"

import { useCampaignForm } from "../api/use-campaign-form"
import { campaignCreateCatalogSchema, type CampaignCreateValues } from "../model/campaign-create-schema"

export function CampaignCreatePage() {
  const navigate = useNavigate()
  const { offers } = useCampaignForm()
  const [offerSearch, setOfferSearch] = useState("")
  const [offerOpen, setOfferOpen] = useState(false)
  const submitting = useRef(false)
  const form = useForm<CampaignCreateValues>({
    resolver: zodResolver(campaignCreateCatalogSchema(offers.data ?? [])),
    defaultValues: { name: "", country_code: "", offer_id: 0 },
  })
  const mutation = useMutation({
    mutationFn: (values: CampaignCreateValues) => campaignsApi.create(values),
    retry: false,
    onSuccess: (campaign) => {
      toast.success("Кампания создана")
      navigate(`/campaigns/${campaign.id}/edit`)
    },
  })
  const loaded = offers.isSuccess
  const blocked = !loaded || offers.data.length === 0
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
          Название, гео и оффер.
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
            {!loaded && !offers.isError && <p role="status">Загрузка каталогов…</p>}
            {offers.isError && <Alert variant="destructive">
              <AlertTitle>Не удалось загрузить каталоги</AlertTitle>
              <AlertDescription>{getApiErrorMessage(offers.error)}</AlertDescription>
              <Button type="button" variant="outline" onClick={() => { void offers.refetch() }}>Повторить загрузку</Button>
            </Alert>}
            {loaded && blocked && <Alert>
              <AlertTitle>Нет офферов в каталоге Keitaro</AlertTitle>
              <AlertDescription>Добавьте записи в Keitaro и обновите каталоги. Для создания нужен существующий ID из каталога.</AlertDescription>
            </Alert>}
            {loaded && blocked && <Button type="button" variant="outline" onClick={() => { void offers.refetch() }}>Обновить каталоги</Button>}
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
                  <CommandInput id="offer_id" aria-label="Оффер" placeholder="Поиск оффера" disabled={blocked || pending} aria-required aria-expanded={offerOpen} aria-invalid={!!error("offer_id")} aria-describedby="offer_id-error" value={offerSearch} onFocus={() => setOfferOpen(true)} onValueChange={(value) => {
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

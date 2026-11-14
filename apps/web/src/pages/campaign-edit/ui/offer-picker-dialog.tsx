import { useQuery } from "@tanstack/react-query"
import { useId, useState } from "react"

import { campaignsApi, type FlowOffers } from "@/shared/api"
import { getApiErrorMessage } from "@/shared/lib/get-api-error-message"
import { Alert, AlertDescription, AlertTitle, Button, Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, Input, Label } from "@/shared/ui"

type Props = {
  flow: FlowOffers
  pending: boolean
  error: Error | null
  onClose: () => void
  onPick: (offerId: number) => void
}

export function OfferPickerDialog({ flow, pending, error, onClose, onPick }: Props) {
  const [search, setSearch] = useState("")
  const searchId = useId()
  const offers = useQuery({
    queryKey: ["offers"], queryFn: campaignsApi.offers, retry: false,
    refetchOnReconnect: false, refetchOnWindowFocus: false,
  })
  const used = new Set(flow.offers.map((offer) => offer.offer_id))
  const term = search.trim().toLowerCase()
  const filtered = (offers.data ?? []).filter((offer) => !used.has(offer.id) && offer.name.toLowerCase().includes(term))

  return (
    <Dialog open onOpenChange={(open) => { if (!open && !pending) onClose() }}>
      <DialogContent showCloseButton={!pending}>
        <DialogHeader>
          <DialogTitle>Добавить оффер в «{flow.name}»</DialogTitle>
          <DialogDescription>Выберите оффер для добавления в поток.</DialogDescription>
        </DialogHeader>
        <Label htmlFor={searchId}>Поиск оффера</Label>
        <Input id={searchId} value={search} onChange={(event) => setSearch(event.target.value)} />
        {(error || offers.error) && (
          <Alert variant="destructive">
            <AlertTitle>Ошибка</AlertTitle>
            <AlertDescription>{getApiErrorMessage(error || offers.error)}</AlertDescription>
          </Alert>
        )}
        {offers.isError && <Button disabled={offers.isFetching || pending} onClick={() => void offers.refetch()}>Повторить</Button>}
        {offers.isPending && <p role="status">Загрузка офферов…</p>}
        <div className="flex max-h-80 flex-col gap-1 overflow-y-auto">
          {filtered.map((offer) => (
            <Button key={offer.id} disabled={pending} variant="ghost" className="justify-start" onClick={() => onPick(offer.id)}>{offer.name}</Button>
          ))}
          {offers.isSuccess && filtered.length === 0 && <p className="text-sm text-muted-foreground">Подходящих офферов нет.</p>}
        </div>
      </DialogContent>
    </Dialog>
  )
}

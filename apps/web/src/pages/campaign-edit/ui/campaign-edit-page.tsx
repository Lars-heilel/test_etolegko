import { Link, useParams } from "react-router-dom"
import { ArrowLeftIcon } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { getApiErrorMessage } from "@/shared/lib/get-api-error-message"
import { Alert, AlertDescription, AlertTitle, Badge, Button, Card, CardContent, CardHeader, CardTitle } from "@/shared/ui"

import { useCampaignOffers } from "../api/use-campaign-offers"
import { FlowOffersCard } from "./flow-offers-card"
import { OfferPickerDialog } from "./offer-picker-dialog"

export function CampaignEditPage() {
  const { campaignId } = useParams()
  const id = Number(campaignId)
  const validId = /^\d+$/.test(campaignId ?? "") && Number.isSafeInteger(id) && id > 0

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <Button asChild className="w-fit" size="sm" variant="ghost">
          <Link to="/campaigns">
            <ArrowLeftIcon data-icon="inline-start" />
            Назад к кампаниям
          </Link>
        </Button>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">Редактор кампании</h1>
          <Badge variant="outline">ID: {campaignId}</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Потоки, офферы и проценты ротации.
        </p>
      </div>

      {validId ? <CampaignOffersEditor key={id} campaignId={id} /> : (
        <Alert variant="destructive"><AlertTitle>Некорректный ID кампании</AlertTitle></Alert>
      )}
    </div>
  )
}

function CampaignOffersEditor({ campaignId }: { campaignId: number }) {
  const { rotation, refresh, add, remove, restore, lock, save, pending } = useCampaignOffers(campaignId)
  const [pickerStream, setPickerStream] = useState<number | null>(null)
  const pickerFlow = rotation?.flows.find((flow) => flow.stream_id === pickerStream)
  const startOperation = (operation: () => void) => {
    if (pending) return
    for (const request of [refresh, add, remove, restore, lock, save]) {
      if (request.isError) request.reset()
    }
    operation()
  }

  return (
    <>
      <div className="flex gap-2">
        <Button disabled={pending} onClick={() => startOperation(() => refresh.mutate())}>Получить потоки</Button>
        <Button disabled={!rotation || pending} onClick={() => startOperation(() => save.mutate(undefined, { onSuccess: () => toast.success("Изменения сохранены в Keitaro") }))}>Сохранить</Button>
      </div>
      {refresh.isPending && <p role="status" className="text-sm text-muted-foreground">Загрузка потоков…</p>}
      {refresh.error && (
        <Alert variant="destructive">
          <AlertTitle>Не удалось получить потоки</AlertTitle>
          <AlertDescription>{getApiErrorMessage(refresh.error)}</AlertDescription>
        </Alert>
      )}
      {[add, remove, restore, lock, save].map((mutation, index) => mutation.error && (
        <Alert key={index} variant="destructive">
          <AlertTitle>Не удалось выполнить действие</AlertTitle>
          <AlertDescription>{getApiErrorMessage(mutation.error)}</AlertDescription>
        </Alert>
      ))}
      {!rotation && !refresh.isPending && (
        <Card>
          <CardHeader><CardTitle>Потоки не загружены</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Нажмите «Получить потоки», чтобы загрузить данные из Keitaro.
          </CardContent>
        </Card>
      )}
      {rotation?.flows.length === 0 && (
        <Card>
          <CardHeader><CardTitle>Потоков нет</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">В кампании пока нет потоков.</CardContent>
        </Card>
      )}
      {rotation?.flows.map((flow) => (
        <FlowOffersCard key={flow.stream_id} flow={flow} disabled={pending}
          onAdd={() => startOperation(() => setPickerStream(flow.stream_id))}
          onDelete={(offer) => startOperation(() => remove.mutate({ streamId: flow.stream_id, offerId: offer.offer_id }))}
          onRestore={(offer) => startOperation(() => restore.mutate({ streamId: flow.stream_id, offerId: offer.offer_id }))}
          onLock={(offer) => startOperation(() => lock.mutate({ streamId: flow.stream_id, offer }))}
        />
      ))}
      {pickerFlow && (
        <OfferPickerDialog flow={pickerFlow} pending={pending} error={add.error}
          onClose={() => setPickerStream(null)}
          onPick={(offerId) => startOperation(() => add.mutate({ streamId: pickerFlow.stream_id, offerId }, { onSuccess: () => setPickerStream(null) }))}
        />
      )}
    </>
  )
}

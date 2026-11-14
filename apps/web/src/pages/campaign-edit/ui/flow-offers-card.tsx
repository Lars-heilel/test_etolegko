import { LockIcon, Trash2Icon, Undo2Icon } from "lucide-react"

import type { FlowOffers, OfferItem } from "@/shared/api"
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui"

type Props = {
  flow: FlowOffers
  onAdd?: () => void
  onDelete?: (offer: OfferItem) => void
  onRestore?: (offer: OfferItem) => void
  onLock?: (offer: OfferItem) => void
  disabled?: boolean
}

export function FlowOffersCard({ flow, onAdd, onDelete, onRestore, onLock, disabled }: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle>{flow.name}</CardTitle>
          <Button onClick={onAdd} disabled={disabled || !onAdd} size="sm">Добавить оффер</Button>
        </div>
      </CardHeader>
      <CardContent>
        <Table aria-label={flow.name}>
          <TableHeader>
            <TableRow>
              <TableHead>Оффер</TableHead>
              <TableHead>Процент</TableHead>
              <TableHead>Состояние</TableHead>
              <TableHead>Действия</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {flow.offers.map((offer) => (
              <TableRow key={offer.offer_id}>
                <TableCell>{offer.name}</TableCell>
                <TableCell>{offer.share}%</TableCell>
                <TableCell>
                  {offer.state === "deleted" ? <Badge variant="secondary">удалён</Badge> : (
                    <Badge variant={offer.locked ? "default" : "outline"}>{offer.locked ? "зафиксирован" : "активен"}</Badge>
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    {offer.state === "deleted" ? (
                      <Button disabled={disabled || !onRestore} onClick={() => onRestore?.(offer)} size="sm" variant="outline">
                        <Undo2Icon data-icon="inline-start" />Вернуть
                      </Button>
                    ) : (
                      <>
                        <Button disabled={disabled || !onLock} onClick={() => onLock?.(offer)} size="sm" variant="outline">
                          <LockIcon data-icon="inline-start" />{offer.locked ? "Снять фиксацию" : "Зафиксировать процент"}
                        </Button>
                        <Button disabled={disabled || !onDelete} onClick={() => onDelete?.(offer)} size="sm" variant="destructive">
                          <Trash2Icon data-icon="inline-start" />Удалить
                        </Button>
                      </>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {flow.offers.length === 0 && <TableRow><TableCell colSpan={4}>Офферов нет</TableCell></TableRow>}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { PlusIcon } from "lucide-react"

import { getApiErrorMessage } from "@/shared/lib/get-api-error-message"
import {
  Alert, AlertDescription, AlertTitle, Button, Card, CardContent,
  CardHeader, CardTitle, Input, Skeleton,
} from "@/shared/ui"

import { useCampaigns } from "../api/use-campaigns"

export function CampaignsListPage() {
  const [search, setSearch] = useState("")
  const { data, isPending, error } = useCampaigns()
  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return (data ?? []).filter((campaign) => campaign.name.toLowerCase().includes(term))
  }, [data, search])

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">Кампании</h1>
          <p className="text-sm text-muted-foreground">
            Создание кампаний и управление офферами в Keitaro.
          </p>
        </div>
        <Button asChild>
          <Link to="/campaigns/new">
            <PlusIcon data-icon="inline-start" />
            Создать кампанию
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Список кампаний</CardTitle>
          <Input
            aria-label="Поиск кампаний"
            placeholder="Поиск по названию"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {isPending && <Skeleton role="status" aria-label="Загрузка кампаний" className="h-24 w-full" />}
          {error && (
            <Alert variant="destructive">
              <AlertTitle>Не удалось загрузить кампании</AlertTitle>
              <AlertDescription>{getApiErrorMessage(error)}</AlertDescription>
            </Alert>
          )}
          {!isPending && !error && filtered.length === 0 && (
            <p className="text-sm text-muted-foreground">Кампании не найдены.</p>
          )}
          {filtered.map((campaign) => (
            <Link
              key={campaign.id}
              to={`/campaigns/${campaign.id}/edit`}
              className="flex items-center justify-between rounded-lg border p-4 hover:bg-accent"
            >
              <span className="font-medium">{campaign.name}</span>
              <span className="text-sm text-muted-foreground">{campaign.state}</span>
            </Link>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

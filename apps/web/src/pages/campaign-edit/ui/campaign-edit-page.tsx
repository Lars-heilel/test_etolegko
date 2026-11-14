import { Link, useParams } from "react-router-dom"
import { ArrowLeftIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle, Badge, Button, Card, CardContent, CardHeader, CardTitle } from "@/shared/ui"

export function CampaignEditPage() {
  const { campaignId } = useParams()

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

      <Card>
        <CardHeader>
          <CardTitle>Редактор офферов</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertTitle>Этап инициализации</AlertTitle>
            <AlertDescription>
              Загрузка кампании из Keitaro, добавление и удаление офферов будут добавлены
              на следующем этапе.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    </div>
  )
}

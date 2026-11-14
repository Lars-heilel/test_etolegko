import { Link } from "react-router-dom"
import { ArrowLeftIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle, Button, Card, CardContent, CardHeader, CardTitle } from "@/shared/ui"

export function CampaignCreatePage() {
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
          <Alert>
            <AlertTitle>Этап инициализации</AlertTitle>
            <AlertDescription>
              Форма, поиск офферов и вызовы Keitaro API будут добавлены на следующем этапе.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    </div>
  )
}

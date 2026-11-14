import { Link } from "react-router-dom"
import { PlusIcon } from "lucide-react"

import { Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui"

export function CampaignsListPage() {
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
          <div className="flex items-center justify-between gap-4">
            <CardTitle>Список кампаний</CardTitle>
            <Badge variant="secondary">Окружение готово</Badge>
          </div>
          <CardDescription>
            Здесь появится список кампаний после подключения Keitaro API.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex min-h-48 flex-col items-center justify-center gap-3 rounded-lg border border-dashed p-6 text-center">
            <p className="text-sm font-medium">Пока пусто</p>
            <p className="max-w-md text-sm text-muted-foreground">
              Это заглушка этапа инициализации проекта. Бизнес-логика и запросы к Keitaro
              добавляются на следующем этапе.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

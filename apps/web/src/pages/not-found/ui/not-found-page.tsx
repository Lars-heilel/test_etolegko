import { Link } from "react-router-dom"

import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui"

export function NotFoundPage() {
  return (
    <Card className="mx-auto mt-12 w-full max-w-lg">
      <CardHeader>
        <CardTitle>Страница не найдена</CardTitle>
        <CardDescription>Такого маршрута в приложении нет.</CardDescription>
      </CardHeader>
      <CardContent>
        <Button asChild>
          <Link to="/campaigns">Вернуться к кампаниям</Link>
        </Button>
      </CardContent>
    </Card>
  )
}

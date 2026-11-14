import { Link, Outlet } from "react-router-dom"

export function RootLayout() {
  return (
    <div className="flex min-h-svh flex-col bg-background text-foreground">
      <header className="border-b">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center gap-6 px-6">
          <Link className="font-semibold tracking-tight" to="/campaigns">
            Keitaro Campaign Manager
          </Link>
          <nav className="flex items-center gap-4 text-sm text-muted-foreground">
            <Link className="transition-colors hover:text-foreground" to="/campaigns">
              Кампании
            </Link>
            <Link className="transition-colors hover:text-foreground" to="/campaigns/new">
              Создать
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}

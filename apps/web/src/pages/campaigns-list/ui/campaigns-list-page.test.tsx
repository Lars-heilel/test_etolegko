import "@testing-library/jest-dom/vitest"
import type { ReactElement } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createMemoryRouter, RouterProvider } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError, campaignsApi, type CampaignSummary } from "@/shared/api"

import { CampaignsListPage } from "./campaigns-list-page"

function renderWithProviders(ui: ReactElement, path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter([{ path: "/campaigns", element: ui }], {
    initialEntries: [path],
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

const campaigns: CampaignSummary[] = [
  { id: 17, name: "Alpha", state: "active", alias: "beta-alias" },
  { id: 42, name: "Beta", state: "paused", alias: "other" },
]

describe("CampaignsListPage", () => {
  beforeEach(() => {
    vi.spyOn(campaignsApi, "list").mockResolvedValue(campaigns)
  })

  afterEach(() => vi.restoreAllMocks())

  it("filters locally by trimmed, case-insensitive name and restores results on clear", async () => {
    const user = userEvent.setup()
    renderWithProviders(<CampaignsListPage />, "/campaigns")
    expect(await screen.findByText("Alpha")).toBeInTheDocument()
    const search = screen.getByRole("textbox", { name: "Поиск кампаний" })
    await user.type(search, "  bET  ")
    expect(screen.queryByText("Alpha")).not.toBeInTheDocument()
    expect(screen.getByText("Beta")).toBeInTheDocument()
    await user.clear(search)
    expect(screen.getByText("Alpha")).toBeInTheDocument()
    expect(screen.getByText("Beta")).toBeInTheDocument()
    expect(campaignsApi.list).toHaveBeenCalledTimes(1)
  })

  it("links each campaign ID to its editor and exposes campaign creation", async () => {
    renderWithProviders(<CampaignsListPage />, "/campaigns")
    expect(await screen.findByRole("link", { name: /Alpha/ })).toHaveAttribute("href", "/campaigns/17/edit")
    expect(screen.getByRole("link", { name: /Beta/ })).toHaveAttribute("href", "/campaigns/42/edit")
    expect(screen.getByRole("link", { name: "Создать кампанию" })).toHaveAttribute("href", "/campaigns/new")
  })

  it("shows loading until the request resolves without showing an empty result", async () => {
    let resolve!: (value: CampaignSummary[]) => void
    vi.mocked(campaignsApi.list).mockReturnValue(new Promise((done) => { resolve = done }))
    renderWithProviders(<CampaignsListPage />, "/campaigns")
    expect(screen.getByRole("status", { name: "Загрузка кампаний" })).toBeInTheDocument()
    expect(screen.queryByText("Кампании не найдены.")).not.toBeInTheDocument()
    resolve(campaigns)
    expect(await screen.findByText("Alpha")).toBeInTheDocument()
    expect(screen.queryByRole("status")).not.toBeInTheDocument()
  })

  it("shows an empty state for an empty response", async () => {
    vi.mocked(campaignsApi.list).mockResolvedValue([])
    renderWithProviders(<CampaignsListPage />, "/campaigns")
    expect(await screen.findByText("Кампании не найдены.")).toBeInTheDocument()
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })

  it("shows an empty state for unmatched names", async () => {
    const user = userEvent.setup()
    renderWithProviders(<CampaignsListPage />, "/campaigns")
    await screen.findByText("Alpha")
    await user.type(screen.getByRole("textbox", { name: "Поиск кампаний" }), "missing")
    expect(screen.getByText("Кампании не найдены.")).toBeInTheDocument()
    expect(screen.queryByText("Alpha")).not.toBeInTheDocument()
    expect(screen.queryByText("Beta")).not.toBeInTheDocument()
  })

  it("shows the shared API error message instead of an empty state", async () => {
    vi.mocked(campaignsApi.list).mockRejectedValue(new ApiError(503, "Unavailable", { message: "Keitaro временно недоступен" }))
    renderWithProviders(<CampaignsListPage />, "/campaigns")
    expect(await screen.findByRole("alert")).toHaveTextContent("Keitaro временно недоступен")
    expect(screen.getByRole("alert")).toHaveTextContent("Не удалось загрузить кампании")
    expect(screen.queryByText("Кампании не найдены.")).not.toBeInTheDocument()
    expect(screen.queryByRole("status")).not.toBeInTheDocument()
  })
})

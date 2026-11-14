import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, fireEvent, render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createMemoryRouter, Link, RouterProvider } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { campaignsApi, type OfferRotation } from "@/shared/api"

import { CampaignEditPage } from "./campaign-edit-page"

const rotation: OfferRotation = {
  campaign_id: 42,
  flows: [{ stream_id: 10, name: "Main", offers: [
    { offer_id: 1, name: "One", share: 70, state: "active", locked: false },
    { offer_id: 2, name: "Two", share: 30, state: "active", locked: true },
    { offer_id: 3, name: "Old", share: 0, state: "deleted", locked: false },
  ] }],
}

function renderEditor(path = "/campaigns/42/edit") {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  const router = createMemoryRouter([{
    path: "/campaigns/:campaignId/edit",
    element: <><Link to="/campaigns/43/edit">Next</Link><CampaignEditPage /></>,
  }], { initialEntries: [path] })
  return render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>)
}

describe("CampaignEditPage", () => {
  beforeEach(() => { vi.spyOn(campaignsApi, "refreshOffers").mockResolvedValue(rotation) })

  it("loads manually, renders shares and states, and does not refresh on focus", async () => {
    renderEditor()
    expect(screen.getByText("Потоки не загружены")).toBeInTheDocument()
    expect(campaignsApi.refreshOffers).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    expect(await screen.findByText("Main")).toBeInTheDocument()
    for (const [name, share, state] of [["One", "70%", "активен"], ["Two", "30%", "зафиксирован"], ["Old", "0%", "удалён"]]) {
      const row = within(screen.getByText(name).closest("tr")!)
      expect(row.getByText(share)).toBeInTheDocument()
      expect(row.getByText(state)).toBeInTheDocument()
      for (const button of row.getAllByRole("button")) expect(button).toBeDisabled()
    }
    fireEvent.focus(window)
    fireEvent.online(window)
    expect(campaignsApi.refreshOffers).toHaveBeenCalledExactlyOnceWith(42)
  })

  it("disables loading and retains the previous rotation when refresh fails", async () => {
    renderEditor()
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    await screen.findByText("Main")
    let reject!: (error: Error) => void
    vi.mocked(campaignsApi.refreshOffers).mockImplementationOnce(() => new Promise((_, fail) => { reject = fail }))
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    expect(screen.getByRole("button", { name: "Получить потоки" })).toBeDisabled()
    await act(async () => { reject(new Error("offline")) })
    expect(await screen.findByText("Не удалось получить потоки")).toBeInTheDocument()
    expect(screen.getByText("Main")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Получить потоки" })).toBeEnabled()
  })

  it("clears loaded data on route change and ignores an old in-flight response", async () => {
    renderEditor()
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    await screen.findByText("Main")
    let resolve!: (value: OfferRotation) => void
    vi.mocked(campaignsApi.refreshOffers).mockImplementationOnce(() => new Promise(done => { resolve = done }))
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    await userEvent.click(screen.getByRole("link", { name: "Next" }))
    expect(screen.queryByText("Main")).not.toBeInTheDocument()
    expect(screen.getByText("Потоки не загружены")).toBeInTheDocument()
    await act(async () => { resolve(rotation) })
    expect(screen.queryByText("Main")).not.toBeInTheDocument()
    expect(campaignsApi.refreshOffers).toHaveBeenCalledTimes(2)
    vi.mocked(campaignsApi.refreshOffers).mockResolvedValueOnce({ campaign_id: 43, flows: [] })
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    expect(await screen.findByText("Потоков нет")).toBeInTheDocument()
    expect(campaignsApi.refreshOffers).toHaveBeenLastCalledWith(43)
  })

  it.each(["abc", "0", "-1", "1.5", "9007199254740992"])("rejects invalid campaign ID %s", (id) => {
    renderEditor(`/campaigns/${id}/edit`)
    expect(screen.getByText("Некорректный ID кампании")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Получить потоки" })).not.toBeInTheDocument()
    expect(campaignsApi.refreshOffers).not.toHaveBeenCalled()
  })
})

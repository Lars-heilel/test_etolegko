import { onlineManager, QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, fireEvent, render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createMemoryRouter, Link, RouterProvider } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError, campaignsApi, type OfferRotation } from "@/shared/api"

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
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const router = createMemoryRouter([{
    path: "/campaigns/:campaignId/edit",
    element: <><Link to="/campaigns/43/edit">Next</Link><CampaignEditPage /></>,
  }], { initialEntries: [path] })
  return render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>)
}

describe("CampaignEditPage", () => {
  beforeEach(() => { vi.spyOn(campaignsApi, "refreshOffers").mockResolvedValue(rotation) })

  it("filters the per-flow picker locally, excludes deleted offers, and applies the add response", async () => {
    vi.spyOn(campaignsApi, "offers").mockResolvedValue([
      { id: 1, name: "One" }, { id: 3, name: "Old" }, { id: 9, name: "Nine" },
    ])
    vi.spyOn(campaignsApi, "saveOffers")
    vi.spyOn(campaignsApi, "addOffer").mockResolvedValue({ ...rotation, flows: [{
      stream_id: 20, name: "Second", offers: [{ offer_id: 9, name: "Backend Nine", share: 0, state: "active", locked: false }],
    }] })
    vi.mocked(campaignsApi.refreshOffers).mockResolvedValue({ ...rotation, flows: [...rotation.flows, { stream_id: 20, name: "Second", offers: [rotation.flows[0].offers[2]] }] })
    renderEditor()
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    await screen.findByText("Second")
    await userEvent.click(screen.getAllByRole("button", { name: "Добавить оффер" })[0])
    const mainPicker = within(screen.getByRole("dialog"))
    await mainPicker.findByRole("button", { name: "Nine" })
    expect(mainPicker.queryByRole("button", { name: "One" })).not.toBeInTheDocument()
    expect(mainPicker.queryByRole("button", { name: "Old" })).not.toBeInTheDocument()
    await userEvent.keyboard("{Escape}")
    await userEvent.click(screen.getAllByRole("button", { name: "Добавить оффер" })[1])
    const dialog = within(screen.getByRole("dialog", { name: "Добавить оффер в «Second»" }))
    expect(await dialog.findByRole("button", { name: "One" })).toBeInTheDocument()
    expect(dialog.queryByRole("button", { name: "Old" })).not.toBeInTheDocument()
    await userEvent.type(dialog.getByRole("textbox", { name: "Поиск оффера" }), " NIN ")
    expect(dialog.queryByRole("button", { name: "One" })).not.toBeInTheDocument()
    await userEvent.click(dialog.getByRole("button", { name: "Nine" }))
    expect(await screen.findByText("Backend Nine")).toBeInTheDocument()
    expect(screen.getByText("0%")).toBeInTheDocument()
    expect(screen.getByText("активен")).toBeInTheDocument()
    expect(screen.queryByText("Main")).not.toBeInTheDocument()
    expect(campaignsApi.addOffer).toHaveBeenCalledWith(42, 20, 9)
    expect(campaignsApi.offers).toHaveBeenCalledTimes(2)
    expect(campaignsApi.saveOffers).not.toHaveBeenCalled()
  })

  it("deletes the last active offer, restores, toggles lock, and saves authoritative results", async () => {
    const single = (state: "active" | "deleted", locked = false, name = "Solo"): OfferRotation => ({ campaign_id: 42, flows: [{ stream_id: 10, name: "Main", offers: [{ offer_id: 1, name, share: 0, state, locked }] }] })
    vi.mocked(campaignsApi.refreshOffers).mockResolvedValue(single("active"))
    vi.spyOn(campaignsApi, "deleteOffer").mockResolvedValue(single("deleted"))
    vi.spyOn(campaignsApi, "restoreOffer").mockResolvedValue(single("active"))
    vi.spyOn(campaignsApi, "lockOffer").mockResolvedValueOnce(single("active", true)).mockResolvedValueOnce(single("active"))
    vi.spyOn(campaignsApi, "saveOffers").mockResolvedValue(single("active", false, "Saved"))
    renderEditor()
    expect(screen.getByRole("button", { name: "Сохранить" })).toBeDisabled()
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    await userEvent.click(await screen.findByRole("button", { name: "Удалить" }))
    expect(await screen.findByText("удалён")).toBeInTheDocument()
    expect(campaignsApi.deleteOffer).toHaveBeenCalledWith(42, 10, 1)
    await userEvent.click(screen.getByRole("button", { name: "Вернуть" }))
    await userEvent.click(await screen.findByRole("button", { name: "Зафиксировать процент" }))
    await userEvent.click(await screen.findByRole("button", { name: "Снять фиксацию" }))
    expect(await screen.findByText("активен")).toBeInTheDocument()
    expect(campaignsApi.restoreOffer).toHaveBeenCalledWith(42, 10, 1)
    expect(campaignsApi.lockOffer).toHaveBeenNthCalledWith(1, 42, 10, 1, true)
    expect(campaignsApi.lockOffer).toHaveBeenNthCalledWith(2, 42, 10, 1, false)
    expect(campaignsApi.saveOffers).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }))
    expect(await screen.findByText("Saved")).toBeInTheDocument()
    expect(campaignsApi.saveOffers).toHaveBeenCalledWith(42)
  })

  it.each([
    ["deleteOffer", "Удалить"], ["restoreOffer", "Вернуть"],
    ["lockOffer", "Зафиксировать процент"], ["saveOffers", "Сохранить"],
  ] as const)("retains rotation and blocks conflicting actions while %s fails", async (method, label) => {
    let reject!: (error: Error) => void
    vi.spyOn(campaignsApi, method).mockImplementation(() => new Promise<OfferRotation>((_, fail) => { reject = fail }))
    renderEditor()
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    await screen.findByText("Main")
    await userEvent.click(screen.getAllByRole("button", { name: label })[0])
    for (const button of screen.getAllByRole("button")) expect(button).toBeDisabled()
    await act(async () => { reject(new ApiError(409, "Conflict", { message: "operation failed" })) })
    expect(await screen.findByText("operation failed")).toBeInTheDocument()
    expect(screen.getByText("70%")).toBeInTheDocument()
    expect(screen.getByText("Old")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Сохранить" })).toBeEnabled()
  })

  it("keeps picker search and shows add failures inside the dialog", async () => {
    vi.spyOn(campaignsApi, "offers").mockResolvedValue([{ id: 9, name: "Nine" }])
    let reject!: (error: Error) => void
    vi.spyOn(campaignsApi, "addOffer").mockImplementation(() => new Promise((_, fail) => { reject = fail }))
    renderEditor()
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    await userEvent.click(await screen.findByRole("button", { name: "Добавить оффер" }))
    const dialog = within(screen.getByRole("dialog"))
    await userEvent.type(dialog.getByRole("textbox", { name: "Поиск оффера" }), "Nine")
    await userEvent.click(await dialog.findByRole("button", { name: "Nine" }))
    expect(dialog.getByRole("button", { name: "Nine" })).toBeDisabled()
    await userEvent.keyboard("{Escape}")
    expect(screen.getByRole("dialog")).toBeInTheDocument()
    await act(async () => { reject(new ApiError(409, "Conflict", { message: "add failed" })) })
    expect(await dialog.findByText("add failed")).toBeInTheDocument()
    expect(dialog.getByRole("textbox")).toHaveValue("Nine")
    expect(dialog.getByRole("button", { name: "Nine" })).toBeEnabled()
  })

  it("shows catalog failure with a retry and empty search feedback", async () => {
    vi.spyOn(campaignsApi, "offers").mockRejectedValueOnce(new ApiError(503, "Unavailable", { message: "catalog failed" })).mockResolvedValueOnce([])
    renderEditor()
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    await userEvent.click(await screen.findByRole("button", { name: "Добавить оффер" }))
    expect(await screen.findByText("catalog failed")).toBeInTheDocument()
    await userEvent.click(screen.getByRole("button", { name: "Повторить" }))
    expect(await screen.findByText("Подходящих офферов нет.")).toBeInTheDocument()
  })

  it("keeps a catalog failure on reconnect until the user retries", async () => {
    vi.spyOn(campaignsApi, "offers").mockRejectedValueOnce(new ApiError(503, "Unavailable", { message: "catalog offline" })).mockResolvedValueOnce([{ id: 9, name: "Nine" }])
    renderEditor()
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    await userEvent.click(await screen.findByRole("button", { name: "Добавить оффер" }))
    await screen.findByText("catalog offline")
    await act(async () => {
      onlineManager.setOnline(false)
      onlineManager.setOnline(true)
      await new Promise(resolve => setTimeout(resolve, 20))
    })
    expect(screen.getByText("catalog offline")).toBeInTheDocument()
    expect(campaignsApi.offers).toHaveBeenCalledTimes(1)
    await userEvent.click(screen.getByRole("button", { name: "Повторить" }))
    expect(await screen.findByRole("button", { name: "Nine" })).toBeInTheDocument()
  })

  it("clears an earlier mutation error when another operation starts and shows its own failure", async () => {
    vi.spyOn(campaignsApi, "deleteOffer").mockRejectedValue(new ApiError(409, "Conflict", { message: "delete failed" }))
    let reject!: (error: Error) => void
    vi.spyOn(campaignsApi, "saveOffers").mockImplementation(() => new Promise<OfferRotation>((_, fail) => { reject = fail }))
    renderEditor()
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    await screen.findByText("Main")
    await userEvent.click(screen.getAllByRole("button", { name: "Удалить" })[0])
    await screen.findByText("delete failed")
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }))
    expect(screen.queryByText("delete failed")).not.toBeInTheDocument()
    expect(screen.getByText("70%")).toBeInTheDocument()
    await act(async () => { reject(new ApiError(503, "Unavailable", { message: "save failed" })) })
    expect(await screen.findByText("save failed")).toBeInTheDocument()
    expect(screen.getByText("70%")).toBeInTheDocument()
  })

  it("clears a previous add failure when reopening the picker", async () => {
    vi.spyOn(campaignsApi, "offers").mockResolvedValue([{ id: 9, name: "Nine" }])
    vi.spyOn(campaignsApi, "addOffer").mockRejectedValue(new ApiError(409, "Conflict", { message: "previous add failed" }))
    renderEditor()
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    await userEvent.click(await screen.findByRole("button", { name: "Добавить оффер" }))
    await userEvent.click(await screen.findByRole("button", { name: "Nine" }))
    await within(screen.getByRole("dialog")).findByText("previous add failed")
    await userEvent.keyboard("{Escape}")
    expect(screen.getByText("previous add failed")).toBeInTheDocument()
    await userEvent.click(screen.getByRole("button", { name: "Добавить оффер" }))
    expect(screen.queryByText("previous add failed")).not.toBeInTheDocument()
    expect(await screen.findByRole("button", { name: "Nine" })).toBeEnabled()
  })

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
      for (const button of row.getAllByRole("button")) expect(button).toBeEnabled()
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

  it("isolates a pending mutation from the next campaign", async () => {
    let resolve!: (value: OfferRotation) => void
    vi.spyOn(campaignsApi, "deleteOffer").mockImplementation(() => new Promise(done => { resolve = done }))
    renderEditor()
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    await screen.findByText("Main")
    await userEvent.click(screen.getAllByRole("button", { name: "Удалить" })[0])
    await userEvent.click(screen.getByRole("link", { name: "Next" }))
    vi.mocked(campaignsApi.refreshOffers).mockResolvedValueOnce({ campaign_id: 43, flows: [] })
    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
    await screen.findByText("Потоков нет")
    await act(async () => { resolve(rotation) })
    expect(screen.queryByText("Main")).not.toBeInTheDocument()
    expect(screen.getByText("Потоков нет")).toBeInTheDocument()
  })

  it.each(["abc", "0", "-1", "1.5", "9007199254740992"])("rejects invalid campaign ID %s", (id) => {
    renderEditor(`/campaigns/${id}/edit`)
    expect(screen.getByText("Некорректный ID кампании")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Получить потоки" })).not.toBeInTheDocument()
    expect(campaignsApi.refreshOffers).not.toHaveBeenCalled()
  })
})

import type { ReactElement } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, useLocation } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError, campaignsApi } from "@/shared/api"

import { CampaignCreatePage } from "./campaign-create-page"

function renderWithProviders(ui: ReactElement, path = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter></QueryClientProvider>)
}

function Page() {
  return <><CampaignCreatePage /><output aria-label="location">{useLocation().pathname}</output></>
}

async function fill() {
  await userEvent.type(screen.getByLabelText("Название кампании"), "  MX Campaign  ")
  await userEvent.selectOptions(screen.getByLabelText("Гео"), "MX")
  await userEvent.selectOptions(screen.getByLabelText("Группа"), "2")
  await userEvent.selectOptions(screen.getByLabelText("Источник (необязательно)"), "3")
  await userEvent.type(screen.getByRole("combobox", { name: "Оффер" }), "Seven")
  expect(screen.queryByRole("option", { name: "Other" })).not.toBeInTheDocument()
  await userEvent.click(await screen.findByRole("option", { name: "Offer Seven" }))
}

describe("CampaignCreatePage", () => {
  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", class { observe() {} unobserve() {} disconnect() {} })
    HTMLElement.prototype.scrollIntoView = vi.fn()
    vi.spyOn(campaignsApi, "formOptions").mockResolvedValue({ domains: [{ id: 1, name: "example.com" }], groups: [{ id: 2, name: "Group" }], traffic_sources: [{ id: 3, name: "Source" }] })
    vi.spyOn(campaignsApi, "offers").mockResolvedValue([{ id: 7, name: "Offer Seven" }, { id: 8, name: "Other" }])
    vi.spyOn(campaignsApi, "create").mockResolvedValue({ id: 42, name: "MX Campaign", state: "active", alias: "mx" })
  })

  it("submits trimmed name and existing catalog IDs then navigates to edit", async () => {
    renderWithProviders(<Page />, "/campaigns/new")
    await fill()
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    await waitFor(() => expect(campaignsApi.create).toHaveBeenCalledWith({ name: "MX Campaign", country_code: "MX", offer_id: 7, group_id: 2, traffic_source_id: 3 }))
    expect(campaignsApi.formOptions).toHaveBeenCalled()
    expect(await screen.findByText("/campaigns/42/edit")).toBeInTheDocument()
  })

  it("validates all required fields including whitespace name", async () => {
    renderWithProviders(<Page />)
    await waitFor(() => expect(screen.getByRole("button", { name: "Создать" })).toBeEnabled())
    await userEvent.type(screen.getByLabelText("Название кампании"), "   ")
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    for (const text of ["Укажите название", "Выберите страну", "Выберите оффер", "Выберите группу"]) expect(await screen.findByText(text)).toBeInTheDocument()
    expect(campaignsApi.create).not.toHaveBeenCalled()
  })

  it("creates without a domain when the domain catalog is empty", async () => {
    vi.mocked(campaignsApi.formOptions).mockResolvedValue({ domains: [], groups: [{ id: 2, name: "Group" }], traffic_sources: [{ id: 3, name: "Source" }] })
    renderWithProviders(<Page />)
    await fill()
    expect(screen.getByText(/Нет доступных доменов/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    await waitFor(() => expect(campaignsApi.create).toHaveBeenCalledTimes(1))
    expect(vi.mocked(campaignsApi.create).mock.calls[0][0].domain_id).toBeUndefined()
  })

  it("sends the selected domain", async () => {
    renderWithProviders(<Page />)
    await fill()
    await userEvent.selectOptions(screen.getByLabelText("Домен (необязательно)"), "1")
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    await waitFor(() => expect(campaignsApi.create).toHaveBeenCalledWith(expect.objectContaining({ domain_id: 1 })))
  })

  it("explains the domain exception visibly", async () => {
    renderWithProviders(<Page />)
    expect(await screen.findByText("Почему домен необязателен?")).toBeInTheDocument()
    expect(screen.getByText(/выданным API-ключом.*403/)).toBeInTheDocument()
  })

  it("creates and selects a source from an empty catalog without creating a campaign", async () => {
    vi.mocked(campaignsApi.formOptions).mockResolvedValue({ domains: [], groups: [{ id: 2, name: "Group" }], traffic_sources: [] })
    const request = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 15, name: "New source" }), { status: 201 }))
    vi.stubGlobal("fetch", request)
    renderWithProviders(<Page />)
    await waitFor(() => expect(screen.getByRole("button", { name: "Создать" })).toBeEnabled())
    await userEvent.click(screen.getByRole("button", { name: "Создать источник" }))
    await userEvent.type(screen.getByLabelText("Название источника"), "  New source  ")
    await userEvent.click(screen.getByRole("button", { name: "Сохранить источник" }))
    await waitFor(() => expect(screen.getByLabelText("Источник (необязательно)")).toHaveValue("15"))
    expect(request).toHaveBeenCalledTimes(1)
    expect(request).toHaveBeenCalledWith(expect.stringContaining("/traffic-sources"), expect.objectContaining({ method: "POST", body: JSON.stringify({ name: "New source" }) }))
    expect(campaignsApi.create).not.toHaveBeenCalled()
    await userEvent.type(screen.getByLabelText("Название кампании"), "Campaign")
    await userEvent.selectOptions(screen.getByLabelText("Гео"), "MX")
    await userEvent.selectOptions(screen.getByLabelText("Группа"), "2")
    await userEvent.type(screen.getByRole("combobox", { name: "Оффер" }), "Seven")
    await userEvent.click(await screen.findByRole("option", { name: "Offer Seven" }))
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    await waitFor(() => expect(campaignsApi.create).toHaveBeenCalledWith(expect.objectContaining({ traffic_source_id: 15 })))
  })

  it("keeps a source error visible and never selects a failed creation", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: "Нет прав на создание источника" }), { status: 502 })))
    renderWithProviders(<Page />)
    await waitFor(() => expect(screen.getByRole("button", { name: "Создать" })).toBeEnabled())
    await userEvent.click(screen.getByRole("button", { name: "Создать источник" }))
    expect(screen.getByRole("button", { name: "Сохранить источник" })).toBeDisabled()
    await userEvent.type(screen.getByLabelText("Название источника"), "New source")
    await userEvent.click(screen.getByRole("button", { name: "Сохранить источник" }))
    expect(await screen.findByText("Нет прав на создание источника")).toBeInTheDocument()
    expect(screen.getByLabelText("Название источника")).toHaveValue("New source")
    expect(screen.getByLabelText("Источник (необязательно)")).not.toHaveValue("15")
    expect(campaignsApi.create).not.toHaveBeenCalled()
  })

  it("prevents duplicate source requests and campaign submission while creating a source", async () => {
    const request = vi.fn().mockImplementation(() => new Promise(() => {}))
    vi.stubGlobal("fetch", request)
    renderWithProviders(<Page />)
    await waitFor(() => expect(screen.getByRole("button", { name: "Создать" })).toBeEnabled())
    await userEvent.click(screen.getByRole("button", { name: "Создать источник" }))
    await userEvent.type(screen.getByLabelText("Название источника"), "New source")
    await userEvent.dblClick(screen.getByRole("button", { name: "Сохранить источник" }))
    expect(request).toHaveBeenCalledTimes(1)
    expect(screen.getByRole("button", { name: "Создание источника…" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Создать" })).toBeDisabled()
  })

  it("blocks an empty group catalog", async () => {
    vi.mocked(campaignsApi.formOptions).mockResolvedValue({ domains: [], groups: [], traffic_sources: [{ id: 3, name: "Source" }] })
    renderWithProviders(<Page />)
    expect(await screen.findByText(/Нет доступных: /)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Создать" })).toBeDisabled()
  })

  it("allows offer search and selection even when sources are empty", async () => {
    vi.mocked(campaignsApi.formOptions).mockResolvedValue({ domains: [], groups: [{ id: 2, name: "Group" }], traffic_sources: [] })
    renderWithProviders(<Page />)
    await waitFor(() => expect(screen.getByRole("button", { name: "Создать" })).toBeEnabled())
    const search = screen.getByRole("combobox", { name: "Оффер" })
    expect(search).toBeEnabled()
    await userEvent.type(search, "Seven")
    expect(await screen.findByRole("option", { name: "Offer Seven" })).toBeInTheDocument()
    expect(screen.queryByRole("option", { name: "Other" })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole("option", { name: "Offer Seven" }))
    expect(search).toHaveValue("Offer Seven")
    expect(screen.getByText("Почему источник необязателен?")).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText("Название кампании"), "Without source")
    await userEvent.selectOptions(screen.getByLabelText("Гео"), "MX")
    await userEvent.selectOptions(screen.getByLabelText("Группа"), "2")
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    await waitFor(() => expect(campaignsApi.create).toHaveBeenCalledTimes(1))
    expect(vi.mocked(campaignsApi.create).mock.calls[0][0].traffic_source_id).toBeUndefined()
  })

  it("blocks submission while catalogs load or fail", async () => {
    vi.mocked(campaignsApi.offers).mockRejectedValue(new ApiError(503, "Unavailable", { message: "Catalog unavailable" }))
    renderWithProviders(<Page />)
    expect(screen.getByRole("button", { name: "Создать" })).toBeDisabled()
    expect(await screen.findByText("Catalog unavailable")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Создать" })).toBeDisabled()
  })

  it("retries failed form options and enables submission after recovery", async () => {
    vi.mocked(campaignsApi.formOptions).mockRejectedValueOnce(new Error("Options unavailable"))
    renderWithProviders(<Page />)
    await screen.findByText("Не удалось загрузить каталоги")
    expect(screen.getByRole("button", { name: "Создать" })).toBeDisabled()
    await userEvent.click(screen.getByRole("button", { name: "Повторить загрузку" }))
    await fill()
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    await waitFor(() => expect(campaignsApi.create).toHaveBeenCalledTimes(1))
  })

  it("rejects a selected source removed by catalog refresh", async () => {
    renderWithProviders(<Page />)
    await fill()
    vi.mocked(campaignsApi.formOptions).mockResolvedValue({ domains: [], groups: [{ id: 2, name: "Group" }], traffic_sources: [{ id: 4, name: "Replacement" }] })
    await userEvent.click(screen.getByRole("button", { name: "Обновить каталоги" }))
    await screen.findByRole("option", { name: "Replacement" })
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    expect(await screen.findByText("Выберите источник из каталога")).toBeInTheDocument()
    expect(campaignsApi.create).not.toHaveBeenCalled()
  })

  it("prevents duplicate pending submits", async () => {
    vi.mocked(campaignsApi.create).mockImplementation(() => new Promise(() => {}))
    renderWithProviders(<Page />)
    await fill()
    await userEvent.dblClick(screen.getByRole("button", { name: "Создать" }))
    expect(screen.getByRole("button", { name: "Создание…" })).toBeDisabled()
    expect(campaignsApi.create).toHaveBeenCalledTimes(1)
  })

  it("requires a new selection after editing the offer search", async () => {
    renderWithProviders(<Page />)
    await fill()
    await userEvent.clear(screen.getByRole("combobox", { name: "Оффер" }))
    await userEvent.type(screen.getByRole("combobox", { name: "Оффер" }), "unknown")
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    expect(await screen.findByText("Выберите оффер")).toBeInTheDocument()
    expect(campaignsApi.create).not.toHaveBeenCalled()
  })

  it.each([
    [42, "Campaign 42 was created, but setup could not be completed. Check its flows in Keitaro before creating again."],
    [null, "Campaign creation could not be confirmed. Check Keitaro before creating again."],
  ])("preserves creation outcome message for campaign %s", async (id, message) => {
    vi.mocked(campaignsApi.create).mockRejectedValue(new ApiError(502, "Bad Gateway", { code: "KEITARO_UNAVAILABLE", campaign_id: id, failed_step: id ? "offer_flow" : "campaign", confirmed_flows: id ? 1 : 0, message }))
    renderWithProviders(<Page />, "/campaigns/new")
    await fill()
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    expect(await screen.findByText(message)).toBeInTheDocument()
    expect(screen.getByLabelText("location")).toHaveTextContent("/campaigns/new")
    expect(screen.queryByText("Не удалось создать кампанию")).not.toBeInTheDocument()
  })
})

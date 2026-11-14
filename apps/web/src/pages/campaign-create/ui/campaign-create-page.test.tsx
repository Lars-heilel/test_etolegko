import type { ReactElement } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
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
  for (const [label, id] of [["Оффер", "7"], ["Домен", "1"], ["Группа", "2"], ["Источник", "3"]]) {
    await userEvent.selectOptions(await screen.findByLabelText(label), id)
  }
}

describe("CampaignCreatePage", () => {
  beforeEach(() => {
    vi.spyOn(campaignsApi, "formOptions").mockResolvedValue({ domains: [{ id: 1, name: "example.com" }], groups: [{ id: 2, name: "Group" }], traffic_sources: [{ id: 3, name: "Source" }] })
    vi.spyOn(campaignsApi, "offers").mockResolvedValue([{ id: 7, name: "Offer Seven" }, { id: 8, name: "Other" }])
    vi.spyOn(campaignsApi, "create").mockResolvedValue({ id: 42, name: "MX Campaign", state: "active", alias: "mx" })
  })

  it("submits trimmed name and existing catalog IDs then navigates to edit", async () => {
    renderWithProviders(<Page />, "/campaigns/new")
    await fill()
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    await waitFor(() => expect(campaignsApi.create).toHaveBeenCalledWith({ name: "MX Campaign", country_code: "MX", offer_id: 7, domain_id: 1, group_id: 2, traffic_source_id: 3 }))
    expect(await screen.findByText("/campaigns/42/edit")).toBeInTheDocument()
  })

  it("validates all required fields including whitespace name", async () => {
    renderWithProviders(<Page />)
    await screen.findByRole("option", { name: "example.com" })
    await userEvent.type(screen.getByLabelText("Название кампании"), "   ")
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    for (const text of ["Укажите название", "Выберите страну", "Выберите оффер", "Выберите домен", "Выберите группу", "Выберите источник"]) expect(await screen.findByText(text)).toBeInTheDocument()
    expect(campaignsApi.create).not.toHaveBeenCalled()
  })

  it("explains missing domains and sources and prevents submit", async () => {
    vi.mocked(campaignsApi.formOptions).mockResolvedValue({ domains: [], groups: [{ id: 2, name: "Group" }], traffic_sources: [] })
    renderWithProviders(<Page />)
    expect(await screen.findByText(/Нет доменов в каталоге Keitaro/)).toBeInTheDocument()
    expect(screen.getByText(/Нет источников в каталоге Keitaro/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Создать" })).toBeDisabled()
    expect(campaignsApi.create).not.toHaveBeenCalled()
  })

  it("blocks submission while catalogs load or fail", async () => {
    vi.mocked(campaignsApi.offers).mockRejectedValue(new ApiError(503, "Unavailable", { message: "Catalog unavailable" }))
    renderWithProviders(<Page />)
    expect(screen.getByRole("button", { name: "Создать" })).toBeDisabled()
    expect(await screen.findByText("Catalog unavailable")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Создать" })).toBeDisabled()
  })

  it("keeps the selected offer when searching and prevents duplicate pending submits", async () => {
    vi.mocked(campaignsApi.create).mockImplementation(() => new Promise(() => {}))
    renderWithProviders(<Page />)
    await fill()
    await userEvent.type(screen.getByLabelText("Поиск оффера"), "other")
    expect(screen.getByLabelText("Оффер")).toHaveValue("7")
    await userEvent.dblClick(screen.getByRole("button", { name: "Создать" }))
    expect(screen.getByRole("button", { name: "Создание…" })).toBeDisabled()
    expect(campaignsApi.create).toHaveBeenCalledTimes(1)
  })

  it("rejects IDs outside the loaded catalog", async () => {
    renderWithProviders(<Page />)
    await fill()
    const select = screen.getByLabelText("Домен")
    const option = document.createElement("option")
    option.value = "999"
    select.append(option)
    fireEvent.change(select, { target: { value: "999" } })
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    expect(await screen.findByText("Выберите домен из каталога")).toBeInTheDocument()
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

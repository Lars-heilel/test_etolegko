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
    await waitFor(() => expect(campaignsApi.create).toHaveBeenCalledWith({ name: "MX Campaign", country_code: "MX", offer_id: 7 }))
    expect(campaignsApi.formOptions).not.toHaveBeenCalled()
    expect(await screen.findByText("/campaigns/42/edit")).toBeInTheDocument()
  })

  it("validates all required fields including whitespace name", async () => {
    renderWithProviders(<Page />)
    await waitFor(() => expect(screen.getByRole("button", { name: "Создать" })).toBeEnabled())
    await userEvent.type(screen.getByLabelText("Название кампании"), "   ")
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    for (const text of ["Укажите название", "Выберите страну", "Выберите оффер"]) expect(await screen.findByText(text)).toBeInTheDocument()
    expect(campaignsApi.create).not.toHaveBeenCalled()
  })

  it("creates with only offers available and never requests form options", async () => {
    vi.mocked(campaignsApi.formOptions).mockResolvedValue({ domains: [], groups: [{ id: 2, name: "Group" }], traffic_sources: [] })
    renderWithProviders(<Page />)
    await fill()
    for (const label of ["Домен", "Группа", "Источник"]) expect(screen.queryByLabelText(label)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))
    await waitFor(() => expect(campaignsApi.create).toHaveBeenCalledTimes(1))
    expect(campaignsApi.formOptions).not.toHaveBeenCalled()
  })

  it("blocks submission while catalogs load or fail", async () => {
    vi.mocked(campaignsApi.offers).mockRejectedValue(new ApiError(503, "Unavailable", { message: "Catalog unavailable" }))
    renderWithProviders(<Page />)
    expect(screen.getByRole("button", { name: "Создать" })).toBeDisabled()
    expect(await screen.findByText("Catalog unavailable")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Создать" })).toBeDisabled()
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

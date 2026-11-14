import type { ReactElement } from "react"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import { createMemoryRouter, RouterProvider } from "react-router-dom"

export function renderWithProviders(ui: ReactElement, path = "/") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const router = createMemoryRouter(
    [
      { path: "/campaigns", element: ui },
      { path: "/campaigns/new", element: ui },
      { path: "/campaigns/:campaignId/edit", element: ui },
      { path: "*", element: ui },
    ],
    { initialEntries: [path] },
  )
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

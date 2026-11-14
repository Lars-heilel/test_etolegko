import { createBrowserRouter, Navigate } from "react-router-dom"

import { RootLayout } from "@/app/layouts/root-layout"
import { CampaignCreatePage } from "@/pages/campaign-create"
import { CampaignEditPage } from "@/pages/campaign-edit"
import { CampaignsListPage } from "@/pages/campaigns-list"
import { NotFoundPage } from "@/pages/not-found"

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { index: true, element: <Navigate replace to="/campaigns" /> },
      { path: "campaigns", element: <CampaignsListPage /> },
      { path: "campaigns/new", element: <CampaignCreatePage /> },
      { path: "campaigns/:campaignId/edit", element: <CampaignEditPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
])

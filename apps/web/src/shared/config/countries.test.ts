/// <reference types="node" />
// @vitest-environment node
import { execFileSync } from "node:child_process"
import { fileURLToPath } from "node:url"

import { describe, expect, it } from "vitest"

import { countryOptions } from "./countries"

describe("countryOptions backend contract", () => {
  it("offers exactly the assigned codes accepted by CountryCode, including territories", () => {
    // Exercise the real, stdlib-only backend validator rather than duplicating
    // its allowlist or deriving expected values from world-countries metadata.
    const result = JSON.parse(execFileSync("python3", ["-c", `
import json
import sys
from app.domain.keitaro.value_objects.country import CountryCode, ISO_ALPHA_2

rejected = []
for code in json.load(sys.stdin):
    try:
        CountryCode(code)
    except ValueError:
        rejected.append(code)
print(json.dumps({"rejected": rejected, "accepted": sorted(ISO_ALPHA_2)}))
`], {
      cwd: fileURLToPath(new URL("../../../../api/", import.meta.url)),
      input: JSON.stringify(countryOptions.map(({ code }) => code)),
      encoding: "utf8",
    })) as { rejected: string[]; accepted: string[] }

    expect(result.rejected).toEqual([])
    expect(countryOptions.map(({ code }) => code).sort()).toEqual(result.accepted)
  })
})

import countries from "world-countries"

const displayNames = new Intl.DisplayNames(["ru"], { type: "region" })

export const countryOptions: { code: string; name: string }[] = countries
  .filter((country) => country.status === "officially-assigned")
  .map((country) => ({
    code: country.cca2,
    name: displayNames.of(country.cca2) ?? country.name.common,
  }))
  .sort((left, right) => left.name.localeCompare(right.name, "ru"))

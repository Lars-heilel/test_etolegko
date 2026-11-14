import countries from "world-countries"

const displayNames = new Intl.DisplayNames(["ru"], { type: "region" })

export const countryOptions: { code: string; name: string }[] = countries
  .map((country) => ({
    code: country.cca2,
    name: displayNames.of(country.cca2) ?? country.name.common,
  }))
  .sort((left, right) => left.name.localeCompare(right.name, "ru"))

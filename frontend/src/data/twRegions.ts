import twRegionsData from "../../../backend/app/data/tw_regions.json";

interface County {
  code: string;
  name: string;
  sort: number;
}

interface District {
  code: string;
  county_code: string;
  name: string;
}

const countiesData = twRegionsData.counties as County[];
const districtsData = twRegionsData.districts as District[];

export const counties = [...countiesData].sort((left, right) => left.sort - right.sort);

const districtsByCountyCode = new Map(
  counties.map((county) => [
    county.code,
    districtsData
      .filter((district) => district.county_code === county.code)
      .sort((left, right) => left.code.localeCompare(right.code))
      .map((district) => district.name),
  ]),
);

const countyCodeByName = new Map(counties.map((county) => [county.name, county.code]));

export function getDistrictsByCountyName(countyName: string): string[] {
  const countyCode = countyCodeByName.get(countyName);
  return countyCode ? districtsByCountyCode.get(countyCode) ?? [] : [];
}

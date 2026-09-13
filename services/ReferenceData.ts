// ---------------------------------------------------------------------------
// services/ReferenceData.ts
//
// Central module for the PUBLISHED reference datasets used across the app.
// All figures below come from official, citable publications (see DATA_SOURCES)
// instead of hand-made demo values.
//
//  * Species populations  -> 20th Livestock Census (2019), DAHD, Govt. of India
//  * Districts           -> Revenue & Forest Department, Govt. of Maharashtra
//                           (36 districts, headquarters coordinates)
//  * Breeds              -> ICAR-NBAGR National Register of Indigenous Breeds
//                           (selection focused on breeds found in Maharashtra)
//  * Vaccination schedule-> DAHD / National Animal Disease Control Programme
//                           (NADCP) published guidelines
// ---------------------------------------------------------------------------

export const SPECIES = ["Cattle", "Buffalo", "Goat", "Sheep", "Poultry", "Pig"] as const;
export type Species = (typeof SPECIES)[number];

/** Population figures from the 20th Livestock Census (2019), in millions. */
export interface CensusPopulation {
  cattle: number;
  buffalo: number;
  sheep: number;
  goat: number;
  pig: number | null; // null = not published separately for that geography
  poultry: number;
  totalLivestock: number; // excludes poultry, per census definition
}

export const LIVESTOCK_CENSUS_2019: {
  source: string;
  national: CensusPopulation;
  maharashtra: CensusPopulation;
} = {
  source:
    "20th Livestock Census 2019 - Department of Animal Husbandry & Dairying, Ministry of Fisheries, Animal Husbandry & Dairying, Govt. of India",
  national: {
    cattle: 192.49,
    buffalo: 109.85,
    sheep: 74.26,
    goat: 148.88,
    pig: 9.06,
    poultry: 851.81,
    totalLivestock: 535.78,
  },
  maharashtra: {
    cattle: 13.9,
    buffalo: 5.6,
    sheep: 2.7,
    goat: 10.6,
    pig: null, // not broken out in the published state-level tables
    poultry: 74.3,
    totalLivestock: 33.0,
  },
};

/** One administrative district of Maharashtra (36 districts since 2014). */
export interface District {
  /** District name as used across the app (official, post-2023 renaming). */
  district: string;
  /** Former official name, when renamed (Aurangabad/Osmanabad/Ahmednagar). */
  formerName?: string;
  division: string;
  /** Headquarters coordinates (WGS84). */
  lat: number;
  lng: number;
}

/**
 * All 36 districts of Maharashtra with headquarters coordinates.
 * Source: Revenue & Forest Department, Govt. of Maharashtra.
 * Renamed districts keep their official current name:
 * Aurangabad -> Chhatrapati Sambhajinagar, Osmanabad -> Dharashiv,
 * Ahmednagar -> Ahilyanagar (Government resolutions, 2023).
 */
export const MAHARASHTRA_DISTRICTS: District[] = [
  // Konkan division
  { district: "Mumbai City", division: "Konkan", lat: 18.9388, lng: 72.8354 },
  { district: "Mumbai Suburban", division: "Konkan", lat: 19.0726, lng: 72.8826 },
  { district: "Thane", division: "Konkan", lat: 19.1971, lng: 72.9633 },
  { district: "Palghar", division: "Konkan", lat: 19.7002, lng: 72.7692 },
  { district: "Raigad", division: "Konkan", lat: 18.6411, lng: 72.8792 },
  { district: "Ratnagiri", division: "Konkan", lat: 16.9944, lng: 73.312 },
  { district: "Sindhudurg", division: "Konkan", lat: 15.888, lng: 73.772 },
  // Pune division
  { district: "Pune", division: "Pune", lat: 18.5204, lng: 73.8567 },
  { district: "Satara", division: "Pune", lat: 17.6805, lng: 74.0183 },
  { district: "Sangli", division: "Pune", lat: 16.8524, lng: 74.5815 },
  { district: "Solapur", division: "Pune", lat: 17.6599, lng: 75.9064 },
  { district: "Kolhapur", division: "Pune", lat: 16.705, lng: 74.2433 },
  // Nashik division
  { district: "Nashik", division: "Nashik", lat: 20.011, lng: 73.7903 },
  { district: "Dhule", division: "Nashik", lat: 20.9013, lng: 74.7749 },
  { district: "Jalgaon", division: "Nashik", lat: 21.008, lng: 75.5626 },
  { district: "Nandurbar", division: "Nashik", lat: 21.3657, lng: 74.2443 },
  { district: "Ahilyanagar", formerName: "Ahmednagar", division: "Nashik", lat: 19.0941, lng: 74.7492 },
  // Chhatrapati Sambhajinagar division
  { district: "Chhatrapati Sambhajinagar", formerName: "Aurangabad", division: "Chhatrapati Sambhajinagar", lat: 19.8762, lng: 75.3433 },
  { district: "Jalna", division: "Chhatrapati Sambhajinagar", lat: 19.8359, lng: 75.8776 },
  { district: "Parbhani", division: "Chhatrapati Sambhajinagar", lat: 19.2686, lng: 76.7704 },
  { district: "Hingoli", division: "Chhatrapati Sambhajinagar", lat: 19.72, lng: 77.15 },
  { district: "Nanded", division: "Chhatrapati Sambhajinagar", lat: 19.1383, lng: 77.321 },
  { district: "Latur", division: "Chhatrapati Sambhajinagar", lat: 18.4088, lng: 76.5604 },
  { district: "Dharashiv", formerName: "Osmanabad", division: "Chhatrapati Sambhajinagar", lat: 18.18, lng: 76.04 },
  { district: "Beed", division: "Chhatrapati Sambhajinagar", lat: 18.99, lng: 75.76 },
  // Amravati division
  { district: "Amravati", division: "Amravati", lat: 20.932, lng: 77.7523 },
  { district: "Akola", division: "Amravati", lat: 20.7102, lng: 77.0021 },
  { district: "Buldhana", division: "Amravati", lat: 20.53, lng: 76.18 },
  { district: "Washim", division: "Amravati", lat: 20.1124, lng: 77.1326 },
  { district: "Yavatmal", division: "Amravati", lat: 20.3897, lng: 78.1266 },
  // Nagpur division
  { district: "Nagpur", division: "Nagpur", lat: 21.1458, lng: 79.0882 },
  { district: "Wardha", division: "Nagpur", lat: 20.7453, lng: 78.6022 },
  { district: "Chandrapur", division: "Nagpur", lat: 19.9615, lng: 79.2961 },
  { district: "Gadchiroli", division: "Nagpur", lat: 20.1113, lng: 80.0011 },
  { district: "Gondia", division: "Nagpur", lat: 21.4607, lng: 80.2 },
  { district: "Bhandara", division: "Nagpur", lat: 21.1667, lng: 79.65 },
];

export const DISTRICT_NAMES: string[] = MAHARASHTRA_DISTRICTS.map((d) => d.district);

/**
 * Indigenous livestock breeds registered by ICAR-NBAGR that are found in
 * Maharashtra (originating in, or commonly reared in, the state).
 * Source: National Bureau of Animal Genetic Resources breed register.
 */
export const INDIGENOUS_BREEDS: Record<string, string[]> = {
  Cattle: ["Gir", "Dangi", "Deoni", "Khillari", "Kankrej", "Red Kandhari", "Tharparkar", "Malvi", "Other / Non-descript"],
  Buffalo: ["Pandharpuri", "Nagpuri (Ellichpuri)", "Surti", "Murrah", "Mehsana", "Jaffarabadi", "Other / Non-descript"],
  Goat: ["Osmanabadi", "Sangamneri", "Berari", "Beetal", "Sirohi", "Other / Non-descript"],
  Sheep: ["Deccani", "Madgyal", "Lonand", "Other / Non-descript"],
  Poultry: ["Aseel", "Kadaknath", "Local / Non-descript"],
  Pig: ["Local / Non-descript"],
};

export function getBreedsForSpecies(species: string | undefined | null): string[] {
  if (!species) return [];
  return INDIGENOUS_BREEDS[species] ?? [];
}

/** One line of the state/central vaccination programme schedule. */
export interface VaccinationRecommendation {
  disease: string;
  vaccine: string;
  species: string[];
  frequency: string;
  programme: string;
  note: string;
}

/**
 * Published vaccination schedule followed in Maharashtra / India.
 * Source: DAHD guidelines and the National Animal Disease Control Programme
 * (NADCP, launched Sept 2019: FMD eradication by 2030 with 100% six-monthly
 * vaccination of cattle, buffalo, sheep, goat and pig; one-time Brucellosis
 * vaccination of female bovine calves aged 4-8 months).
 */
export const VACCINATION_SCHEDULE: VaccinationRecommendation[] = [
  {
    disease: "Foot-and-Mouth Disease (FMD)",
    vaccine: "Trivalent FMD vaccine (serotypes O, A, Asia-1)",
    species: ["Cattle", "Buffalo", "Sheep", "Goat", "Pig"],
    frequency: "Twice a year (six-monthly campaigns)",
    programme: "NADCP / FMD Control Programme",
    note: "NADCP targets 100% vaccination of all susceptible livestock every six months, with eradication planned by 2030.",
  },
  {
    disease: "Brucellosis",
    vaccine: "S-19 (cattle) / RB51",
    species: ["Cattle", "Buffalo"],
    frequency: "Single dose at 4-8 months of age (lifetime)",
    programme: "NADCP",
    note: "Only female bovine calves are vaccinated; one dose confers life-long protection.",
  },
  {
    disease: "Peste des Petits Ruminants (PPR)",
    vaccine: "PPR live attenuated vaccine",
    species: ["Sheep", "Goat"],
    frequency: "Once a year (campaigns)",
    programme: "National PPR Eradication Programme",
    note: "India targets PPR eradication by 2030 in line with the FAO-WOAH global strategy.",
  },
  {
    disease: "Hemorrhagic Septicemia (HS)",
    vaccine: "HS alum-precipitated / oil-adjuvanted vaccine",
    species: ["Cattle", "Buffalo"],
    frequency: "Once a year, before the monsoon (April-May)",
    programme: "State Livestock Health Programme",
    note: "Cases peak during the rainy season; pre-monsoon vaccination is critical.",
  },
  {
    disease: "Blackquarter (BQ)",
    vaccine: "BQ vaccine (Clostridium chauvoei)",
    species: ["Cattle", "Sheep", "Goat"],
    frequency: "Once a year in endemic areas",
    programme: "State Livestock Health Programme",
    note: "Spore-borne soil infection; endemic pockets are vaccinated annually.",
  },
  {
    disease: "Anthrax",
    vaccine: "Live spore vaccine (Sterne strain)",
    species: ["Cattle", "Sheep", "Goat"],
    frequency: "Once a year in endemic districts",
    programme: "State Livestock Health Programme",
    note: "Zoonotic and notifiable; burial/cremation protocol applies to carcasses.",
  },
  {
    disease: "Rabies",
    vaccine: "Anti-rabies vaccine (ARV)",
    species: ["Cattle", "Buffalo", "Goat", "Sheep"],
    frequency: "Once a year for at-risk animals",
    programme: "National Action Plan for Rabies Elimination (NAPRE)",
    note: "Dog-mediated rabies elimination is targeted by 2030; livestock vaccination protects grazing animals.",
  },
  {
    disease: "Ranikhet Disease (Newcastle Disease)",
    vaccine: "F1 strain (day-old) followed by R2B / LaSota boosters",
    species: ["Poultry"],
    frequency: "Primary dose plus periodic boosters",
    programme: "Poultry Disease Control Programme",
    note: "Standard ICAR-recommended schedule for backyard and commercial flocks.",
  },
  {
    disease: "Goat Pox / Sheep Pox",
    vaccine: "Goat pox / sheep pox live vaccine",
    species: ["Goat", "Sheep"],
    frequency: "Once a year in endemic areas",
    programme: "State Livestock Health Programme",
    note: "Also used heterologously against Lumpy Skin Disease in cattle during outbreaks.",
  },
  {
    disease: "Classical Swine Fever (CSF)",
    vaccine: "Lapinised CSF vaccine",
    species: ["Pig"],
    frequency: "Once a year",
    programme: "State Livestock Health Programme",
    note: "Recommended for all pigs above the age prescribed by the state schedule.",
  },
];

export interface DataSource {
  name: string;
  publisher: string;
  url: string;
  year: string;
}

export const DATA_SOURCES: DataSource[] = [
  {
    name: "20th Livestock Census 2019 - Key Results",
    publisher: "Department of Animal Husbandry & Dairying, Govt. of India",
    url: "https://dahd.gov.in/",
    year: "2019",
  },
  {
    name: "National Animal Disease Control Programme (NADCP)",
    publisher: "Department of Animal Husbandry & Dairying, Govt. of India",
    url: "https://dahd.gov.in/",
    year: "2019-",
  },
  {
    name: "National Register of Indigenous Livestock Breeds",
    publisher: "ICAR-National Bureau of Animal Genetic Resources (NBAGR)",
    url: "https://www.nbagri.org.in/",
    year: "2013-",
  },
  {
    name: "Administrative Districts of Maharashtra (36 districts)",
    publisher: "Revenue & Forest Department, Govt. of Maharashtra",
    url: "https://maharashtra.gov.in/",
    year: "2023",
  },
  {
    name: "WOAH Listed Diseases & India's disease reporting",
    publisher: "World Organisation for Animal Health (WOAH)",
    url: "https://www.woah.org/",
    year: "2024",
  },
];

export interface FilterOptions {
  dateRange: string;
  district: string;
  species: string;
  disease: string;
}

export interface KPIData {
  label: string;
  value: number;
  changePercent: number;
  trend: "up" | "down" | "flat";
  status: "success" | "warning" | "danger" | "neutral";
}

export interface DiseaseTrend {
  date: string;
  FMD: number;
  LSD: number;
  PPR: number;
  Brucellosis: number;
}

export interface DistrictStat {
  district: string;
  totalCases: number;
  activeCases: number;
  recovered: number;
  mortality: number;
  vaccinationCoverage: number;
  riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  trend: "up" | "down" | "flat";
}

export interface AnalyticsData {
  summary: KPIData[];
  diseaseTrends: DiseaseTrend[];
  diseaseDistribution: { name: string; confirmed: number; suspected: number; recovered: number; deaths: number }[];
  districtAnalytics: DistrictStat[];
  speciesAnalytics: { species: string; affected: number; active: number; recoveryRate: number; mortality: number }[];
  outbreakAnalytics: { active: number; newDetected: number; resolved: number; avgResponseHours: number; highestDistrict: string };
  vaccinationAnalytics: { target: number; vaccinated: number; pending: number; coveragePercent: number };
  laboratoryAnalytics: { collected: number; tested: number; positive: number; negative: number; pending: number; avgTurnaroundHours: number };
  insights: string[];
}

const DISTRICTS = [
  "Pune", "Nashik", "Nagpur", "Mumbai", "Thane", 
  "Chhatrapati Sambhajinagar", "Kolhapur", "Satara", 
  "Sangli", "Solapur", "Ahilyanagar"
];

const SPECIES = ["Cattle", "Buffalo", "Goat", "Sheep", "Poultry", "Pig"];

function calculateRisk(active: number, mortality: number, coverage: number): "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" {
  const score = (active * 0.5) + (mortality * 2) - (coverage * 0.1);
  if (score > 500) return "CRITICAL";
  if (score > 200) return "HIGH";
  if (score > 50) return "MEDIUM";
  return "LOW";
}

export const AnalyticsService = {
  async getAnalytics(filters: FilterOptions): Promise<AnalyticsData> {
    // Simulate API delay
    await new Promise(r => setTimeout(r, 600));

    // Base multiplier to simulate filter changes
    let multiplier = 1;
    if (filters.dateRange === "Last 7 Days") multiplier = 0.25;
    if (filters.dateRange === "Today") multiplier = 0.05;
    if (filters.district !== "All") multiplier *= 0.15;

    const summary: KPIData[] = [
      { label: "Total Cases", value: Math.floor(1284 * multiplier), changePercent: 12.4, trend: "up", status: "danger" },
      { label: "Active Cases", value: Math.floor(452 * multiplier), changePercent: -5.2, trend: "down", status: "warning" },
      { label: "Recovered", value: Math.floor(790 * multiplier), changePercent: 18.1, trend: "up", status: "success" },
      { label: "Mortality", value: Math.floor(42 * multiplier), changePercent: 2.1, trend: "up", status: "danger" },
      { label: "Outbreaks Detected", value: Math.floor(15 * multiplier), changePercent: 0, trend: "flat", status: "warning" },
      { label: "Vaccinated Animals", value: Math.floor(45000 * multiplier), changePercent: 22.5, trend: "up", status: "success" },
      { label: "Samples Tested", value: Math.floor(3200 * multiplier), changePercent: 8.4, trend: "up", status: "neutral" },
      { label: "High-Risk Districts", value: Math.floor(3 * (multiplier > 0.5 ? 1 : 0.3)), changePercent: -1, trend: "down", status: "danger" },
    ];

    const diseaseTrends: DiseaseTrend[] = Array.from({ length: 14 }).map((_, i) => ({
      date: `Day ${i + 1}`,
      FMD: Math.floor((Math.random() * 50 + 20) * multiplier),
      LSD: Math.floor((Math.random() * 80 + 30) * multiplier),
      PPR: Math.floor((Math.random() * 40 + 10) * multiplier),
      Brucellosis: Math.floor((Math.random() * 20 + 5) * multiplier),
    }));

    const diseaseDistribution = [
      { name: "FMD", confirmed: Math.floor(450 * multiplier), suspected: Math.floor(120 * multiplier), recovered: Math.floor(300 * multiplier), deaths: Math.floor(15 * multiplier) },
      { name: "LSD", confirmed: Math.floor(620 * multiplier), suspected: Math.floor(200 * multiplier), recovered: Math.floor(400 * multiplier), deaths: Math.floor(20 * multiplier) },
      { name: "PPR", confirmed: Math.floor(180 * multiplier), suspected: Math.floor(50 * multiplier), recovered: Math.floor(120 * multiplier), deaths: Math.floor(5 * multiplier) },
      { name: "Brucellosis", confirmed: Math.floor(34 * multiplier), suspected: Math.floor(10 * multiplier), recovered: Math.floor(20 * multiplier), deaths: Math.floor(2 * multiplier) },
    ];

    const districtAnalytics: DistrictStat[] = DISTRICTS.map(district => {
      const active = Math.floor(Math.random() * 200 * multiplier);
      const mortality = Math.floor(Math.random() * 15 * multiplier);
      const cov = Math.floor(Math.random() * 40 + 40); // 40-80%
      return {
        district,
        totalCases: active + Math.floor(Math.random() * 500 * multiplier),
        activeCases: active,
        recovered: Math.floor(Math.random() * 400 * multiplier),
        mortality,
        vaccinationCoverage: cov,
        riskLevel: calculateRisk(active, mortality, cov),
        trend: Math.random() > 0.5 ? "up" : "down"
      };
    });

    const speciesAnalytics = SPECIES.map(species => {
      const affected = Math.floor(Math.random() * 1000 * multiplier);
      return {
        species,
        affected,
        active: Math.floor(affected * 0.3),
        recoveryRate: Math.floor(Math.random() * 30 + 60),
        mortality: Math.floor(affected * 0.05)
      };
    });

    const insights = [
      `FMD cases ${multiplier > 0.5 ? "increased" : "decreased"} by 18% in the selected period.`,
      `${districtAnalytics.filter(d => d.riskLevel === "CRITICAL" || d.riskLevel === "HIGH").length} districts currently show elevated outbreak activity.`,
      `Vaccination coverage is below the target threshold in ${districtAnalytics.filter(d => d.vaccinationCoverage < 60).length} districts.`,
      `Laboratory positivity rate ${Math.random() > 0.5 ? "increased" : "decreased"} compared with the previous period.`
    ];

    return {
      summary,
      diseaseTrends,
      diseaseDistribution,
      districtAnalytics,
      speciesAnalytics,
      outbreakAnalytics: {
        active: Math.floor(12 * multiplier),
        newDetected: Math.floor(3 * multiplier),
        resolved: Math.floor(8 * multiplier),
        avgResponseHours: 14.5,
        highestDistrict: "Pune"
      },
      vaccinationAnalytics: {
        target: 150000,
        vaccinated: Math.floor(45000 * multiplier),
        pending: Math.floor(105000 * multiplier),
        coveragePercent: Math.floor((45000 / 150000) * 100)
      },
      laboratoryAnalytics: {
        collected: Math.floor(3400 * multiplier),
        tested: Math.floor(3200 * multiplier),
        positive: Math.floor(850 * multiplier),
        negative: Math.floor(2350 * multiplier),
        pending: Math.floor(200 * multiplier),
        avgTurnaroundHours: 36
      },
      insights
    };
  },
  
  async generateReport(_filters: FilterOptions, type: string, format: string) {
    await new Promise(r => setTimeout(r, 1500));
    return `${type}_${format}_generated.pdf`;
  }
};

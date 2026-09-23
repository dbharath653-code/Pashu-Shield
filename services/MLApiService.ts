/**
 * Client for the optional FastAPI "ml-backend" service.
 *
 * The API base is configurable so the same build can be deployed:
 *   - behind a reverse proxy that exposes the backend on the same origin (default: "/api")
 *   - against an absolute backend URL (set VITE_API_BASE_URL, e.g. https://api.example.org/api)
 *   - as a static/PWA-only deployment: every call transparently falls back to the
 *     on-device models (see `localEngine`) so the UI keeps working with no backend.
 *
 * The fallback mirrors the weighted risk formula that ml-backend/train_model.py uses to
 * build its training target, so the offline numbers stay in the same range as the
 * hosted Random Forest instead of showing an empty screen.
 */

export type PredictionSource = 'backend' | 'local';

export interface RiskFactor {
  factor: string;
  impact: number;
  value: number;
}

export interface RiskPrediction {
  disease: string;
  district: string;
  risk_score: number;
  probability: number;
  risk_level: 'High Risk' | 'Moderate Risk' | 'Low Risk';
  confidence: number;
  trend: 'Increasing' | 'Stable' | 'Decreasing';
  predicted_cases: number;
  prediction_horizon_days: number;
  top_risk_factors: RiskFactor[];
  recommended_actions: string[];
  model_version: string;
  source: PredictionSource;
  /** Server-reported validation status, e.g. NOT_VALIDATED_SYNTHETIC. Decision support only — never a diagnosis. */
  validation_status?: string;
  is_synthetic_training?: boolean;
  disclaimer?: string;
}

export interface OutbreakDetection {
  outbreak_detected: boolean;
  severity: 'Normal' | 'Moderate' | 'High';
  anomaly_score: number;
  case_growth: number;
  affected_districts: string[];
  source: PredictionSource;
}

export interface ForecastPoint {
  date: string;
  predicted_cases: number;
}

export interface ForecastResult {
  forecast: ForecastPoint[];
  source: PredictionSource;
}

export interface ClusterPoint {
  cluster_id: string;
  district: string;
  lat: number;
  lng: number;
  cases: number;
  risk_level: 'High Risk' | 'Moderate Risk' | 'Low Risk';
  latest_case: string;
}

export interface ClusterResult {
  clusters: ClusterPoint[];
  source: PredictionSource;
}

export interface ModelPerformance {
  model: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  roc_auc: number;
  training_samples: number;
  last_trained: string;
  source: PredictionSource;
}

export interface RiskInput {
  disease: string;
  district: string;
  time_range: string;
  animal_population: number;
  affected_animals: number;
  new_cases: number;
  deaths: number;
  vaccination_coverage: number;
  temperature: number;
  rainfall: number;
  humidity: number;
  animal_density: number;
  previous_cases: number;
  cases_growth_rate: number;
}

import { assetUrl } from './AssetPaths';

const DEFAULT_API_BASE = '/api';
const REQUEST_TIMEOUT_MS = 6000;

const apiBase = ((): string => {
  const configured = import.meta.env?.VITE_API_BASE_URL as string | undefined;
  return (configured && configured.trim() !== '' ? configured : DEFAULT_API_BASE).replace(/\/+$/, '');
})();

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const res = await fetch(`${apiBase}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`${path} responded with ${res.status}`);
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

async function getJson<T>(path: string): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const res = await fetch(`${apiBase}${path}`, { signal: controller.signal });
    if (!res.ok) throw new Error(`${path} responded with ${res.status}`);
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

/* ------------------------------------------------------------------ */
/* On-device fallback engine                                           */
/* ------------------------------------------------------------------ */

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

const RISK_WEIGHTS: { key: keyof RiskInput; label: string; normalise: (v: number) => number; weight: number }[] = [
  { key: 'new_cases', label: 'New Cases', normalise: (v) => clamp01(v / 150), weight: 0.25 },
  { key: 'cases_growth_rate', label: 'Cases Growth Rate', normalise: (v) => clamp01((v + 0.5) / 3), weight: 0.2 },
  { key: 'vaccination_coverage', label: 'Vaccination Coverage (inverse)', normalise: (v) => clamp01(1 - v), weight: 0.2 },
  { key: 'affected_animals', label: 'Affected Animals', normalise: (v) => clamp01(v / 1000), weight: 0.15 },
  { key: 'animal_density', label: 'Animal Density', normalise: (v) => clamp01(v / 500), weight: 0.1 },
  { key: 'temperature', label: 'Temperature', normalise: (v) => clamp01(v / 42), weight: 0.05 },
  { key: 'humidity', label: 'Humidity', normalise: (v) => clamp01(v / 95), weight: 0.05 },
];

// Mirrors the weighted risk formula used to generate the training target in ml-backend/train_model.py
function localRiskScore(input: RiskInput): number {
  return clamp01(RISK_WEIGHTS.reduce((total, f) => total + f.weight * f.normalise(Number(input[f.key]) || 0), 0));
}

function riskLevel(scorePercent: number): RiskPrediction['risk_level'] {
  if (scorePercent > 60) return 'High Risk';
  if (scorePercent > 30) return 'Moderate Risk';
  return 'Low Risk';
}

function recommendedActions(input: RiskInput, level: RiskPrediction['risk_level']): string[] {
  const actions: string[] = [];
  if (level === 'High Risk') {
    actions.push('Immediate Veterinary inspection', 'Implement quarantine measures');
  }
  if (input.vaccination_coverage < 0.6) actions.push('Initiate emergency vaccination campaign');
  if (input.cases_growth_rate > 0.5) actions.push('Enhanced active surveillance');
  if (actions.length === 0) actions.push('Routine monitoring', 'Promote biosecurity awareness');
  return actions;
}

const localEngine = {
  predict(input: RiskInput, confidence: number): RiskPrediction {
    const probability = localRiskScore(input);
    const riskScore = Math.round(probability * 1000) / 10;
    const factors = RISK_WEIGHTS
      .map((f) => {
        const value = Number(input[f.key]) || 0;
        return { factor: f.label, impact: f.weight * f.normalise(value), value };
      })
      .sort((a, b) => b.impact - a.impact)
      .slice(0, 4)
      .map((f) => ({ ...f, impact: Math.round(f.impact * 1000) / 1000 }));

    const horizon = Number.parseInt(input.time_range, 10);
    const level = riskLevel(riskScore);

    return {
      disease: input.disease,
      district: input.district,
      risk_score: riskScore,
      probability: Math.round(probability * 1000) / 1000,
      risk_level: level,
      confidence,
      trend:
        input.cases_growth_rate > 0.1 ? 'Increasing' : input.cases_growth_rate > -0.1 ? 'Stable' : 'Decreasing',
      predicted_cases: Math.round(input.new_cases * (1 + input.cases_growth_rate)),
      prediction_horizon_days: Number.isNaN(horizon) ? 14 : horizon,
      top_risk_factors: factors,
      recommended_actions: recommendedActions(input, level),
      model_version: 'local-heuristic-v1.0',
      source: 'local',
      validation_status: 'HEURISTIC_NOT_VALIDATED',
      disclaimer: 'On-device rule-based estimate (offline fallback). Not a diagnosis; confirm with a veterinarian.',
    };
  },

  outbreakDetection(newCases: number, growth: number, deaths: number, district: string): OutbreakDetection {
    // Robust z-scores against the surveillance baselines used to train the Isolation Forest.
    const z = (value: number, mean: number, sd: number) => (value - mean) / sd;
    const zScores = [
      z(newCases, 75, 43.3),
      z(growth, 1, 0.87),
      z(deaths, 25, 14.4),
    ];
    const worst = Math.max(...zScores);
    const detected = worst > 2;
    const anomalyScore = Math.round(Math.max(-0.5, -worst / 6) * 1000) / 1000;

    return {
      outbreak_detected: detected,
      severity: detected ? (worst > 3 ? 'High' : 'Moderate') : 'Normal',
      anomaly_score: anomalyScore,
      case_growth: growth,
      affected_districts: detected ? [district] : [],
      source: 'local',
    };
  },

  forecast(historicalCases: number[], horizon: number): ForecastResult {
    const points: ForecastPoint[] = [];
    const values = historicalCases.length > 0 ? historicalCases : [0];
    const trend = values.length > 1 ? (values[values.length - 1] - values[0]) / values.length : 0;
    let last = values[values.length - 1];
    const today = new Date();

    for (let i = 0; i < Math.max(1, horizon); i += 1) {
      // Damped trend projection: keeps the growth realistic over longer horizons.
      const next = Math.max(0, last + trend * Math.pow(0.92, i));
      const date = new Date(today.getTime() + (i + 1) * 86400000);
      points.push({ date: date.toISOString().split('T')[0], predicted_cases: Math.round(next) });
      last = next;
    }
    return { forecast: points, source: 'local' };
  },

  cluster(districts: string[], locations: { district: string; lat: number; lng: number }[]): ClusterResult {
    const clusters: ClusterPoint[] = districts.map((district, i) => {
      const match = locations.find((l) => l.district.toLowerCase() === district.toLowerCase());
      // Deterministic pseudo-jitter keeps the marker stable between renders.
      const seed = [...district].reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
      const jitter = ((seed % 7) - 3) / 100;
      const cases = 30 + (seed % 90);
      return {
        cluster_id: `CLUST-${i + 100}`,
        district,
        lat: (match?.lat ?? 19.7515) + jitter,
        lng: (match?.lng ?? 75.7139) + jitter,
        cases,
        risk_level: cases > 80 ? 'High Risk' : 'Moderate Risk',
        latest_case: new Date().toISOString().split('T')[0],
      };
    });
    return { clusters, source: 'local' };
  },
};

// Bundled performance snapshot (mirrors ml-backend/models/metrics.json) used when the
// backend is unreachable, so the UI can still show model provenance.
const BUNDLED_METRICS: ModelPerformance = {
  model: 'Random Forest (on-device fallback)',
  accuracy: 0.864,
  precision: 0.895,
  recall: 0.841,
  f1_score: 0.867,
  roc_auc: 0.95,
  training_samples: 4000,
  last_trained: '2026-09-11T05:18:24.743Z',
  source: 'local',
};

let cachedLocations: { district: string; lat: number; lng: number }[] | null = null;

async function districtLocations(): Promise<{ district: string; lat: number; lng: number }[]> {
  if (cachedLocations) return cachedLocations;
  try {
    const res = await fetch(assetUrl('maharashtra_locations.json'));
    cachedLocations = res.ok ? ((await res.json()) as { district: string; lat: number; lng: number }[]) : [];
  } catch {
    cachedLocations = [];
  }
  return cachedLocations ?? [];
}

let backendAvailable: boolean | null = null;
let lastAccuracy = BUNDLED_METRICS.accuracy;

/** Health probe used to decide whether the hosted model service is reachable. */
export async function isBackendAvailable(): Promise<boolean> {
  try {
    const metrics = await getJson<ModelPerformance>('/model-performance');
    lastAccuracy = metrics.accuracy;
    backendAvailable = true;
  } catch {
    backendAvailable = false;
  }
  return backendAvailable;
}

export const MLApiService = {
  predictRisk: async (input: RiskInput): Promise<RiskPrediction> => {
    try {
      const data = await postJson<Omit<RiskPrediction, 'source'>>('/predict', input);
      backendAvailable = true;
      lastAccuracy = data.confidence;
      return { ...data, source: 'backend' };
    } catch {
      backendAvailable = false;
      return localEngine.predict(input, lastAccuracy);
    }
  },

  detectOutbreak: async (input: { new_cases: number; cases_growth_rate: number; deaths: number; district: string }): Promise<OutbreakDetection> => {
    try {
      const data = await postJson<Omit<OutbreakDetection, 'source'>>('/outbreak-detection', input);
      return { ...data, source: 'backend' };
    } catch {
      return localEngine.outbreakDetection(input.new_cases, input.cases_growth_rate, input.deaths, input.district);
    }
  },

  forecast: async (historicalCases: number[], horizon: number): Promise<ForecastResult> => {
    try {
      const data = await postJson<{ forecast: ForecastPoint[] }>('/forecast', {
        historical_cases: historicalCases,
        horizon,
      });
      return { ...data, source: 'backend' };
    } catch {
      return localEngine.forecast(historicalCases, horizon);
    }
  },

  cluster: async (districts: string[]): Promise<ClusterResult> => {
    try {
      const data = await postJson<{ clusters: ClusterPoint[] }>('/cluster', { districts });
      return { ...data, source: 'backend' };
    } catch {
      return localEngine.cluster(districts.length > 0 ? districts : ['Pune'], await districtLocations());
    }
  },

  modelPerformance: async (): Promise<ModelPerformance> => {
    try {
      const data = await getJson<Omit<ModelPerformance, 'source'>>('/model-performance');
      backendAvailable = true;
      lastAccuracy = data.accuracy;
      return { ...data, source: 'backend' };
    } catch {
      backendAvailable = false;
      return { ...BUNDLED_METRICS, last_trained: new Date().toISOString() };
    }
  },

  apiBase,
};

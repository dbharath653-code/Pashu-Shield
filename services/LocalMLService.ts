import { assetUrl } from './AssetPaths';

export interface ModelWeights {
  classes: string[];
  coef: number[][];
  intercept: number[];
  num_mean: number[];
  num_scale: number[];
  cat_categories: string[][];
}

const SYMPTOMS_LIST = [
  'Difficulty_swallowing', 'Lethargy', 'Fever', 'Diarrhea', 'Appetite_loss', 'Abnormal_milk', 'Weight_loss',
  'Swelling_neck', 'Blisters_on_gums', 'Abortion', 'Vomiting', 'Salivation', 'Lameness', 'Milk_decrease',
  'Sudden_death', 'Retained_placenta', 'Paralysis', 'Skin_discoloration', 'Swollen_lymph_nodes', 'Mouth_ulcers',
  'Swelling_head', 'Drop_in_egg_production', 'Swelling_udder', 'Cough', 'Difficulty_breathing', 'Nasal_discharge',
  'Bleeding_orifices', 'Swelling_limbs', 'Neurological', 'Skin_lesions', 'Aggression', 'Swelling_muscle'
];

export class LocalMLService {
  private weights: ModelWeights | null = null;

  async loadModel() {
    if (this.weights) return;
    try {
      const response = await fetch(assetUrl('model_weights.json'));
      if (response.ok) {
        this.weights = await response.json();
      }
    } catch (error) {
      console.warn('Failed to load local ML model', error);
    }
  }

  isModelReady(): boolean {
    return this.weights !== null;
  }

  predict(data: any): { disease: string, confidence: number } | null {
    if (!this.weights) return null;

    // 1. Numerical scaling (Age_Years, Temperature_C)
    const age = data.Age_Years || 3;
    const temp = data.Temperature_C || 38.5;
    
    const num_features = [
      (age - this.weights.num_mean[0]) / this.weights.num_scale[0],
      (temp - this.weights.num_mean[1]) / this.weights.num_scale[1]
    ];

    // 2. Categorical One-Hot (Species, Gender)
    const speciesIndex = this.weights.cat_categories[0].indexOf(data.Species);
    const genderIndex = this.weights.cat_categories[1].indexOf(data.Gender);
    
    const cat_features = Array.from(
      { length: this.weights.cat_categories[0].length + this.weights.cat_categories[1].length },
      () => 0
    );
    if (speciesIndex >= 0) cat_features[speciesIndex] = 1;
    if (genderIndex >= 0) cat_features[this.weights.cat_categories[0].length + genderIndex] = 1;

    // 3. Binary Symptoms
    const bin_features = SYMPTOMS_LIST.map(sym => data[sym] ? 1 : 0);

    // Combine all features (matches python ColumnTransformer order: num, cat, bin)
    const x = [...num_features, ...cat_features, ...bin_features];

    // Linear combination: z = x * coef^T + intercept
    const z = this.weights.intercept.map((inter, i) => {
      return inter + x.reduce((sum, val, j) => sum + val * this.weights!.coef[i][j], 0);
    });

    // Softmax
    const maxZ = Math.max(...z);
    const exps = z.map(val => Math.exp(val - maxZ));
    const sumExps = exps.reduce((a, b) => a + b, 0);
    const probs = exps.map(exp => exp / sumExps);

    // Argmax
    const maxProb = Math.max(...probs);
    const bestClassIdx = probs.indexOf(maxProb);

    return {
      disease: this.weights.classes[bestClassIdx],
      confidence: maxProb
    };
  }
}

export const localMLService = new LocalMLService();
import { pipeline, env } from '@xenova/transformers';

console.log("Whisper Worker started!");

// Strictly use local models served from public/models/
env.allowLocalModels = true;
env.allowRemoteModels = false;
const BASE = import.meta.env.BASE_URL || '/';
env.localModelPath = `${BASE.replace(/\/+$/, '')}/models/`;
env.backends.onnx.wasm.wasmPaths = `${BASE.replace(/\/+$/, '')}/wasm/`;

const originalFetch = globalThis.fetch;
globalThis.fetch = async function(url, options) {
    console.log("[Worker Fetch]", url);
    const response = await originalFetch(url, options);
    if (response.headers.get('content-type')?.includes('text/html') && typeof url === 'string' && url.endsWith('.json')) {
        console.error("WARNING: Server returned HTML for JSON request!", url);
    }
    return response;
};

class PipelineSingleton {
  static task = 'automatic-speech-recognition' as const;
  static model = 'Xenova/whisper-tiny';
  static instance: any = null;

  static async getInstance(progress_callback?: (data: any) => void) {
    if (this.instance === null) {
      // Models are served locally from public/models/ (see env config above)
      this.instance = pipeline(this.task, this.model, progress_callback ? { progress_callback } : {});
    }
    return this.instance;
  }
}

self.addEventListener('message', async (event) => {
  if (event.data.type === 'load') {
    try {
        await PipelineSingleton.getInstance((x: any) => {
            self.postMessage({ type: 'progress', data: x });
        });
        self.postMessage({ type: 'ready' });
    } catch (e) {
        self.postMessage({ type: 'error', error: (e as Error).message });
    }
  } else if (event.data.type === 'transcribe') {
    try {
        const transcriber = await PipelineSingleton.getInstance();
        const output = await transcriber(event.data.audio, {
          language: event.data.language || 'english',
          task: 'transcribe',
        });
        self.postMessage({ type: 'result', text: output.text });
    } catch (e) {
        self.postMessage({ type: 'error', error: (e as Error).message });
    }
  }
});
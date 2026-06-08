const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') ?? '';

// Load model config from localStorage
interface ModelConfig {
  provider: string;
  apiKey: string;
  baseUrl: string;
  model: string;
}

function getModelConfig(): ModelConfig | null {
  try {
    const saved = localStorage.getItem('veritylens_model_config');
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
}

/**
 * Stream the analysis pipeline via SSE.
 * Calls onEvent for each SSE event received.
 */
export async function analyzeText(
  payload: { text: string; url: string },
  onEvent: (eventType: string, data: any) => void
): Promise<void> {
  // Build request body with model config
  const modelConfig = getModelConfig();
  const body: any = { ...payload };
  
  if (modelConfig && modelConfig.provider !== 'duckduckgo') {
    body.model_config = {
      provider: modelConfig.provider,
      api_key: modelConfig.apiKey || undefined,
      base_url: modelConfig.baseUrl || undefined,
      model: modelConfig.model || undefined,
    };
  }
  
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Server error: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    let currentEvent = '';
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ') && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6));
          onEvent(currentEvent, data);
        } catch (e) {
          console.warn('Failed to parse SSE data:', line);
        }
        currentEvent = '';
      }
    }
  }
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}

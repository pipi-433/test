export type Attraction = {
  id: string;
  attraction_id?: string;
  scenic_area: string;
  name: string;
  category?: string;
  summary?: string;
  description?: string;
  visitor_tips?: string[];
  tags?: string[];
  source_file?: string;
};

export type Source = {
  chunk_id: string;
  title: string;
  source_file: string;
  source_section: string;
  attraction_id: string | null;
  score: number;
};

export type QAResponse = {
  answer: string;
  sources: Source[];
  mode: string;
  latency_ms: number;
};

export type VisionResponse = {
  matched_attraction: Attraction | null;
  confidence: number;
  explanation: string;
  suggested_questions: string[];
  mode: string;
  latency_ms: number;
};

type ApiErrorPayload = {
  code?: string;
  message?: string;
  cause?: string;
  fix?: string;
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    let payload: ApiErrorPayload = {};
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = {};
    }
    throw new Error(payload.message || payload.cause || `请求失败：${response.status}`);
  }

  return (await response.json()) as T;
}

export async function fetchAttractions(): Promise<Attraction[]> {
  const payload = await requestJson<{ items: Attraction[] }>("/api/attractions");
  return payload.items;
}

export async function askQuestion({
  attractionId,
  question,
}: {
  attractionId?: string;
  question: string;
}): Promise<QAResponse> {
  return requestJson<QAResponse>("/api/qa", {
    body: JSON.stringify({
      attraction_id: attractionId || null,
      question,
      top_k: 5,
      visitor_profile: {
        group_type: "family",
        time_budget_minutes: 120,
        interests: ["佛教文化", "拍照打卡"],
      },
    }),
    method: "POST",
  });
}

export async function recognizeImage({
  file,
  hint,
  textHint,
}: {
  file: File;
  hint?: string;
  textHint?: string;
}): Promise<VisionResponse> {
  const body = new FormData();
  body.append("file", file);
  if (hint) {
    body.append("hint", hint);
  }
  if (textHint) {
    body.append("text_hint", textHint);
  }
  return requestJson<VisionResponse>("/api/vision/recognize", {
    body,
    method: "POST",
  });
}

export type Background = {
  id: string;
  name: string;
  duration: number;
  thumbnail_url: string;
  video_url: string;
};

export type Voice = { id: string; name: string };

export type JobStatus = "queued" | "running" | "done" | "error";

export type Job = {
  id: string;
  status: JobStatus;
  stage: string;
  progress: number;
  error: string | null;
  title: string | null;
  script: string | null;
  video_url: string | null;
};

type Check = { ok: boolean; message: string };
export type Health = { ollama: Check; ffmpeg: Check; backgrounds: Check };

export type Length = 30 | 60 | 180;

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // not JSON; keep the status text
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const getHealth = () => request<Health>("/api/health");
export const getBackgrounds = () => request<Background[]>("/api/backgrounds");
export const getVoices = () => request<{ default: string; voices: Voice[] }>("/api/voices");
export const getJob = (id: string) => request<Job>(`/api/jobs/${id}`);

export function createJob(opts: {
  pdf: File;
  backgroundId: string;
  length: Length;
  voice: string;
}) {
  const form = new FormData();
  form.append("pdf", opts.pdf);
  form.append("background_id", opts.backgroundId);
  form.append("length", String(opts.length));
  form.append("voice", opts.voice);
  return request<{ job_id: string }>("/api/jobs", { method: "POST", body: form });
}

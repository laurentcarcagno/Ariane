import type { HarnessModel, PluginInfo } from "./types";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

async function parse<T>(res: Response): Promise<T> {
  if (res.ok) return (await res.json()) as T;
  let code = "http_error", message = `HTTP ${res.status}`;
  try {
    const body = await res.json();
    const err = body?.detail?.error ?? body?.error;
    if (err) { code = err.code; message = err.message; }
  } catch { /* keep defaults */ }
  throw new ApiError(res.status, code, message);
}

export async function listPlugins(): Promise<PluginInfo[]> {
  return parse(await fetch("/api/v1/plugins"));
}

export async function importHarness(plugin: string, files: Record<string, File>): Promise<HarnessModel> {
  const form = new FormData();
  form.set("plugin", plugin);
  for (const [role, file] of Object.entries(files)) form.set(role, file);
  return parse(await fetch("/api/v1/imports", { method: "POST", body: form }));
}

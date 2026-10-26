import { accessToken } from "./auth";
import type { HarnessModel, PluginInfo } from "./types";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

export interface ImportSummary {
  id: string; plugin: string; partNumber: string | null; drawing: string; bom: string;
  createdAt: string; createdBy: string; errors: number; warnings: number;
}
export interface Me { username: string; customer: string; label: string; roles: string[] }

async function call(url: string, init: RequestInit = {}): Promise<Response> {
  const token = accessToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(url, { ...init, headers });
}

async function parse<T>(res: Response): Promise<T> {
  if (res.ok) return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
  let code = "http_error", message = `HTTP ${res.status}`;
  try {
    const body = await res.json();
    const err = body?.detail?.error ?? body?.error;
    if (err) { code = err.code; message = err.message; }
  } catch { /* keep defaults */ }
  throw new ApiError(res.status, code, message);
}

export const me = async (): Promise<Me> => parse(await call("/api/v1/me"));
export const listPlugins = async (): Promise<PluginInfo[]> => parse(await call("/api/v1/plugins"));
export const listImports = async (): Promise<ImportSummary[]> => parse(await call("/api/v1/imports"));
export const getImport = async (id: string): Promise<HarnessModel> => (await parse<{ model: HarnessModel }>(await call(`/api/v1/imports/${id}`))).model;
export const deleteImport = async (id: string): Promise<void> => parse(await call(`/api/v1/imports/${id}`, { method: "DELETE" }));

export async function importHarness(plugin: string, files: Record<string, File>): Promise<{ id: string; model: HarnessModel }> {
  const form = new FormData();
  form.set("plugin", plugin);
  for (const [role, file] of Object.entries(files)) form.set(role, file);
  return parse(await call("/api/v1/imports", { method: "POST", body: form }));
}

/** Downloads the Excel workbook of a stored analysis (the bearer token rules out a plain link). */
export async function downloadXlsx(id: string): Promise<void> {
  const res = await call(`/api/v1/imports/${id}/export.xlsx`);
  if (!res.ok) await parse(res);
  const name = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? "harness.xlsx";
  const url = URL.createObjectURL(await res.blob());
  Object.assign(document.createElement("a"), { href: url, download: name }).click();
  URL.revokeObjectURL(url);
}

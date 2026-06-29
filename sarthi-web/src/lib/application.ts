const BASE = "/api/agent";

export type SchemaField = {
  key: string; label: string; type: string; extractable: boolean; required: boolean;
};
export type SchemaSection = { key: string; title: string; fields: SchemaField[] };
export type SchemaDoc = { key: string; label: string };

export type Application = {
  fields: Record<string, string>;
  ai_filled: string[];
  documents: Record<string, boolean>;
  status: "draft" | "submitted";
  reference: string | null;
  schema: { sections: SchemaSection[]; documents: SchemaDoc[] };
  completeness: { filled: number; total: number };
};

const j = async (res: Response): Promise<Application> => {
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()).application as Application;
};

export const getApplication = () =>
  fetch(`${BASE}/application`, { credentials: "include" }).then(j);

export const saveApplication = (fields: Record<string, string>, documents: Record<string, boolean>) =>
  fetch(`${BASE}/application`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ fields, documents }),
  }).then(j);

export const submitApplication = () =>
  fetch(`${BASE}/application/submit`, { method: "POST", credentials: "include" }).then(j);

export const resetApplication = () =>
  fetch(`${BASE}/application/reset`, { method: "POST", credentials: "include" }).then(j);

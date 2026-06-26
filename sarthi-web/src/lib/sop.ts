const BASE = "/api/agent";

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export type SopMeta = {
  id: number;
  title: string;
  created_at: string;
  latest_version_id: number | null;
  updated_at: string | null;
  word_count: number | null;
};

export type Analysis = {
  word_count: number;
  paragraph_count: number;
  length_flag: "short" | "ok" | "long";
  target_words: [number, number];
  cliche_hits: { phrase: string; count: number }[];
  long_sentences: { text_preview: string; word_count: number }[];
  long_sentence_threshold: number;
  structure_signals: { mentions_program: boolean; mentions_goal: boolean; gives_reasons: boolean };
  note: string;
};

export type Version = {
  id: number;
  content: string;
  analysis: Analysis;
  created_at: string;
  word_count: number;
};

export const listSops = () =>
  fetch(`${BASE}/sops`, { credentials: "include" }).then(j<{ sops: SopMeta[] }>).then((d) => d.sops);

export const createSop = (title: string) =>
  fetch(`${BASE}/sops`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ title }),
  }).then(j<{ id: number; title: string; created_at: string }>);

export const getSop = (id: number) =>
  fetch(`${BASE}/sops/${id}`, { credentials: "include" }).then(
    j<{ sop: SopMeta; latest: Version | null }>,
  );

export const saveVersion = (id: number, content: string) =>
  fetch(`${BASE}/sops/${id}/versions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ content }),
  }).then(j<{ version: { id: number; created_at: string }; analysis: Analysis }>);

export const listVersions = (id: number) =>
  fetch(`${BASE}/sops/${id}/versions`, { credentials: "include" })
    .then(j<{ versions: { id: number; created_at: string; word_count: number }[] }>)
    .then((d) => d.versions);

export const getVersion = (sopId: number, vId: number) =>
  fetch(`${BASE}/sops/${sopId}/versions/${vId}`, { credentials: "include" })
    .then(j<{ version: Version }>)
    .then((d) => d.version);

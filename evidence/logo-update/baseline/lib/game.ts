export type Mode = 'easy' | 'hard';
export type Stage = { id: number; title: string; location: string; category: string; weight: number; summary: string };
export type Clue = Stage & { payload: string; objective: string; hints: string[]; sample: string; tool: string; artifact_name: string; debrief: string | null };
export type Progress = { solved: number[]; points: number; hints: Record<string, number> };
export type Session = { name: string; csrf: string; modes: Record<Mode, Progress> };
export type Reward = { name: string; code: string; reward: string; event: string; instruction: string; seconds: number; logo_ready: boolean };
export type Entry = { name: string; solved: number; points: number; seconds: number | null };
export async function api<T>(path: string, data?: unknown, csrf?: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch('/api/v1/' + path, {
    method: data !== undefined ? 'POST' : 'GET', cache: 'no-store', signal,
    headers: { 'Content-Type': 'application/json', 'X-Expedition': '1', ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  const body = await response.json();
  if (!response.ok) { const error = new Error(body.detail || 'Yêu cầu chưa hoàn tất.'); Object.assign(error, { status: response.status }); throw error; }
  return body;
}
export function message(error: unknown) { return error instanceof Error ? error.message : 'Kết nối bị gián đoạn. Hãy thử lại.'; }

export function decode(input: string, tool: string, shift: number, key: string) {
  const fromHex = (s: string) => {
    const clean = s.replace(/\s/g, '');
    if (!clean.length || clean.length % 2 || !/^[a-f\d]+$/i.test(clean)) throw new Error('Hex cần các cặp ký tự 0–9, a–f.');
    return Uint8Array.from(clean.match(/../g)!, x => parseInt(x, 16));
  };
  const b64 = (s: string) => {
    try { return Uint8Array.from(atob(s.trim()), c => c.charCodeAt(0)); }
    catch { throw new Error('Kiểm tra lại chuỗi Base64, kể cả dấu = ở cuối.'); }
  };
  const text = (bytes: Uint8Array) => { try { return new TextDecoder('utf-8', { fatal: true }).decode(bytes); } catch { throw new Error('Kết quả chưa phải UTF-8. Kiểm tra khóa hoặc lớp biểu diễn.'); } };
  if (!input.trim()) throw new Error('Dán dữ liệu cần giải trước nhé.');
  if (input.length > 20000) throw new Error('Bàn giải mã nhận tối đa 20.000 ký tự.');
  if (tool === 'base64') return text(b64(input));
  if (tool === 'hex') return text(fromHex(input));
  if (tool === 'caesar') return input.replace(/[a-z]/gi, c => {
    const base = c <= 'Z' ? 65 : 97;
    return String.fromCharCode((c.charCodeAt(0) - base - ((shift % 26 + 26) % 26) + 26) % 26 + base);
  });
  if (tool === 'inspect') return input; // Deliberately text, never execute supplied HTML.
  if (tool === 'log') {
    const parts = [...input.matchAll(/FRAGMENT seq=(\d+) text=([^\r\n]+)/g)];
    if (!parts.length) throw new Error('Chưa thấy dòng FRAGMENT seq=… text=…');
    return parts.sort((a, b) => +a[1] - +b[1]).map(m => m[2]).join('');
  }
  if (!key) throw new Error('XOR cần khóa. Kiểm tra manh mối tại hải đăng.');
  const bytes = tool === 'xor64' ? b64(input) : fromHex(input);
  const k = new TextEncoder().encode(key);
  return text(bytes.map((b, i) => b ^ k[i % k.length]));
}

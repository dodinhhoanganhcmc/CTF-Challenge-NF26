import { NextRequest } from 'next/server';
export const dynamic = 'force-dynamic';
const allowed = /^(session|catalog|leaderboard|treasure|stages\/[1-5](?:\/(artifact|hints|answers))?)$/;

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const route = path.join('/');
  if (!allowed.test(route)) return Response.json({ detail: 'Đường dẫn không tồn tại.' }, { status: 404 });
  const writes = request.method === 'POST';
  const postAllowed = route === 'session' || /^stages\/[1-5]\/(answers|hints)$/.test(route);
  if (writes && !postAllowed) return Response.json({ detail: 'Phương thức không hợp lệ.' }, { status: 405 });
  if (!writes && /\/(answers|hints)$/.test(route)) return Response.json({ detail: 'Phương thức không hợp lệ.' }, { status: 405 });
  const origins = (process.env.APP_ORIGINS || 'http://127.0.0.1:3000,http://localhost:3000').split(',');
  if (writes && (!origins.includes(request.headers.get('origin') || '') || request.headers.get('x-expedition') !== '1')) {
    return Response.json({ detail: 'Nguồn yêu cầu không hợp lệ.' }, { status: 403 });
  }
  let body: ArrayBuffer | undefined;
  if (writes) {
    // Bound the stream before buffering, even when Content-Length is absent.
    const reader = request.body?.getReader();
    const chunks: Uint8Array[] = []; let size = 0;
    if (reader) while (true) {
      const { done, value } = await reader.read(); if (done) break;
      size += value.length;
      if (size > 4096) { await reader.cancel(); return Response.json({ detail: 'Dữ liệu vượt quá 4 KB.' }, { status: 413 }); }
      chunks.push(value);
    }
    const joined = new Uint8Array(size); let offset = 0;
    for (const chunk of chunks) { joined.set(chunk, offset); offset += chunk.length; }
    body = joined.buffer;
  }
  const headers = new Headers();
  for (const key of ['cookie', 'content-type', 'x-csrf-token', 'x-expedition', 'origin']) {
    const value = request.headers.get(key); if (value) headers.set(key, value);
  }
  const url = new URL('/api/v1/' + route, process.env.BACKEND_URL || 'http://127.0.0.1:8000');
  for (const key of ['mode', 'limit', 'offset']) {
    const value = request.nextUrl.searchParams.get(key); if (value !== null) url.searchParams.set(key, value);
  }
  try {
    const upstream = await fetch(url, { method: request.method, headers, body, cache: 'no-store', signal: AbortSignal.timeout(10000), redirect: 'error' });
    const resultHeaders = new Headers({ 'Cache-Control': 'no-store' });
    for (const key of ['content-type', 'set-cookie', 'content-disposition', 'retry-after']) {
      const value = upstream.headers.get(key); if (value) resultHeaders.set(key, value);
    }
    return new Response(upstream.body, { status: upstream.status, headers: resultHeaders });
  } catch {
    return Response.json({ detail: 'Chưa kết nối được máy chủ trò chơi. Thử lại sau ít giây nhé.' }, { status: 503 });
  }
}
export const GET = proxy;
export const POST = proxy;

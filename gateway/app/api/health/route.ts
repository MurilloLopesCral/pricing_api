export const runtime = 'edge';

export async function GET() {
  return new Response(
    JSON.stringify({ ok: true, source: 'ai-gateway' }),
    { headers: { 'Content-Type': 'application/json' } }
  );
}

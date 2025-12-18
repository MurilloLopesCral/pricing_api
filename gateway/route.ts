export const runtime = 'edge';

export async function GET() {
  return new Response(
    JSON.stringify({
      ok: true,
      service: 'pricing-ai-gateway'
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );
}

export async function proxyToPricing(
  req: Request,
  targetPath: string
) {
  try {
    console.log('--- AI GATEWAY ---');
    console.log('PATH:', targetPath);
    console.log('ENV:', {
      PRICING_API_URL: process.env.PRICING_API_URL,
      HAS_PRICING_KEY: !!process.env.PRICING_INTERNAL_KEY,
      HAS_AI_KEY: !!process.env.AI_GATEWAY_KEY
    });

    const apiKey = req.headers.get('x-api-key');
    console.log('REQ KEY:', apiKey);

    // if (apiKey !== process.env.AI_GATEWAY_KEY) {
    //   return new Response(
    //     JSON.stringify({ error: 'Unauthorized' }),
    //     { status: 401 }
    //   );
    // }

    console.log('HEADERS:', Object.fromEntries(req.headers));



    const body = await req.text();
    console.log('BODY:', body);

    const res = await fetch(
      `${process.env.PRICING_API_URL}${targetPath}`,
      {
        method: req.method,
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': process.env.PRICING_INTERNAL_KEY!
        },
        body
      }
    );

    const text = await res.text();
    return new Response(text, {
      status: res.status,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (err: any) {
    console.error('GATEWAY ERROR:', err?.message || err);
    return new Response(
      JSON.stringify({ error: 'Gateway error', detail: String(err) }),
      { status: 500 }
    );
  }
}
  
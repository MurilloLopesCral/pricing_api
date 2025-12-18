import { proxyToPricing } from '@/app/utils/proxy';

export const runtime = 'edge';

export async function POST(req: Request) {
  return proxyToPricing(req, '/analytics/compare');
}

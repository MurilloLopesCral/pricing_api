(globalThis.TURBOPACK || (globalThis.TURBOPACK = [])).push(["chunks/[root-of-the-server]__19b9905a._.js",
"[externals]/node:buffer [external] (node:buffer, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("node:buffer", () => require("node:buffer"));

module.exports = mod;
}),
"[externals]/node:async_hooks [external] (node:async_hooks, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("node:async_hooks", () => require("node:async_hooks"));

module.exports = mod;
}),
"[project]/app/utils/proxy.ts [app-edge-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "proxyToPricing",
    ()=>proxyToPricing
]);
async function proxyToPricing(req, targetPath) {
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
        if (apiKey !== process.env.AI_GATEWAY_KEY) {
            return new Response(JSON.stringify({
                error: 'Unauthorized'
            }), {
                status: 401
            });
        }
        const body = await req.text();
        console.log('BODY:', body);
        const res = await fetch(`${process.env.PRICING_API_URL}${targetPath}`, {
            method: req.method,
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': process.env.PRICING_INTERNAL_KEY
            },
            body
        });
        const text = await res.text();
        return new Response(text, {
            status: res.status,
            headers: {
                'Content-Type': 'application/json'
            }
        });
    } catch (err) {
        console.error('GATEWAY ERROR:', err?.message || err);
        return new Response(JSON.stringify({
            error: 'Gateway error',
            detail: String(err)
        }), {
            status: 500
        });
    }
}
}),
"[project]/app/api/analytics/query/route.ts [app-edge-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "POST",
    ()=>POST,
    "runtime",
    ()=>runtime
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$utils$2f$proxy$2e$ts__$5b$app$2d$edge$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/app/utils/proxy.ts [app-edge-route] (ecmascript)");
;
const runtime = 'edge';
async function POST(req) {
    return (0, __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$utils$2f$proxy$2e$ts__$5b$app$2d$edge$2d$route$5d$__$28$ecmascript$29$__["proxyToPricing"])(req, '/analytics/query');
}
}),
]);

//# sourceMappingURL=%5Broot-of-the-server%5D__19b9905a._.js.map
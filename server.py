from aiohttp import web
import asyncio

async def handle_health_check(request):
    return web.Response(text="Bot is running!", status=200)

async def start_server(port):
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Dummy server started on port {port}")
    return runner

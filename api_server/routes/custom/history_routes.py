from aiohttp import web

class HistoryRoutes:
    def __init__(self, prompt_server):
        self.prompt_server = prompt_server

    def get_routes(self):
        routes = web.RouteTableDef()
        
        @routes.get("/api/custom/history/{prompt_id}")
        async def get_history_by_prompt_id(request):
            prompt_id = request.match_info.get("prompt_id", None)
            if prompt_id is None:
                return web.Response(status=400, text="Prompt ID is required")
            
            history_data = self.prompt_server.prompt_queue.get_history(prompt_id=prompt_id)
            return web.json_response(history_data)

        return routes 
from .clothes_routes import ClothesRoutes
from .history_routes import HistoryRoutes
from .image_routes import ImageRoutes
from .workflow_routes import WorkflowRoutes

class CustomRoutes:
    def __init__(self, prompt_server):
        self.clothes_routes = ClothesRoutes(prompt_server)
        self.history_routes = HistoryRoutes(prompt_server)
        self.image_routes = ImageRoutes(prompt_server)
        self.workflow_routes = WorkflowRoutes(prompt_server)

    def get_routes(self):
        routes = []
        routes.extend(self.clothes_routes.get_routes())
        routes.extend(self.history_routes.get_routes())
        routes.extend(self.image_routes.get_routes())
        routes.extend(self.workflow_routes.get_routes())
        return routes 
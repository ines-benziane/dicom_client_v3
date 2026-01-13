from services.move import Move
from config.server_config import TelemisConfig
from services.search_criteria import SearchCriteria

class MoveController:
    def __init__(self):
        self.config = TelemisConfig
        self.move_service = Move(self.config)

    def move(self, search_criteria: SearchCriteria, destination=None):
        return self.move_service.move_data(search_criteria, destination)
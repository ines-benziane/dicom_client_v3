from services.get_service import get
from config.server_config import TelemisConfig
from services.search_criteria import SearchCriteria

class GetController:
    def __init__(self):
        self.get_service = get
        self.current_get_results = []
        self.config = config or TelemisConfig

    def get(self, search_criteria: SearchCriteria):
        data = Get(self.config)
        results = data.retrieve_data(search_criteria)
        return results
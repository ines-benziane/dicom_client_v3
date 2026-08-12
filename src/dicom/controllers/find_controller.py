from services.find import Find
from services.search_criteria import SearchCriteria

class FindController:
    def __init__(self):
        self.find_service = Find(config)
        self.current_search_results = []

    def find(self, search_criteria: SearchCriteria):
        results = self.find_service.search_data("STUDY")
        self._current_search_results = results
        return results

    
from services.find import Find
from services.move import Move
from services.search_criteria import SearchCriteria

class BatchController:
    def __init__(self, config):
        self.finder = Find(config)
        self.mover = Move(config)

    def process_patient_list(self, patient_data_list):
        """
        patient_data_list : liste de dictionnaires [{'name': '...', 'series': '...'}]
        """
        for entry in patient_data_list:
            criteria = SearchCriteria(
                patient_name=entry['name'],
                series_description=entry['series'],
                level="SERIES"
            )
            results = self.finder.search_data(criteria)
            
            if not results:
                print(f"W: Rien trouvé pour {entry['name']} - {entry['series']}")
                continue

            for identifier in results:
                criteria.study_instance_uid = identifier.StudyInstanceUID
                criteria.series_instance_uid = identifier.SeriesInstanceUID
                self.mover.move_data(criteria)
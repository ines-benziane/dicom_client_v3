class SearchCriteria:
    def __init__(self, level=None, patient_id=None, patient_name=None, study_date=None, study_description=None, series_description=None, accession_number=None, modality=None, series_instance_uid=None, study_instance_uid=None, patient_birth_date=None):
        self.level = level
        self.patient_id = patient_id
        self.patient_name = patient_name
        self.study_date = study_date
        self.study_description = study_description
        self.series_description = series_description
        self.accession_number = accession_number
        self.modality = modality
        self.series_instance_uid = series_instance_uid
        self.study_instance_uid = study_instance_uid
        self.patient_birth_date = patient_birth_date
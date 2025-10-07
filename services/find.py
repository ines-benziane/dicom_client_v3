from pynetdicom import AE, evt
from pydicom.dataset import Dataset
from pynetdicom.sop_class import StudyRootQueryRetrieveInformationModelFind
from config.server_config import TelemisConfig
from services.search_criteria import SearchCriteria
import logging

class Find:
    PENDING_STATUS = 0xFF00
    SUCCESS_STATUS = 0x0000

    def __init__(self, config):
        self.config = config
        self.ae_factory = self.config.CALLING_AET
        self.setup_ae()

    def setup_ae(self):
        """Configure Application Entity (AE)"""
        self.ae = AE(ae_title=self.config.CALLING_AET)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)

    def _establish_connection(self):
        """Establish association with the DICOM server"""
        self.assoc = self.ae.associate(
            self.config.HOST, 
            self.config.PORT,
            ae_title=self.config.CALLED_AET
        )
        return self.assoc.is_established

    def _build_query_dataset(self, search_criteria, query_level):
        """Build the DICOM query dataset based on search criteria"""
        ds = Dataset()
        ds.QueryRetrieveLevel = query_level
        ds.PatientID = search_criteria.patient_id or ''
        ds.PatientName = search_criteria.patient_name or ''
        ds.StudyDate = search_criteria.study_date or ''
        ds.StudyDescription = search_criteria.study_description or ''
        ds.SeriesDescription = search_criteria.series_description or ''
        ds.AccessionNumber = search_criteria.accession_number or ''
        ds.Modality = search_criteria.modality or ''
        return ds

    def _perform_find(self, query_dataset):
        """Perform the C-FIND operation"""
        responses = self.assoc.send_c_find(query_dataset, self.sop_class)
        results = []
        for status, identifier in responses:
            if status and status.Status == self.PENDING_STATUS:
                results.append(identifier)
            elif status and status.Status == self.SUCCESS_STATUS:
                break
        self.assoc.release()
        return results

    def search_data(self, criteria: SearchCriteria):
        """Main entry point"""
        query_level = criteria.level
        print(f"Query Level: {query_level}")
        info_model = "STUDY_ROOT"
        self.sop_class = StudyRootQueryRetrieveInformationModelFind
        try:
            if self._establish_connection():
                print("Association established.")
                query_dataset = self._build_query_dataset(criteria, query_level)    
                return self._perform_find(query_dataset)
            return []
        except Exception as e:
            print(f"DICOM search error: {e}")
            logging.error(f"DICOM search error: {e}")
            return []
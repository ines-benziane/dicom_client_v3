from pathlib import Path
from pydicom import Dataset
from services.search_criteria import SearchCriteria
from pynetdicom import AE, evt, StoragePresentationContexts, AllStoragePresentationContexts, build_role
from pynetdicom.sop_class import StudyRootQueryRetrieveInformationModelGet, MRImageStorage, MRSpectroscopyStorage
from pydicom.uid import ExplicitVRLittleEndian, ImplicitVRLittleEndian
import threading
import time
import logging

class Get:
    SUCCESS_STATUS = 0x0000
    MAX_CONTEXTS = 127

    def __init__(self,  config, output_dir="output_dir",ae_factory=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.ae_factory = self.config.CALLING_AET
        # files_received is incremented by the C-STORE handler (may run in another thread)
        self.files_received = 0
        self._files_lock = threading.Lock()
        self._setup_ae()

    def _setup_ae(self):
        """Configure Application Entity (AE)"""
        self.ae = AE(ae_title=self.config.CALLING_AET)
        self.ae.requested_contexts = StoragePresentationContexts[:self.MAX_CONTEXTS]
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelGet)
        self.ae.add_supported_context(MRImageStorage)
        self.ae.add_supported_context(MRSpectroscopyStorage)
        self.role_mr_image = build_role(MRImageStorage, scp_role=True)
        self.role_mr_spectro = build_role(MRSpectroscopyStorage, scp_role=True)

    def _establish_connection(self):
        """DICOM Connection"""
        handlers = [(evt.EVT_C_STORE, self._handle_store)]
        self.scp = self.ae.start_server(("", 0), block=False, evt_handlers=handlers)
        
        ext_neg = [self.role_mr_image, self.role_mr_spectro]
        self.assoc = self.ae.associate(
            self.config.HOST, 
            self.config.PORT, 
            ae_title=self.config.CALLED_AET, 
            ext_neg=ext_neg, 
            evt_handlers=handlers
        )
        return self.assoc.is_established

    def _save_dicom_file(self, dataset, filename, target_dir=None):
        """Centralise and save"""
        if target_dir is None:
            target_dir = self.output_dir
        filepath = target_dir / filename
        dataset.save_as(filepath, write_like_original=False)


    def _handle_store(self, event):
        """Handle incoming DICOM store request"""
        ds = event.dataset
        ds.file_meta = event.file_meta
        
        if hasattr(ds, 'SeriesNumber') and hasattr(ds, 'SeriesDescription'):
            series_dir = self.output_dir / f"{ds.SeriesNumber}_{ds.SeriesDescription.replace(' ', '_')}"
            series_dir.mkdir(exist_ok=True)
            filename = f"{ds.SOPInstanceUID}.dcm"
            self._save_dicom_file(ds, filename, series_dir)
            
            with self._files_lock:
                self.files_received += 1
                if self.files_received % 10 == 0:
                    print(f"I: Received {self.files_received} files...")


        return 0x0000

    def _build_query_dataset(self, search_criteria, query_level):
        """Build the DICOM query dataset based on search criteria"""
        ds = Dataset()
        ds.QueryRetrieveLevel = query_level
        ds.StudyInstanceUID = getattr(search_criteria, 'study_instance_uid', '') or ''
        if query_level == "SERIES":
            ds.SeriesInstanceUID = getattr(search_criteria, 'series_instance_uid', '') or ''
        return ds
        
    def _perform_get(self, query_dataset):
        """Perform the C-GET operation"""
        start_time = time.time()

        responses = self.assoc.send_c_get(query_dataset, StudyRootQueryRetrieveInformationModelGet)
        for (status, identifier) in responses:
            if status and status.Status == self.SUCCESS_STATUS:
                break

        # collect result and timing
        with self._files_lock:
            received = self.files_received
        elapsed = time.time() - start_time

        print(f"I: C-GET completed in {elapsed:.1f}s — files received for this study: {received}")
        try:
            self.assoc.release()
        except Exception:
            pass
        return received

    def retrieve_data(self, criteria: SearchCriteria):
        """Main entry point"""
        query_level = criteria.level
        info_model = "STUDY_ROOT"
        self.files_received = 0

        try:
            if self._establish_connection():
                query_ds = self._build_query_dataset(criteria, query_level)
                received = self._perform_get(query_ds)
                return received
            return False
        except Exception as e:
            print(f"DICOM retrieval error: {e}")
            return False
        return False


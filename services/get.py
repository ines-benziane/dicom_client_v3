from pathlib import Path
import click
from pydicom import Dataset
from services.json_file import SeriesMetadataCollector
from services.search_criteria import SearchCriteria
# from services.anonym_service import anonymize_dataset
from controllers.anonym_controller import AnonymController
from controllers.pseudonym_controller import PseudonymController
from pynetdicom import AE, evt, StoragePresentationContexts, AllStoragePresentationContexts, build_role
from pynetdicom.sop_class import StudyRootQueryRetrieveInformationModelGet, MRImageStorage, MRSpectroscopyStorage
from pydicom.uid import ExplicitVRLittleEndian, ImplicitVRLittleEndian
import threading
import time
import logging
import tqdm

class Get:
    SUCCESS_STATUS = 0x0000
    MAX_CONTEXTS = 127

    def __init__(self,  config, output_dir="output_dir",ae_factory=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.ae_factory = self.config.CALLING_AET
        self.files_received = 0
        self._setup_ae()
        self.metadata_collector = None
        self.current_patient_dir = None
        self.current_criteria = None
        self.pseudo_controller = PseudonymController()
        self.ano_controller = AnonymController()


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
        # Build optional association kwargs from config (do not break if absent)
        assoc_kwargs = dict(
            ae_title=self.config.CALLED_AET,
            ext_neg=ext_neg,
            evt_handlers=handlers,
        )

        try:
            self.assoc = self.ae.associate(
                self.config.HOST,
                self.config.PORT,
                **assoc_kwargs,
            )
        except TypeError as e:
            logging.debug("Association failed due to unexpected argument: %s", e)
            self.assoc = self.ae.associate(
                self.config.HOST,
                self.config.PORT,
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
 
        # Anonymize dataset if requested
        if self.current_criteria and getattr(self.current_criteria, 'anonymize', True):
            ds = self.ano_controller.anonymize_file(event.dataset)
        # Apply pseudonymization if requested
        elif self.current_criteria and (getattr(self.current_criteria, 'clinical_pseudo', True) or 
                                        getattr(self.current_criteria, 'research_pseudo', True) or 
                                        getattr(self.current_criteria, 'protocol_pseudo', True)):
            ds = self.pseudo_controller.pseudonymize_file(event.dataset)
        else:
            ds = event.dataset
        ds.file_meta = event.file_meta
        # Extract Patient ID to organize files
        patient_id = getattr(ds, 'PatientID', 'Unknown_Patient')
        # Sanitize patient ID for folder name
        # Use chained replace calls (each with two arguments) to avoid TypeError from invalid extra args
        patient_id_safe = (
            str(patient_id)
            .replace('/', '_')
            .replace(':', '_')
            .replace('\\', '_')
            .replace(' ', '_')
        )
        
        # Create patient directory if needed
        patient_dir = self.output_dir / patient_id_safe
        patient_dir.mkdir(exist_ok=True)
        
        # Initialize metadata collector for this patient if not done yet
        if self.current_patient_dir != patient_dir:
            if self.metadata_collector is not None:
                # Save previous patient's metadata
                self.metadata_collector.save_to_json()
            self.current_patient_dir = patient_dir
            self.metadata_collector = SeriesMetadataCollector(patient_dir)
        
        # Process series information
        series_number = getattr(ds, 'SeriesNumber', None)
        series_desc = getattr(ds, 'SeriesDescription', 'Unknown_Series')
        if series_number is not None:
            # Create series subdirectory inside patient directory
            series_desc_safe = str(series_desc).replace(' ', '_').replace('/', '_').replace('\\', '_')
            series_dir = patient_dir / f"{series_number}_{series_desc_safe}"
            series_dir.mkdir(exist_ok=True)
            filename = f"{ds.SOPInstanceUID}.dcm"
            self._save_dicom_file(ds, filename, series_dir)
            self.files_received += 1
            self.metadata_collector.add_instance(ds)
        return 0x0000

    def _build_query_dataset(self, search_criteria, query_level):
        """Build the DICOM query dataset based on search criteria"""
        ds = Dataset()
        ds.QueryRetrieveLevel = query_level
        ds.StudyInstanceUID = search_criteria.study_instance_uid or ''
        ds.SeriesInstanceUID = search_criteria.series_instance_uid  or ''
        if query_level == "SERIES":
            ds.SeriesDate = search_criteria.series_date or ''
            ds.SeriesDescription = search_criteria.series_description or ''
            ds.SeriesNumber = ''
        return ds
        

    def _perform_get(self, query_dataset):
        """Perform the C-GET operation"""
        start_time = time.time()

        responses = self.assoc.send_c_get(query_dataset, StudyRootQueryRetrieveInformationModelGet)
        pbar = tqdm.tqdm(desc="C-GET", unit="resp", dynamic_ncols=True)
        try:
            for (status, identifier) in responses:
                pbar.update(1)
                pbar.set_postfix(files_received=self.files_received,
                        status=(hex(status.Status) if status else "None"))
                if status and status.Status == self.SUCCESS_STATUS:
                    break
        finally:
            pbar.close()

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
        # info_model = "STUDY_ROOT"
        self.files_received = 0
        # Store criteria for use in handlers
        self.current_criteria = criteria

        try:
            if self._establish_connection():
                query_ds = self._build_query_dataset(criteria, query_level)
                received = self._perform_get(query_ds)
                click.echo(f"I: Total files received: {received}")
                # Save metadata for the last patient processed
                if received > 0 and self.metadata_collector is not None:
                    print("I: Saving series metadata to JSON...")
                    self.metadata_collector.save_to_json()
                return received
            return False
        except Exception as e:
            print(f"DICOM retrieval error: {e}")
            return False


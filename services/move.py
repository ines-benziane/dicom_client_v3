from pathlib import Path
import click
from pydicom import Dataset
from pynetdicom import AE, evt, StoragePresentationContexts
from pynetdicom.sop_class import StudyRootQueryRetrieveInformationModelMove
from services.search_criteria import SearchCriteria
from services.json_file import SeriesMetadataCollector
from controllers.anonym_controller import AnonymController
from controllers.pseudonym_controller import PseudonymController

class Move:
    def __init__(self, config, output_dir="output_dir"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialisation identique à ton Get.py
        self.ano_controller = AnonymController()
        self.pseudo_controller = PseudonymController()
        
        self.ae = AE(ae_title=self.config.CALLING_AET)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelMove)
        self.ae.supported_contexts = StoragePresentationContexts
        
        self.files_received = 0
        self.current_criteria = None
        self.metadata_collector = None
        self.current_patient_dir = None

    def _handle_store(self, event):
        """Ta logique de stockage et d'anonymisation extraite de Get.py"""
        # Anonymisation / Pseudonymisation
        if self.current_criteria and getattr(self.current_criteria, 'anonymize_data', False):
            ds = self.ano_controller.anonymize_file(event.dataset)
        elif self.current_criteria and (getattr(self.current_criteria, 'clinical_pseudo', False) or 
                                        getattr(self.current_criteria, 'research_pseudo', False)):
            ds = self.pseudo_controller.pseudonymize_file(event.dataset)
        else:
            ds = event.dataset

        ds.file_meta = event.file_meta
        
        # Organisation des dossiers
        patient_id = getattr(ds, 'PatientID', 'Unknown_Patient')
        patient_id_safe = str(patient_id).replace('/', '_').replace(':', '_').replace('\\', '_').replace(' ', '_')
        
        patient_dir = self.output_dir / patient_id_safe
        patient_dir.mkdir(exist_ok=True)
        
        if self.current_patient_dir != patient_dir:
            if self.metadata_collector is not None:
                self.metadata_collector.save_to_json()
            self.current_patient_dir = patient_dir
            self.metadata_collector = SeriesMetadataCollector(patient_dir)
        
        series_number = getattr(ds, 'SeriesNumber', '0')
        series_desc = getattr(ds, 'SeriesDescription', 'Unknown_Series')
        series_dir = patient_dir / f"{series_number}_{series_desc.replace(' ', '_')}"
        series_dir.mkdir(exist_ok=True)
        
        # Sauvegarde
        filename = f"{ds.SOPInstanceUID}.dcm"
        ds.save_as(series_dir / filename, write_like_dicom=False)
        
        self.files_received += 1
        self.metadata_collector.add_instance(ds)
        return 0x0000

    def move_data(self, criteria: SearchCriteria, destination_aet=None):
        self.current_criteria = criteria
        self.files_received = 0
        
        # 1. On prépare le serveur de réception
        handlers = [(evt.EVT_C_STORE, self._handle_store)]
        scp = self.ae.start_server(("", 0), block=False, evt_handlers=handlers)
        local_port = scp.server_address[1]
        
        dest = destination_aet or self.config.CALLING_AET
        assoc = self.ae.associate(self.config.HOST, self.config.PORT, ae_title=self.config.CALLED_AET)
        
        if assoc.is_established:
            # 2. Construction du dataset de recherche
            # IMPORTANT: C-MOVE au niveau STUDY nécessite obligatoirement le StudyInstanceUID
            ds = Dataset()
            ds.QueryRetrieveLevel = criteria.level
            
            # Si on n'a pas d'UID, le C-MOVE échouera sur la plupart des PACS
            if not criteria.study_instance_uid:
                click.echo(click.style("W: C-MOVE requires a StudyInstanceUID. Use search first.", fg='yellow'))
                # Optionnel : Tu pourrais lancer un Find ici automatiquement
            
            ds.StudyInstanceUID = criteria.study_instance_uid or ''
            if criteria.level == 'SERIES':
                ds.SeriesInstanceUID = criteria.series_instance_uid or ''
                
            click.echo(f"I: C-MOVE listening on port {local_port}, Destination: {dest}")
            
            # 3. Envoi avec gestion du timeout
            responses = assoc.send_c_move(ds, dest, StudyRootQueryRetrieveInformationModelMove)
            
            try:
                for (status, identifier) in responses:
                    if status:
                        # Status 0xFF00 est 'Pending' (en cours)
                        # Status 0x0000 est 'Success'
                        print(f"I: Move Status: {hex(status.Status)}")
            except Exception as e:
                click.echo(f"E: Error during response iteration: {e}")
                
            assoc.release()
            scp.shutdown()
            return self.files_received
        
        scp.shutdown()
        return False
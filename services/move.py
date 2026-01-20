from pathlib import Path
from time import sleep
from time import time
import pydicom
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
        self.temp_dir = self.output_dir / "temp_transit"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
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
        self.ae.dimse_timeout = 1200
        self.ae.network_timeout = 1200 
        self.ae.acse_timeout = 1200    

    # def _handle_store(self, event):
    #     # if self.current_criteria and getattr(self.current_criteria, 'anonymize_data', False):
    #     #     ds = self.ano_controller.anonymize_file(event.dataset)
    #     # elif self.current_criteria and (getattr(self.current_criteria, 'clinical_pseudo', False) or 
    #     #                                 getattr(self.current_criteria, 'research_pseudo', False)):
    #     #     ds = self.pseudo_controller.pseudonymize_file(event.dataset)
    #     # else:
    #     ds = event.dataset

    #     ds.file_meta = event.file_meta
        
    #     patient_id = getattr(ds, 'PatientID', 'Unknown_Patient')
    #     patient_id_safe = str(patient_id).replace('/', '_').replace(':', '_').replace('\\', '_').replace(' ', '_')
        
    #     patient_dir = self.output_dir / patient_id_safe
    #     patient_dir.mkdir(exist_ok=True)
        
    #     if self.current_patient_dir != patient_dir:
    #         if self.metadata_collector is not None:
    #             self.metadata_collector.save_to_json()
    #         self.current_patient_dir = patient_dir
    #         # self.metadata_collector = SeriesMetadataCollector(patient_dir)
        
    #     series_number = getattr(ds, 'SeriesNumber', '0')
    #     series_desc = getattr(ds, 'SeriesDescription', 'Unknown_Series')
    #     series_dir = patient_dir / f"{series_number}_{series_desc.replace(' ', '_')}"
    #     series_dir.mkdir(exist_ok=True)
        
    #     filename = f"{ds.SOPInstanceUID}.dcm"
    #     ds.save_as(series_dir / filename)
        
    #     self.files_received += 1
    #     self.metadata_collector.add_instance(ds)
    #     return 0x0000

    # def _handle_store(self, event):
    #     # On récupère le dataset et les meta
    #     ds = event.dataset
    #     ds.file_meta = event.file_meta # Indispensable pour save_as()
        
    #     filename = f"{ds.SOPInstanceUID}.dcm"
    #     # Utilise write_like_original=False pour forcer la création d'un header valide
    #     ds.save_as(self.temp_dir / filename, write_like_original=False)
        
    #     self.files_received += 1
    #     return 0x0000
    def _handle_store(self, event):
        ds = event.dataset
        ds.file_meta = event.file_meta
        
        patient_id = self.clean_name(getattr(ds, 'PatientID', 'Unknown_Patient'))
        patient_path = self.temp_dir / patient_id
        patient_path.mkdir(exist_ok=True)
        
        filename = f"{ds.SOPInstanceUID}.dcm"
        ds.save_as(patient_path / filename, write_like_original=False)
        
        self.files_received += 1
        return 0x0000


    # def move_data(self, criteria: SearchCriteria, destination_aet=None):
    #     self.current_criteria = criteria
    #     self.files_received = 0
    #     self.ae.maximum_pdu_size = 65536 # Tu peux descendre à 16384 si 0xa702 persiste
        
    #     # 1. Préparation du serveur de réception
    #     handlers = [(evt.EVT_C_STORE, self._handle_store)]
    #     # On utilise un bloc try pour s'assurer que le serveur s'arrête QUOI QU'IL ARRIVE
    #     scp = self.ae.start_server(("192.168.4.163", 106), block=False, evt_handlers=handlers)
        
    #     dest = destination_aet or self.config.CALLING_AET
    #     assoc = self.ae.associate(self.config.HOST, self.config.PORT, ae_title=self.config.CALLED_AET)
        
    #     try:
    #         if assoc.is_established:
    #             ds = Dataset()
    #             ds.QueryRetrieveLevel = criteria.level
    #             ds.StudyInstanceUID = criteria.study_instance_uid or ''
                
    #             if criteria.level == 'SERIES':
    #                 ds.SeriesInstanceUID = criteria.series_instance_uid or ''
                
    #             click.echo(f"I: C-MOVE listening on port 106, Destination: {dest}")

    #             responses = assoc.send_c_move(ds, dest, StudyRootQueryRetrieveInformationModelMove)
                
    #             for (status, identifier) in responses:
    #                 if status:
    #                     # Si Status est 0xa702, on le verra ici
    #                     print(f"I: Move Status: {hex(status.Status)}")
                
    #             assoc.release()
    #         else:
    #             click.echo("E: Association avec Telemis échouée.")

    #     except Exception as e:
    #         click.echo(f"E: Erreur pendant le mouvement: {e}")
        
    #     finally:
    #         scp.shutdown()
    #         sleep(5)

    #     if self.files_received > 0:
    #         self.process_and_sort()
    #         return self.files_received
            
    #     return False

    def move_data(self, criteria: SearchCriteria, destination_aet=None):
        self.current_criteria = criteria
        self.files_received = 0
        
        dest = destination_aet or self.config.CALLING_AET
        assoc = self.ae.associate(self.config.HOST, self.config.PORT, ae_title=self.config.CALLED_AET)
        
        if assoc.is_established:
            ds = Dataset()
            ds.QueryRetrieveLevel = criteria.level
            ds.StudyInstanceUID = criteria.study_instance_uid or ''
            if criteria.level == 'SERIES':
                ds.SeriesInstanceUID = criteria.series_instance_uid or ''
                
            responses = assoc.send_c_move(ds, dest, StudyRootQueryRetrieveInformationModelMove)
            for (status, identifier) in responses:
                if status:
                    print(f"I: Move Status: {hex(status.Status)}")
            assoc.release()
        return self.files_received
            

    def clean_name(self, name):
            """Supprime les caractères interdits pour les dossiers Windows."""
            if not name:
                return "Unknown"
            name = str(name)
            forbidden_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
            for char in forbidden_chars:
                name = name.replace(char, '_')
            return name.strip()

    # def process_and_sort(self):
    #     click.echo(f"I: Tri de {self.files_received} fichiers...")
        
    #     for file_path in self.temp_dir.glob("*.dcm"):
    #         try:
    #             ds = pydicom.dcmread(file_path, force=True)
    #             if not hasattr(ds, 'file_meta') or not ds.file_meta:
    #                 ds.file_meta = pydicom.dataset.FileMetaDataset()
    #         except Exception as e:
    #             click.echo(click.style(f"E: Erreur lecture DICOM {file_path.name}: {e}", fg='red'))
    #             continue

    #         raw_p_id = str(getattr(ds, 'PatientID', 'Unknown')).replace(' ', '_')
    #         p_id = self.clean_name(raw_p_id)
    #         p_dir = self.output_dir / p_id
    #         p_dir.mkdir(exist_ok=True)
            
    #         s_num = getattr(ds, 'SeriesNumber', '0')
            
    #         raw_s_desc = str(getattr(ds, 'SeriesDescription', 'NoDesc')).replace(' ', '_')
    #         s_desc = self.clean_name(raw_s_desc)
    #         s_dir = p_dir / f"{s_num}_{s_desc}"
    #         s_dir.mkdir(exist_ok=True)

    #         if self.current_patient_dir != p_dir:
    #             if self.metadata_collector: self.metadata_collector.save_to_json()
    #             self.current_patient_dir = p_dir
    #             self.metadata_collector = SeriesMetadataCollector(p_dir)
            
    #         self.metadata_collector.add_instance(ds)

    #         file_path.rename(s_dir / file_path.name)

    #     if self.metadata_collector: self.metadata_collector.save_to_json()
    #     self.temp_dir.rmdir()
    #     click.echo("I: Tri terminé et JSON sauvegardé.")

    def final_global_sort(self):
        start_time = time()

        click.echo(click.style("\nBegin sorting...", fg='magenta', bold=True))
        
        all_files = list(self.temp_dir.rglob("*.dcm"))
        total = len(all_files)
        click.echo(f"I: {total} fichiers à traiter.")

        with click.progressbar(all_files, label="Tri en cours") as bar:
            for file_path in bar:
                try:
                    ds = pydicom.dcmread(file_path, force=True)
                    
                    p_id = self.clean_name(getattr(ds, 'PatientID', 'Unknown'))
                    s_num = getattr(ds, 'SeriesNumber', '0')
                    s_desc = self.clean_name(getattr(ds, 'SeriesDescription', 'NoDesc'))
                    
                    # Construction du chemin final : output_dir / PatientID / Series
                    p_dir = self.output_dir / p_id
                    s_dir = p_dir / f"{s_num}_{s_desc}"
                    s_dir.mkdir(parents=True, exist_ok=True)

                    # Gestion des métadonnées JSON par patient
                    if self.current_patient_dir != p_dir:
                        if self.metadata_collector: 
                            self.metadata_collector.save_to_json()
                        self.current_patient_dir = p_dir
                        self.metadata_collector = SeriesMetadataCollector(p_dir)
                    
                    self.metadata_collector.add_instance(ds)

                    destination = s_dir / file_path.name
                    file_path.rename(destination)

                except Exception as e:
                    click.echo(f"\nE: Erreur sur {file_path.name}: {e}")

        if self.metadata_collector: 
            self.metadata_collector.save_to_json()
        
        click.echo(click.style("Globally sorted successfully.", fg='green', bold=True))
        elapsed = time() - start_time
        click.echo(click.style(f"Elapsed time for sorting: {elapsed:.2f} seconds", fg='cyan', bold=True))
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

    def _handle_store(self, event):
        ds = event.dataset
        ds.file_meta = event.file_meta
        
        patient_id = self.clean_name(getattr(ds, 'PatientID', 'Unknown_Patient'))
        patient_path = self.temp_dir / patient_id
        patient_path.mkdir(exist_ok=True, parents=True)
        
        filename = f"{ds.SOPInstanceUID}.dcm"
        ds.save_as(patient_path / filename, enforce_file_format=True)
        
        self.files_received += 1
        return 0x0000


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


    def final_global_sort(self):
        start_time = time()

        click.echo(click.style("\nBegin sorting...", fg='magenta', bold=True))
        
        all_files = list(self.temp_dir.rglob("*.dcm"))
        total = len(all_files)
        click.echo(f"I: {total} fichiers à traiter.")

        with click.progressbar(all_files, label="Sorting..") as bar:
            for file_path in bar:
                try:
                    ds = pydicom.dcmread(file_path, force=True)

                    p_id = self.clean_name(getattr(ds, 'PatientID', 'Unknown'))
                    p_dir = self.output_dir / p_id
                    p_dir.mkdir(parents=True, exist_ok=True)
# ORGANIZED BY SERIES
                        # s_num = getattr(ds, 'SeriesNumber', '0')
                        # s_desc = self.clean_name(getattr(ds, 'SeriesDescription', 'NoDesc'))
                        # s_dir = p_dir / f"{s_num}_{s_desc}"
                        # s_dir.mkdir(parents=True, exist_ok=True)
                        # destination = s_dir / file_path.name
# NOT ORGNIZED BY SERIES
                    destination = p_dir / file_path.name

                    if self.current_patient_dir != p_dir:
                        if self.metadata_collector:
                            self.metadata_collector.save_to_json()
                        self.current_patient_dir = p_dir
                        self.metadata_collector = SeriesMetadataCollector(p_dir)

                    self.metadata_collector.add_instance(ds)

                    file_path.rename(destination)

                except Exception as e:
                    click.echo(f"\nE: Erreur sur {file_path.name}: {e}")

        if self.metadata_collector: 
            self.metadata_collector.save_to_json()
        
        click.echo(click.style("Globally sorted successfully.", fg='green', bold=True))
        elapsed = time() - start_time
        click.echo(click.style(f"Elapsed time for sorting: {elapsed:.2f} seconds", fg='cyan', bold=True))
        for item in self.temp_dir.iterdir():
            if item.is_dir():
                for subitem in item.iterdir():
                    subitem.unlink()
                item.rmdir()

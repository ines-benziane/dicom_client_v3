from pynetdicom import evt
import os
import pydicom
import click
from time import time 
from controllers.pseudonym_controller import PseudonymController
from services.find import Find
from config.server_config import TelemisConfig
from services.move import Move
from services.search_criteria import SearchCriteria
import csv
from cli_options import build_search_criteria
from controllers.pseudonym_controller import PseudonymController

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
BIOMARKERS = [
    "VIBE*CUISSES",
    "VIBE*JAMBES",
    "T2mapping 2D TRA 17Echos CUISSES",
    "T2mapping 2D TRA 17Echos JAMBES"]


from pynetdicom import evt
import os
import pydicom
import click
from controllers.pseudonym_controller import PseudonymController
from services.find import Find
from config.server_config import TelemisConfig
from services.move import Move
from services.search_criteria import SearchCriteria
import csv
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
BIOMARKERS = [
    "VIBE*CUISSES",
    "VIBE*JAMBES",
    "T2mapping 2D TRA 17Echos CUISSES",
    "T2mapping 2D TRA 17Echos JAMBES"
]

# Lock pour le pseudonymizer (si pas thread-safe)
pseudo_lock = Lock()
stats_lock = Lock()

class TransferStats:
    def __init__(self):
        self.total_patients = 0
        self.total_series = 0
        self.total_errors = 0
        self.pseudo_files = 0
        self.pseudo_errors = 0
    
    def increment_series(self):
        with stats_lock:
            self.total_series += 1
    
    def increment_errors(self):
        with stats_lock:
            self.total_errors += 1
    
    def increment_pseudo(self):
        with stats_lock:
            self.pseudo_files += 1
    
    def increment_pseudo_errors(self):
        with stats_lock:
            self.pseudo_errors += 1

@click.command()
@click.option('--file', '-f',  help='CSV Path (Format: PatientID,SeriesDescription)')
def main(file):
    if not os.path.exists(file):
        click.echo(click.style(f" E: File {file} does not exist.", fg='red'))
        return
    
    finder = Find(TelemisConfig)
    mover = Move(TelemisConfig)
    pseudonymizer = PseudonymController()

    handlers = [(evt.EVT_C_STORE, mover._handle_store)]
    scp = mover.ae.start_server(("192.168.4.163", 106), block=False, evt_handlers=handlers)

    try:
        with open(file, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row : continue
                
                p_id = row[0].strip()
                for series_desc in BIOMARKERS:
                    criteria = SearchCriteria(
                        level='SERIES',
                        patient_id=p_id,
                        series_description=series_desc, 
                        research_pseudo=True
                    )
                    results = finder.search_data(criteria)

                    if not results:
                        click.echo(click.style(f" W: Nothing found for {p_id} | Series: {series_desc}", fg='red'))
                        continue
                        
                    for idx, res in enumerate(results, 1):
                        s_uid = getattr(res, 'SeriesInstanceUID', None)
                        std_uid = getattr(res, 'StudyInstanceUID', None)
                        p_id = getattr(res, 'PatientID', 'Unknown')

                        if not s_uid or not std_uid: continue

                        click.echo(f"\n [{idx}/{len(results)}] Transfert Patient: {p_id}")

                        specific_criteria = SearchCriteria(
                            level='SERIES',
                            study_instance_uid=std_uid,
                            series_instance_uid=s_uid,
                            research_pseudo=True
                        )

                        try:
                            mover.move_data(specific_criteria)
                        
                        except Exception as e:
                            click.echo(click.style(f" Error: {e}", fg='red'))
                
    finally:
        scp.shutdown()
        temp_dir = "output_dir/temp_transit"

        if os.path.exists(temp_dir):
            for root, dirs, files in os.walk(temp_dir):
                for filename in files:
                    if filename.startswith('.') or filename == "Thumbs.db":
                        continue

                    file_path = os.path.join(root, filename)
                    file_count += 1
                    try:
                        ds = pydicom.dcmread(file_path)
                        ds = pseudonymizer.pseudonymize_file(ds)
                        ds.save_as(file_path)
                        if file_count % 10 == 0:
                            click.echo(f"Pseudonymized {file_count} files...")
                    except pydicom.errors.InvalidDicomError:
                        continue
                    except Exception as e:
                        click.echo(f" Erreur on {filename}: {e}", fg='red')
    try:
        mover.final_global_sort()
        click.echo("Final sort completed")
    except Exception as e:
        click.echo(f"Final sort failed: {e}")

if __name__ == "__main__":
    main()
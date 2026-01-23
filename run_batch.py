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
    "VIBE_3TE CUISSES",
    "VIBE_3TE JAMBES",
    "T2mapping 2D TRA 17Echos CUISSES",
    "T2mapping 2D TRA 17Echos JAMBES"]

@click.command()
@click.option('--file', '-f',  help='CSV Path (Format: PatientID,SeriesDescription)')
def main(file):

    finder = Find(TelemisConfig)
    mover = Move(TelemisConfig)
    pseudonymizer = PseudonymController()
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
            criteria_kwargs = build_search_criteria(patient_id=p_id, series_description=series_desc, level="SERIES", research_pseudo=True)
            if not criteria_kwargs:
                return  
            criteria = SearchCriteria(patient_id=p_id, series_description=series_desc, level="SERIES", research_pseudo=True)
            if not criteria:
                return
            
            results = finder.search_data(criteria)
            if not results:
                click.echo(click.style(f" W: Nothing found for {p_id} | Series: {series_desc}", fg='red'))
                continue
                
            handlers = [(evt.EVT_C_STORE, mover._handle_store)]
            scp = mover.ae.start_server(("192.168.4.163", 106), block=False, evt_handlers=handlers)
    
            try:
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
                if criteria_kwargs.get('research_pseudo'):
                    temp_dir = "output_dir/temp_transit" 

                    if os.path.exists(temp_dir):
                        for root, dirs, files in os.walk(temp_dir):
                            for filename in files:
                                if filename.startswith('.') or filename == "Thumbs.db":
                                    continue

                                file_path = os.path.join(root, filename)
                                
                                try:
                                    ds = pydicom.dcmread(file_path)
                                    ds = pseudonymizer.pseudonymize_file(ds)
                                    ds.save_as(file_path)
                                except pydicom.errors.InvalidDicomError:
                                    continue
                                except Exception as e:
                                    click.echo(f" Erreur on {filename}: {e}", fg='red')
                mover.final_global_sort()


if __name__ == "__main__":
    main()
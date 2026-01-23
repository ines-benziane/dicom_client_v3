            
import pydicom
import os
import click
from time import  time
from services.find import Find
from services.move import Move
from services.search_criteria import SearchCriteria
from config.server_config import TelemisConfig
from cli_options import common_dicom_options, build_search_criteria
from controllers.pseudonym_controller import PseudonymController

from pynetdicom import evt

@click.command()
@common_dicom_options
def main(**kwargs):
    criteria_kwargs = build_search_criteria(**kwargs)
    if not criteria_kwargs:
        return
    start = time()
    finder = Find(TelemisConfig)
    mover = Move(TelemisConfig)
    pseudonymizer = PseudonymController()

    try:
        criteria = SearchCriteria(**criteria_kwargs)
        results = finder.search_data(criteria)
    except Exception as e:
        click.echo(click.style(f" Error during search: {e}", fg='red'))
        return
    
    if not results:
        click.echo(click.style("No series found.", fg='red'))
        return

    click.echo(click.style(f" {len(results)} series found.", fg='green'))
   
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
                series_instance_uid=s_uid
            )

            try:
                mover.move_data(specific_criteria)
                
            except Exception as e:
                click.echo(click.style(f" Error: {e}", fg='red'))
    
    finally:
        scp.shutdown()
        elapsed = time() - start
        click.echo(click.style(f"\nTotal elapsed time: {elapsed:.2f} seconds", fg='cyan', bold=True))
        click.echo(click.style("Serveur de réception arrêté proprement.", fg='cyan'))
        if criteria_kwargs.get('research_pseudo'):
            click.echo(click.style("Option -rps active : Pseudonymisation en cours...", fg='yellow'))
            temp_dir = "output_dir/temp_transit" 

            if os.path.exists(temp_dir):
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    if os.path.isfile(file_path):
                        try:
                            ds = pydicom.dcmread(file_path)
                            ds = pseudonymizer.pseudonymize_file(ds)
                            ds.save_as(file_path)
                        except Exception as e:
                            click.echo(f" Erreur sur {filename}: {e}", fg='red')
            
            click.echo(click.style("Pseudonymisation terminée.", fg='green'))
        mover.final_global_sort()

if __name__ == "__main__":
    main()
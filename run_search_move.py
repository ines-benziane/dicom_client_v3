import time # Import complet pour éviter l'erreur 'builtin_function'
import click
from time import  time
from services.find import Find
from services.move import Move
from services.search_criteria import SearchCriteria
from config.server_config import TelemisConfig

from pynetdicom import evt

@click.command()
@click.option('--patient-id', default="CL*", help="Pattern PatientID")
@click.option('--date', default="20251110-20251120", help="Plage de dates")
@click.option('--desc', default="VIBE_3TE CUISSES", help="Description de la série")
@click.option('--pause', default=5, help="Pause entre séries")
def main(patient_id, date, desc, pause):
    start = time()
    finder = Find(TelemisConfig)
    mover = Move(TelemisConfig)
    click.echo(click.style(f"Phase 1 : Looking for {patient_id}...", fg='cyan'))
    criteria = SearchCriteria(patient_id=patient_id, study_date=date, series_description=desc, level="SERIES")
    results = finder.search_data(criteria)
    
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
                # time.sleep(2)
                
            except Exception as e:
                click.echo(click.style(f" Error: {e}", fg='red'))
    
    finally:
        scp.shutdown()
        elapsed = time() - start
        click.echo(click.style(f"\nTotal elapsed time: {elapsed:.2f} seconds", fg='cyan', bold=True))
        click.echo(click.style("Serveur de réception arrêté proprement.", fg='cyan'))
        mover.final_global_sort()

if __name__ == "__main__":
    main()
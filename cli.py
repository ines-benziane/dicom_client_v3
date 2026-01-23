import click
from services.find import Find
from config.server_config import TelemisConfig
from services.search_criteria import SearchCriteria
from pynetdicom import debug_logger
from cli_options import common_dicom_options, build_search_criteria
from services.get import Get
from services.move import Move
import time

# debug_logger()

find_service = Find(TelemisConfig)
get_service = Get(TelemisConfig)
move_service = Move(TelemisConfig)

@click.group()
@click.version_option(version='1.0.0', prog_name='Dicom CLI Tool')
def cli():
    """DICOM Client - A command-line tool for managing DICOM files and servers."""
    pass

@cli.command()
@common_dicom_options
def search(**kwargs):  
    """Search for DICOM studies based on provided criteria."""
    start_time = time.time()
    click.echo(click.style("Searching DICOM studies...", fg='cyan', bold=True))

    criteria_kwargs = build_search_criteria(**kwargs)

    if not criteria_kwargs:
        return

    try:
        criteria = SearchCriteria(**criteria_kwargs)
        studies = find_service.search_data(criteria)
    except Exception as e:
        click.echo(click.style(f"Search error: {e}", fg='red', bold=True))
        return

    if not studies:
        click.echo(click.style("No studies found.", fg='red', bold=True))
        return

    click.echo(click.style(f"{len(studies)} study(ies) found.", fg='green', bold=True))
    for idx, study in enumerate(studies, 1):
        click.echo(click.style(f"[{idx}]", fg='green', bold=True) + f" {study}")
        click.echo()
    end_time = time.time()
    elapsed = end_time - start_time
    click.echo(click.style(f"Elapsed time for search: {elapsed:.2f} seconds", fg='cyan', bold=True))

@cli.command()
@common_dicom_options
def get(**kwargs):
    """Retrieve DICOM files based on provided criteria."""
    click.echo(click.style("Retrieving DICOM files...", fg='cyan', bold=True))
    # Build initial search criteria (we will C-FIND at STUDY level to get StudyInstanceUIDs)
    criteria_kwargs, jsonpath2 = build_search_criteria(**kwargs)
    if not criteria_kwargs:
        click.echo(click.style("No criteria provided.", fg='red'))
        return

    criteria = SearchCriteria(**criteria_kwargs)

    try:
        results = find_service.search_data(criteria)
    except Exception as e:
        click.echo(click.style(f"Find error: {e}", fg='red', bold=True))
        return

    if not results:
        click.echo(click.style(f"No {criteria.level.lower()}s found.", fg='red', bold=True))
        return

    if criteria.level == 'STUDY':
        study_uids = []
        for ds in results:
            uid = getattr(ds, 'StudyInstanceUID', None)
            if uid:
                study_uids.append(uid)
        
        click.echo(click.style(f"{len(study_uids)} study(ies) found. Starting retrieval...", fg='green'))

        total_files = 0
        for uid in study_uids:
            click.echo(click.style(f"Retrieving study {uid}...", fg='cyan'))
            sc = SearchCriteria(level='STUDY', study_instance_uid=uid)
            try:
                received = get_service.retrieve_data(sc)
                total_files += int(received)
                click.echo(click.style(f"Received {received} files for study {uid}.", fg='green'))
            except Exception as e:
                click.echo(click.style(f"Error retrieving study {uid}: {e}", fg='red'))
    
    elif criteria.level == 'SERIES':
        series_list = []
        for ds in results:
            study_uid = getattr(ds, 'StudyInstanceUID', None)
            series_uid = getattr(ds, 'SeriesInstanceUID', None)
            if study_uid and series_uid:
                series_list.append((study_uid, series_uid))
        
        click.echo(click.style(f"{len(series_list)} series found. Starting retrieval...", fg='green'))
        
        total_files = 0
        for study_uid, series_uid in series_list:
            click.echo(click.style(f"Retrieving series {series_uid} from study {study_uid}...", fg='cyan'))
            sc = SearchCriteria(level='SERIES', study_instance_uid=study_uid, series_instance_uid=series_uid)
            try:
                received = get_service.retrieve_data(sc)
                total_files += int(received)
                click.echo(click.style(f"Received {received} files for series {series_uid}.", fg='green'))
            except Exception as e:
                click.echo(click.style(f"Error retrieving series {series_uid}: {e}", fg='red'))
    
    else:
        click.echo(click.style(f"Unsupported query level: {criteria.level}", fg='red', bold=True))
        return

    click.echo(click.style(f"Total files retrieved: {total_files}", fg='yellow', bold=True))


move_service = Move(TelemisConfig)

from time import time

@cli.command()
@common_dicom_options
@click.option('--destination', help='Destination AE Title')
def move(destination, **kwargs):
    """Retrieve DICOM files using C-MOVE."""
    start_time = time()
    click.echo(click.style("Phase 1 : Recherche des UIDs (C-FIND)...", fg='cyan'))
    
    criteria_kwargs = build_search_criteria(**kwargs)
    criteria = SearchCriteria(**criteria_kwargs)

    results = find_service.search_data(criteria)
    
    if not results:
        click.echo(click.style("Aucun résultat trouvé pour ces critères.", fg='red'))
        return

    total_moved = 0
    

    for res in results:
        study_uid = getattr(res, 'StudyInstanceUID', None)
        series_uid = getattr(res, 'SeriesInstanceUID', None) # Pour le niveau SERIES

        if criteria.level == 'SERIES' and series_uid:
            click.echo(f"Transfert de la Série : {series_uid}")
            sc = SearchCriteria(
                level='SERIES', 
                study_instance_uid=study_uid, 
                series_instance_uid=series_uid
            )
        else:
            click.echo(f"Transfert de l'Étude : {study_uid}")
            sc = SearchCriteria(level='STUDY', study_instance_uid=study_uid)

        try:
            received = move_service.move_data(sc, destination_aet=destination)
            if received:
                total_moved += int(received)
        except Exception as e:
            click.echo(click.style(f"Error during move: {e}", fg='red'))

    click.echo(click.style(f" Terminé. Total fichiers reçus et triés : {total_moved}", fg='green', bold=True))
    elasped = time() - start_time
    click.echo(click.style(f"Elapsed time for all operation: {elasped:.2f} seconds", fg='cyan', bold=True))

if __name__ == '__main__':
    cli()
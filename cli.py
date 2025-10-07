import click
from services.find import Find
from config.server_config import TelemisConfig
from services.search_criteria import SearchCriteria
from pynetdicom import debug_logger
from cli_options import common_dicom_options, build_search_criteria
from services.get import Get


find_service = Find(TelemisConfig)
get_service = Get(TelemisConfig)

@click.group()
@click.version_option(version='1.0.0', prog_name='Dicom CLI Tool')
def cli():
    """DICOM Client - A command-line tool for managing DICOM files and servers."""
    pass

@cli.command()
@common_dicom_options
def search(level, patient_id, patient_name, study_date, study_description, series_description, accession_number, modality, series_instance_uid, study_instance_uid, patient_birth_date):
    """Search for DICOM studies based on provided criteria."""
    click.echo(click.style("Searching DICOM studies...", fg='cyan', bold=True))

    # Build search criteria dictionary
    criteria_kwargs = build_search_criteria(
        level=level,
        patient_id=patient_id,
        patient_name=patient_name,
        study_date=study_date,
        study_description=study_description,
        series_description=series_description,
        accession_number=accession_number,
        modality=modality,
        series_instance_uid=series_instance_uid,
        study_instance_uid=study_instance_uid,
        patient_birth_date=patient_birth_date,
    )
    if not criteria_kwargs:
        return
    else:
        criteria_kwargs['level'] = level.upper()

    # Perform search
    try:
        criteria = SearchCriteria(**criteria_kwargs)
        studies = find_service.search_data(criteria)
    except Exception as e:
        click.echo(click.style(f"Search error: {e}", fg='red', bold=True))
        return

    if not studies:
        click.echo(click.style("No studies found.", fg='red', bold=True))
        return

    # Display results
    click.echo(click.style(f"{len(studies)} study(ies) found.", fg='green', bold=True))
    for idx, study in enumerate(studies, 1):
        click.echo(click.style(f"[{idx}]", fg='green', bold=True) + f" {study}")
        click.echo()

@cli.command()
@common_dicom_options
def get(**kwargs):
    """Retrieve DICOM files based on provided criteria."""
    click.echo(click.style("Retrieving DICOM files...", fg='cyan', bold=True))
    # Build initial search criteria (we will C-FIND at STUDY level to get StudyInstanceUIDs)
    criteria_kwargs = build_search_criteria(**kwargs)
    if not criteria_kwargs:
        click.echo(click.style("No criteria provided.", fg='red'))
        return

    # Force study-level find
    criteria_kwargs['level'] = 'STUDY'
    criteria = SearchCriteria(**criteria_kwargs)

    # 1) C-FIND to list matching studies
    try:
        studies = find_service.search_data(criteria)
    except Exception as e:
        click.echo(click.style(f"Find error: {e}", fg='red', bold=True))
        return

    if not studies:
        click.echo(click.style("No studies found.", fg='red', bold=True))
        return

    # extract StudyInstanceUIDs from responses (each 'study' is a pydicom Dataset)
    study_uids = []
    for ds in studies:
        uid = getattr(ds, 'StudyInstanceUID', None)
        if uid:
            study_uids.append(uid)

    click.echo(click.style(f"{len(study_uids)} study(ies) found. Starting retrieval...", fg='green'))

    # 2) For each study, perform a C-GET targeted by StudyInstanceUID
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

    click.echo(click.style(f"Total files retrieved: {total_files}", fg='yellow', bold=True))



if __name__ == '__main__':
    cli()
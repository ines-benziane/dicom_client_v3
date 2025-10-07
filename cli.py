import click
from services.find import Find
from config.server_config import TelemisConfig
from services.search_criteria import SearchCriteria
from pynetdicom import debug_logger

find_service = Find(TelemisConfig)

debug_logger()
@click.group()
@click.version_option(version='1.0.0', prog_name='Dicom CLI Tool')
def cli():
    """DICOM Client - A command-line tool for managing DICOM files and servers."""
    pass

@cli.command()
@click.option('--level', '-l', type=click.Choice(['STUDY', 'SERIES', 'IMAGE'], case_sensitive=False), default='STUDY', help='Level of search: STUDY, SERIES, or IMAGE.')
@click.option('--patient-id', '-p', help='Patient ID to search for.')
@click.option('--patient-name', '-n', help='Patient Name to search for.')
@click.option('--study-date', '-d', help='Study Date to search for (YYYYMMDD).')
@click.option('--study-description', '-s', help='Study Description to search for.')
@click.option('--series-description', '-sd', help='Series Description to search for.')
@click.option('--accession-number', '-a', help='Accession Number to search for.')
@click.option('--modality', '-m', help='Modality to search for (e.g., CT, MR).')
@click.option('--series-instance-uid', '-seiu', help='Series Instance UID to search for.')
@click.option('--study-instance-uid', '-stui', help='Study Instance UID to search for.')
@click.option('--patient-birth-date', '-bd', help='Patient Birth Date to search for (YYYYMMDD).')
def search(level, patient_id, patient_name, study_date, study_description, series_description, accession_number, modality, series_instance_uid, study_instance_uid, patient_birth_date):
    """Search for DICOM studies based on provided criteria."""
    click.echo(click.style("Searching DICOM studies...", fg='cyan', bold=True))

    # Build search criteria dictionary
    criteria_map = {
        'level': level,
        'patient_id': patient_id,
        'patient_name': patient_name,
        'study_date': study_date,
        'study_description': study_description,
        'series_description': series_description,
        'accession_number': accession_number,
        'modality': modality,
        'series_instance_uid': series_instance_uid,
        'study_instance_uid': study_instance_uid,
        'patient_birth_date': patient_birth_date
    }
    criteria_kwargs = {k: v for k, v in criteria_map.items() if v is not None}
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


if __name__ == '__main__':
    cli()
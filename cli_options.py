import click
from functools import wraps

def common_dicom_options(f):
    """Decorator to add common DICOM options to CLI commands."""
    options = [
        click.option('--level', '-l', type=click.Choice(['STUDY', 'SERIES', 'IMAGE'], case_sensitive=False), default='STUDY', help='Level of search: STUDY, SERIES, or IMAGE.'),
        click.option('--patient-id', '-p', help='Patient ID to search for.'),
        click.option('--patient-name', '-n', help='Patient Name to search for.'),
        click.option('--study-date', '-d', help='Study Date to search for (YYYYMMDD).'),
        click.option('--study-description', '-s', help='Study Description to search for.'),
        click.option('--series-description', '-sd', help='Series Description to search for.'),
        click.option('--accession-number', '-a', help='Accession Number to search for.'),
        click.option('--modality', '-m', help='Modality to search for (e.g., CT, MR).'),
        click.option('--series-instance-uid', '-seiu', help='Series Instance UID to search for.'),
        click.option('--study-instance-uid', '-stui', help='Study Instance UID to search for.'),
        click.option('--patient-birth-date', '-bd', help='Patient Birth Date to search for (YYYYMMDD).'),
    ]

    for option in reversed(options):
        f = option(f)
    return f

def build_search_criteria(**kwargs):
    """Build a dictionary of search criteria from provided keyword arguments."""
    criteria = {k: v for k, v in kwargs.items() if v is not None}
    if 'level' in criteria:
        criteria['level'] = criteria['level'].upper()
    return criteria
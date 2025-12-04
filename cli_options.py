import click
from functools import wraps

def common_dicom_options(f):
    """Decorator to add common DICOM options to CLI commands."""
    options = [
        click.option('--level', '-l', type=click.Choice(['STUDY', 'SERIES', 'IMAGE'], case_sensitive=False), default='STUDY', help='Level of search: STUDY, SERIES, or IMAGE.'),
        click.option('--patient-id', '-p', help='Patient ID to search for. Example : -p"CL*"'),
        click.option('--patient-name', '-n', help='Patient Name to search for. Example : -n"Benziane Ines"'),
        click.option('--study-date', '-d', help='Study Date to search for (YYYYMMDD).'),
        click.option('--series-date', '-sda', help='Series Date to search for (YYYYMMDD).'),
        click.option('--study-description', '-s', help='Study Description to search for.'),
        click.option('--series-description', '-sde', help='Series Description to search for.'),
        click.option('--accession-number', '-a', help='Accession Number to search for.'),
        click.option('--modality', '-m', help='Modality to search for (e.g., CT, MR).'),
        click.option('--series-instance-uid', '-seui', help='Series Instance UID to search for.'),
        click.option('--study-instance-uid', '-stui', help='Study Instance UID to search for.'),
        click.option('--patient-birth-date', '-bd', help='Patient Birth Date to search for (YYYYMMDD).'),
        # click.option('--json-series-number-file', '-jsnf', help='Path to JSON file containing series numbers.'),
        click.option('--number-of-study-related-instances', '-nsri', help='Number of Study Related Instances to search for.'),
        click.option('--clinical-pseudo', '-cps', is_flag=True, help='Enable clinical pseudonymization of patient data.'),
        click.option('--research-pseudo', '-rps', is_flag=True, help='Enable research pseudonymization of patient data.'),
        click.option('--protocol-pseudo', '-pps', is_flag=True, help='Enable protocol pseudonymization of patient data.'),
        click.option('--anonymize', '-an', is_flag=True, help='Anonymize patient data by removing name, age, sex while preserving Patient ID.')
    ]

    for option in reversed(options):
        f = option(f)
    return f

def build_search_criteria(**kwargs):
    """Build a dictionary of search criteria from provided keyword arguments."""
    json_file = kwargs.pop('json_series_number_file', None)

    criteria = {k: v for k, v in kwargs.items() if v is not None}
    criteria.setdefault('level', 'STUDY')
    if 'level' in criteria:
        criteria['level'] = criteria['level'].upper()
    return criteria, json_file
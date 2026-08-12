from datetime import datetime
import threading
import csv
import os

PSEUDONYM_PREFIX = "PAT"
CSV_FIELDNAMES = ['pseudonym', 'patient_name', 'patient_ID', 'birth_date', 'sex']
DEFAULT_CSV_PATH = "mappings.csv"

mapping_lock = threading.Lock()

def get_patient_field(ds, field_name, default="N/A"):
    """Retrieve a field from the dataset, returning a default if not present."""
    if hasattr(ds, field_name):
        return str(getattr(ds, field_name))
    return default

def empty_data(ds):
    """Erase sensitive patient data from the dataset."""
    fields_to_clear = ['PatientBirthDate', 'PatientSex']
    for field in fields_to_clear:
        if hasattr(ds, field):
            setattr(ds, field, '')

def patient_exists(mappings, patient_ID):
    """Check if a patient_ID exists in the mappings."""
    return patient_ID in mappings

def add_patient(csv_path, pseudo,original_id, original_sex):
    """Add a new patient mapping to the CSV file."""
    try:
        file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
        with open(csv_path, 'a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDNAMES, delimiter=';')
            if not file_exists:
                    writer.writeheader()

            writer.writerow({
                'pseudonym':pseudo,
                'patient_ID' : original_id,
                'sex': original_sex
            })
    except (IOError, OSError, PermissionError) as e:
        raise RuntimeError(f"Cannot write to mapping file {csv_path}: {e}")
    
# def create_patient_key(patient_ID, birth_date):
#     return f"{patient_ID}|{birth_date}"

def read_mappings(csv_path=DEFAULT_CSV_PATH) -> dict:
    """Read existing patient mappings from the CSV file."""
    mappings = {}
    if not os.path.exists(csv_path):
        return mappings
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter=';')

            for line in reader:
                if 'patient_ID' not in line or 'pseudonym' not in line or 'birth_date' not in line:
                    raise ValueError(f"CSV malformed: missing required columns in {csv_path}")
                
                patient_id = line['patient_ID']
                mappings[patient_id] = {
                "pseudonym": line['pseudonym'],
                "sex": line.get('sex', 'N/A')
            }
            return mappings
    except (IOError, UnicodeDecodeError, PermissionError) as e:
        raise RuntimeError(f"Cannot read mapping file {csv_path}: {e}")
    except csv.Error as e:
        raise ValueError(f"CSV format error in {csv_path}: {e}")
    
def initialize_data(ds) -> tuple:
    original_name = get_patient_field(ds, 'PatientName')
    original_id = get_patient_field(ds, 'PatientID')
    original_birth_date = get_patient_field(ds, 'PatientBirthDate')
    original_sex = get_patient_field(ds, 'PatientSex')
    return original_name, original_id, original_birth_date, original_sex

def add_mapping(ds, csv_path=DEFAULT_CSV_PATH) :
    """Returns pseudonymized dataset"""
    if not hasattr(ds, 'PatientID'):
        return ds
    original_name, original_id, original_birth_date, original_sex = initialize_data(ds)
    with mapping_lock:
        mappings = read_mappings(csv_path)
        if patient_exists(mappings, original_id):
            pseudo = mappings[original_id]["pseudonym"]
        else:
            count = len(mappings)
            pseudo = f"{PSEUDONYM_PREFIX}_{count+1:04d}"
            
            add_patient(csv_path, pseudo, original_id, original_sex)
    ds.PatientName = pseudo
    empty_data(ds)
    return ds

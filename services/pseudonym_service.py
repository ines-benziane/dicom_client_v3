from datetime import datetime
import csv
import os

PSEUDONYM_PREFIX = "PAT"
CSV_FIELDNAMES = ['pseudonym', 'patient_name', 'patient_ID', 'birth_date', 'sex']
DEFAULT_CSV_PATH = "mappings.csv"

def create_patient_key(patient_name, birth_date):
    return f"{patient_name}|{birth_date}"

def read_mappings(csv_path=DEFAULT_CSV_PATH) -> dict:
    mappings = {}
    if not os.path.exists(csv_path):
        return mappings
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter=';')

            for line in reader:
                if 'patient_name' not in line or 'pseudonym' not in line or 'birth_date' not in line:
                    raise ValueError(f"CSV malformed: missing required columns in {csv_path}")
                
                key = create_patient_key(line['patient_name'], line['birth_date'])
                mappings[key] = {
                "pseudonym": line['pseudonym'],
                "birth_date": line['birth_date'], 
                "sex": line['sex']
            }
            return mappings
    except (IOError, UnicodeDecodeError, PermissionError) as e:
        raise RuntimeError(f"Cannot read mapping file {csv_path}: {e}")
    except csv.Error as e:
        raise ValueError(f"CSV format error in {csv_path}: {e}")

def get_patient_field(ds, field_name, default="N/A"):
    if hasattr(ds, field_name):
        return str(getattr(ds, field_name))
    return default

def initialize_data(ds) -> tuple:
    original_name = get_patient_field(ds, 'PatientName')
    original_id = get_patient_field(ds, 'PatientID')
    original_birth_date = get_patient_field(ds, 'PatientBirthDate')
    original_sex = get_patient_field(ds, 'PatientSex')
    return original_name, original_id, original_birth_date, original_sex

def empty_data(ds):
    fields_to_clear = ['PatientBirthDate', 'PatientSex']
    for field in fields_to_clear:
        if hasattr(ds, field):
            setattr(ds, field, '')

def patient_exists(mappings, patient_name):
    return patient_name in mappings

def add_patient(csv_path, pseudo,original_name,original_id,original_birth_date,original_sex):
    try:
        with open(csv_path, 'a', newline='', encoding='utf-8') as file:
            fieldnames = CSV_FIELDNAMES

            writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
            if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
                    writer.writeheader()
            writer.writerow({
                'pseudonym':pseudo,
                'patient_name': original_name,
                'patient_ID' : original_id,
                'birth_date' : original_birth_date,
                'sex': original_sex
            })
    except (IOError, OSError, PermissionError) as e:
        raise RuntimeError(f"Cannot write to mapping file {csv_path}: {e}")

def add_mapping(ds, csv_path=DEFAULT_CSV_PATH) :
    """Returns pseudonymized dataset"""
    if not hasattr(ds, 'PatientName'):
        return ds
    original_name, original_id, original_birth_date, original_sex = initialize_data(ds)
    mappings = read_mappings(csv_path)
    key = create_patient_key(original_name, original_birth_date)
    if patient_exists(mappings, key):
        ds.PatientName = mappings[key]["pseudonym"]
        empty_data(ds)
        return ds
    count = len(mappings) 
    pseudo = f"{PSEUDONYM_PREFIX}_{count+1:04d}"
    add_patient(csv_path, pseudo, original_name, original_id, original_birth_date, original_sex)
    ds.PatientName = pseudo
    empty_data(ds)
    return ds

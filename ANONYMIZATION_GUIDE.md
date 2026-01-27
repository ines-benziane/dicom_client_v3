<!-- # DICOM Anonymization Feature

## Overview
This feature allows you to anonymize DICOM files during retrieval by removing patient demographic information while preserving the Patient ID for file organization purposes.

## Usage

To retrieve DICOM files with anonymization enabled, add the `--anonymize-data` flag to your `get` command:

```powershell
dicom-client get --patient-name "fromes yves" --study-date "20120606" --anonymize-data
```

## What Gets Removed

When `--anonymize-data` is used, the following DICOM tags are removed from the retrieved files:
Anonymze data is a work in progress

- **PatientName** - Patient's full name
- **PatientBirthDate** - Date of birth
- **PatientSex** - Patient's sex
- **PatientAge** - Patient's age
- **PatientWeight** - Patient's weight
- **PatientSize** - Patient's size/height
- **OtherPatientIDs** - Additional patient identifiers
- **OtherPatientNames** - Additional patient names
- **EthnicGroup** - Patient's ethnicity
- **PatientComments** - Comments about the patient
- **PatientAddress** - Patient's address
- **PatientTelephoneNumbers** - Patient's phone numbers
- **PatientMotherBirthName** - Mother's maiden name
- **MilitaryRank** - Military information
- **BranchOfService** - Military service branch
- **MedicalRecordLocator** - Medical record location
- **ReferencedPatientSequence** - Patient reference sequences
- **ResponsiblePerson** - Responsible person information
- **ResponsiblePersonRole** - Role of responsible person
- **ResponsibleOrganization** - Responsible organization

## What Gets Preserved

- **PatientID** - This is preserved to maintain file organization structure
- **All imaging data** - The actual DICOM images remain unchanged
- **Study and Series metadata** - Study dates, descriptions, modalities, etc.

## File Organization

Files are still organized by Patient ID in the same folder structure:

```
output_dir/
├── {PatientID}/
│   ├── {SeriesNumber}_{SeriesDescription}/
│   │   ├── {SOPInstanceUID}.dcm
│   │   └── ...
│   └── metadata.json
```

The Patient ID remains in the DICOM headers and is used for folder naming.

## Implementation Details

The anonymization is performed by the `anonymize_dataset()` function in `services/anonym_service.py`. This function:

1. Takes a pydicom Dataset as input
2. Iterates through the list of demographic tags
3. Removes each tag if it exists in the dataset
4. Returns the modified dataset


## Example Commands

### Retrieve all studies for a patient with anonymization
```powershell
dicom-client get --patient-name "Doe John" --anonymize-data
```

### Retrieve specific study date with anonymization
```powershell
dicom-client get --study-date "20230101" --anonymize-data
```

### Retrieve at SERIES level with anonymization
```powershell
dicom-client get --level SERIES --patient-id "12345" --anonymize-data
```

### Combine with other options
```powershell
dicom-client get --patient-name "Smith*" --modality "MR" --study-date "20230101-20231231" --anonymize-data
```

## Notes

- Anonymization happens during file retrieval, not during search (C-FIND)
- The Patient ID is intentionally preserved for file organization
- If you need to remove the Patient ID as well, you would need to modify the `anonymize_dataset()` function in `services/anonym_service.py`
- The JSON metadata file will still contain the Patient ID for organization purposes -->

# DICOM CLI Tool

A command-line tool for managing DICOM files and servers.

## Installation

### Development installation
```bash
pip install -e .
```

### Installation from source
```bash
pip install .
```

## Usage

After installation, you can use the tool with the following commands:

```bash
# Using the full name
dicom-client search --patient-name="Patient Name"


### Command examples

```bash
# Search by patient name
dicom-client search --patient-name="Benziane Ines"

# Search by patient ID
dicom-client search --patient-id="CL*"

dicom-client search -p"CL*"

# Search by study date
dicom-client search --study-date="20231001"

# Search with multiple criteria
dicom-client search --patient-name="Benziane" --modality="CT" --study-date="20231001"

# Search at series level
dicom-client search --level="SERIES" --patient-name="Benziane"
```

### Available options

- `--level, -l`: Search level (STUDY, SERIES, IMAGE) - default: STUDY
- `--patient-id, -p`: Patient ID
- `--patient-name, -n`: Patient name
- `--study-date, -d`: Study date (YYYYMMDD)
- `--study-description, -s`: Study description
- `--series-description, -sd`: Series description
- `--accession-number, -a`: Accession number
- `--modality, -m`: Modality (e.g., CT, MR)
- `--series-instance-uid, seiu` : Series Instance UID
- `--study-instance-uid, stui` : Study Instance UID

## Configuration

DICOM server configuration is located in `config/server_config.py`.

## Development

### Project structure
```
dicom_client_v2/
├── cli.py                 # CLI entry point
├── config/
│   └── server_config.py   # Server configuration
├── controllers/
│   ├── find_controller.py
│   ├── get_controller.py
│   ├── move_controller.py
│   ├──anonym_controller.py
│   ├──batch_controller.py
│   ├──pseudonym_controller.py
├── services/
│   ├── find.py           # DICOM search service
│   ├── get.py
│   ├── get.py
│   ├── json_file.py
│   ├── pseudonym_service.py
│   └── search_criteria.py # Search criteria
├── setup.py              # Installation configuration
├── run_process_v2.py
├── mappings.csv
└── requirements.txt      # Dependencies
```

## License

MIT License
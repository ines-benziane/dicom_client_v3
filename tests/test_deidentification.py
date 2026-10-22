"""De-identification of received DICOM files: anonymization and research pseudonymization."""

import csv

from dicom.controllers.anonym_controller import AnonymController
from dicom.controllers.pseudonym_controller import PseudonymController
from dicom.services.anonym_service import anonymize_dataset

from conftest import make_dataset


# --- anonymization ------------------------------------------------------------

def test_anonymization_removes_demographics(dataset):
    dataset.PatientAddress = "1 rue X"
    dataset.OtherPatientIDs = "OLD-ID"
    dataset.PatientComments = "note"

    anonymize_dataset(dataset)

    for tag in ("PatientName", "PatientBirthDate", "PatientSex", "PatientAge",
                "PatientAddress", "OtherPatientIDs", "PatientComments"):
        assert tag not in dataset, tag


def test_anonymization_keeps_patient_id_for_file_organisation(dataset):
    anonymize_dataset(dataset)

    assert dataset.PatientID == "CL0TEST"


def test_anonymization_tolerates_missing_tags():
    ds = make_dataset()
    del ds.PatientAge

    AnonymController().anonymize_file(ds)

    assert "PatientName" not in ds


# --- research pseudonymization -----------------------------------------------

def _pseudo(tmp_path):
    return PseudonymController(csv_path=tmp_path / "mappings.csv")


def test_name_replaced_by_pseudonym(tmp_path, dataset):
    ds = _pseudo(tmp_path).pseudonymize_file(dataset)

    assert str(ds.PatientName) == "PAT_0001"


def test_birth_date_and_sex_emptied(tmp_path, dataset):
    ds = _pseudo(tmp_path).pseudonymize_file(dataset)

    assert (ds.PatientBirthDate, ds.PatientSex) == ("", "")


def test_same_patient_always_gets_the_same_pseudonym(tmp_path):
    controller = _pseudo(tmp_path)
    first = controller.pseudonymize_file(make_dataset(patient_id="A"))
    second = controller.pseudonymize_file(make_dataset(patient_id="A"))

    assert str(first.PatientName) == str(second.PatientName) == "PAT_0001"


def test_new_patient_gets_the_next_pseudonym(tmp_path):
    controller = _pseudo(tmp_path)
    controller.pseudonymize_file(make_dataset(patient_id="A"))
    second = controller.pseudonymize_file(make_dataset(patient_id="B"))

    assert str(second.PatientName) == "PAT_0002"


def test_mapping_survives_a_new_run(tmp_path):
    """The mapping file is the memory: a later run must reuse it."""
    _pseudo(tmp_path).pseudonymize_file(make_dataset(patient_id="A"))
    later = _pseudo(tmp_path).pseudonymize_file(make_dataset(patient_id="A"))

    assert str(later.PatientName) == "PAT_0001"


def test_mapping_file_links_pseudonym_to_patient_id_without_name(tmp_path, dataset):
    _pseudo(tmp_path).pseudonymize_file(dataset)

    with open(tmp_path / "mappings.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    assert [(r["pseudonym"], r["patient_ID"]) for r in rows] == [("PAT_0001", "CL0TEST")]
    assert "Doe" not in (tmp_path / "mappings.csv").read_text(encoding="utf-8")


def test_research_pseudonymization_keeps_patient_id(tmp_path, dataset):
    """Current behaviour, to be confirmed: PatientID is NOT replaced (it is the mapping key).
    If the site's PatientID can identify a person, the files are not de-identified."""
    ds = _pseudo(tmp_path).pseudonymize_file(dataset)

    assert ds.PatientID == "CL0TEST"


def test_dataset_without_patient_id_left_untouched(tmp_path, dataset):
    del dataset.PatientID

    ds = _pseudo(tmp_path).pseudonymize_file(dataset)

    assert str(ds.PatientName) == "Doe^John"
    assert not (tmp_path / "mappings.csv").exists()

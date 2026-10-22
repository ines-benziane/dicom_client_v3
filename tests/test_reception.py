"""After transfer: sorting received files into patient/series folders, series_metadata.json,
and reading the patient list."""

import json

import pandas as pd
import pytest

from dicom.run_process import load_patient_ids
from dicom.run_select_series import write_series_metadata
from dicom.services.move import Move

from conftest import make_dataset


class FakeConfig:
    CALLING_AET = "TEST-AET"


@pytest.fixture
def mover(tmp_path):
    return Move(FakeConfig, output_dir=tmp_path / "out")


def _receive(mover, *datasets):
    """Simulate files received in temp_transit, as _handle_store writes them."""
    for ds in datasets:
        folder = mover.temp_dir / mover.clean_name(ds.PatientID)
        folder.mkdir(parents=True, exist_ok=True)
        ds.save_as(folder / f"{ds.SOPInstanceUID}.dcm", enforce_file_format=True)


@pytest.mark.parametrize("raw, expected", [
    ("CL2LD260112", "CL2LD260112"),
    ("A/B:C*D?", "A_B_C_D_"),
    ("  X  ", "X"),
    ("", "Unknown"),
])
def test_clean_name_makes_valid_folder_names(mover, raw, expected):
    assert mover.clean_name(raw) == expected


def test_files_sorted_by_patient_then_series(mover):
    _receive(mover,
             make_dataset("P1", 17, "VIBE_3TE JAMBES"), make_dataset("P1", 17, "VIBE_3TE JAMBES"),
             make_dataset("P1", 19, "T2mapping 2D TRA 17Echos CUISSES"),
             make_dataset("P2", 2, "T1_TRA_TSE"))

    mover.final_global_sort()

    out = mover.output_dir
    assert len(list((out / "P1" / "17_VIBE_3TE JAMBES").glob("*.dcm"))) == 2
    assert len(list((out / "P1" / "19_T2mapping 2D TRA 17Echos CUISSES").glob("*.dcm"))) == 1
    assert len(list((out / "P2" / "2_T1_TRA_TSE").glob("*.dcm"))) == 1


def test_no_file_left_in_transit_after_sort(mover):
    _receive(mover, make_dataset("P1"))

    mover.final_global_sort()

    assert not any(mover.temp_dir.rglob("*.dcm"))


def test_series_metadata_lists_received_series(mover):
    _receive(mover, make_dataset("P1", 19), make_dataset("P1", 2), make_dataset("P1", 3))
    mover.final_global_sort()

    write_series_metadata([mover.output_dir / "P1"])

    data = json.loads((mover.output_dir / "P1" / "series_metadata.json").read_text(encoding="utf-8"))
    assert data == {"PatientID": "P1", "SeriesNumber": [2, 3, 19]}


# --- patient list file --------------------------------------------------------

def test_patient_ids_from_first_column_header_skipped(tmp_path):
    path = tmp_path / "patients.xlsx"
    pd.DataFrame({"Mes patients": [" CL1 ", None, "CL2"], "notes": ["a", "b", "c"]}).to_excel(path, index=False)

    assert load_patient_ids(str(path)) == ["CL1", "CL2"]


def test_patient_ids_from_csv_with_semicolon(tmp_path):
    path = tmp_path / "patients.csv"
    path.write_text("PatientID;notes\nCL1;a\nCL2;b\n", encoding="utf-8")

    assert load_patient_ids(str(path)) == ["CL1", "CL2"]


def test_unsupported_patient_file_rejected(tmp_path):
    path = tmp_path / "patients.txt"
    path.write_text("CL1\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_patient_ids(str(path))

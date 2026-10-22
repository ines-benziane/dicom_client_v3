"""What is asked to the PACS (C-FIND query) and which series are kept before transfer."""

import pytest
from pydicom.dataset import Dataset

from dicom.cli_options import build_search_criteria
from dicom.run_select_series import select_series
from dicom.services.find import Find
from dicom.services.search_criteria import SearchCriteria


class FakeConfig:
    CALLING_AET = "TEST-AET"
    HOST, PORT, CALLED_AET = "127.0.0.1", 0, "NONE"


# --- CLI criteria ----------------------------------------------------------------

def test_criteria_keep_only_given_options():
    criteria = build_search_criteria(patient_id="CL*", patient_name=None, level="series")

    assert criteria == {"patient_id": "CL*", "level": "SERIES"}


def test_default_level_is_study():
    assert build_search_criteria(patient_id="CL*")["level"] == "STUDY"


# --- C-FIND query --------------------------------------------------------------

def _query(level, **criteria):
    return Find(FakeConfig)._build_query_dataset(SearchCriteria(level=level, **criteria), level)


def test_series_query_carries_filters():
    ds = _query("SERIES", patient_id="CL2LD260112", series_description="T1*TRA*TSE*")

    assert (ds.PatientID, ds.SeriesDescription) == ("CL2LD260112", "T1*TRA*TSE*")


def test_series_query_asks_for_dates_and_numbers():
    """Empty attributes are 'return keys': the PACS must send them back for the selection step."""
    ds = _query("SERIES", patient_id="X")

    for tag in ("SeriesDate", "SeriesTime", "SeriesNumber", "SeriesInstanceUID", "StudyDate"):
        assert tag in ds, tag


def test_study_query_has_no_series_attributes():
    ds = _query("STUDY", patient_id="X")

    assert "SeriesDescription" not in ds


# --- series selection (run_select_series) ----------------------------------------

def _series(date, time="", number=1, study_date=None):
    ds = Dataset()
    ds.SeriesDate, ds.SeriesTime, ds.SeriesNumber = date, time, number
    ds.StudyDate = study_date if study_date is not None else date
    return ds


SERIES = [_series("20230101", "100000", 5), _series("20190611", "090000", 3),
          _series("20190611", "080000", 2), _series("20250301", "110000", 7)]


def _dates(selected):
    return [(s.SeriesDate, s.SeriesTime) for s in selected]


def test_earliest_two_in_chronological_order():
    assert _dates(select_series(SERIES, "earliest", 2)) == [("20190611", "080000"), ("20190611", "090000")]


def test_latest_one():
    assert _dates(select_series(SERIES, "latest", 1)) == [("20250301", "110000")]


def test_undated_series_are_never_selected():
    selected = select_series(SERIES + [_series("", study_date="")], "earliest", 1)

    assert _dates(selected) == [("20190611", "080000")]


def test_study_date_used_when_series_date_missing():
    selected = select_series([_series("", study_date="20100101"), _series("20200101")], "earliest", 1)

    assert selected[0].StudyDate == "20100101"


def test_asking_more_than_available_returns_all():
    assert len(select_series(SERIES, "earliest", 10)) == 4


def test_unknown_order_rejected():
    with pytest.raises(ValueError):
        select_series(SERIES, "middle", 1)

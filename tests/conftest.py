import pytest
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, MRImageStorage, generate_uid


def make_dataset(patient_id="CL0TEST", series_number=17, series_description="VIBE_3TE JAMBES",
                 **tags):
    """A small, valid MR DICOM dataset with patient demographics filled in."""
    ds = Dataset()
    ds.file_meta = FileMetaDataset()
    ds.file_meta.MediaStorageSOPClassUID = MRImageStorage
    ds.file_meta.MediaStorageSOPInstanceUID = generate_uid()
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.SOPClassUID = MRImageStorage
    ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
    ds.PatientID = patient_id
    ds.PatientName = "Doe^John"
    ds.PatientBirthDate = "19800101"
    ds.PatientSex = "M"
    ds.PatientAge = "045Y"
    ds.SeriesNumber = series_number
    ds.SeriesDescription = series_description
    for name, value in tags.items():
        setattr(ds, name, value)
    return ds


@pytest.fixture
def dataset():
    return make_dataset()

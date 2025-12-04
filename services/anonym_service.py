"""
DICOM Anonymization Service

This module provides functions to anonymize DICOM datasets by removing
patient demographic information while preserving the Patient ID for
file organization purposes.
"""

from pydicom import Dataset


def anonymize_dataset(ds):
    """
    Anonymize a DICOM dataset by removing patient demographic information.
    
    Preserves:
    - PatientID (0010,0020)
    
    Removes:
    - PatientName
    - PatientAge
    - PatientSex
    - PatientBirthDate
    - other demographic information
    
    Args:
        ds: pydicom Dataset to anonymize
        
    Returns:
        The modified Dataset (note: modification is done in-place)
    """
    # List of DICOM tags to remove with their hex codes
    # Using tag numbers ensures proper deletion
    tags_to_remove = [
        0x00100010,  # PatientName
        0x00100030,  # PatientBirthDate
        0x00100040,  # PatientSex
        0x00101010,  # PatientAge
        0x00101030,  # PatientWeig
        0x00101000,  # OtherPatientIDs
        0x00101001,  # OtherPatientNames
        0x00102160,  # EthnicGroup
        0x00104000,  # PatientComments
        0x00101040,  # PatientAddress
        0x00102154,  # PatientTelephoneNumbers
        0x00101060,  # PatientMotherBirthName
        0x00101080,  # MilitaryRank
        0x00101081,  # BranchOfService
        0x00101090,  # MedicalRecordLocator
        0x00081120,  # ReferencedPatientSequence
        0x00102297,  # ResponsiblePerson
        0x00102298,  # ResponsiblePersonRole
        0x00102299,  # ResponsibleOrganization
    ]
    
    # Remove tags if they exist
    for tag in tags_to_remove:
        if tag in ds:
            del ds[tag]
    
    return ds

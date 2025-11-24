import json
from pathlib import Path
from typing import Dict, Any

class SeriesMetadataCollector:
    """Collect and save metadata about DICOM series during C-GET operations"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.series_metadata: Dict[str, Dict[str, Any]] = {}
    
    def add_instance(self, dataset):
        """Add metadata from a DICOM instance to the collection"""
        # Extract required fields with fallbacks
        print("Adding instance metadata...")
        patient_id = getattr(dataset, 'PatientID', 'Unknown')
        series_number = str(getattr(dataset, 'SeriesNumber', 'Unknown'))
        series_desc = getattr(dataset, 'SeriesDescription', 'Unknown')
        study_instance_uid = getattr(dataset, 'StudyInstanceUID', 'Unknown')
        series_instance_uid = getattr(dataset, 'SeriesInstanceUID', 'Unknown')
        
        # Create unique key for this series
        series_key = f"{series_number}_SE_{series_desc}"
        
        # Initialize or update series entry
        if series_key not in self.series_metadata:
            self.series_metadata[series_key] = {
                "PatientID": patient_id,
                "SeriesNumber": series_number,
                "SeriesDescription": series_desc,
                "StudyInstanceUID": study_instance_uid,
                "SeriesInstanceUID": series_instance_uid,
                "NumberOfInstances": 0
            }
        
        self.series_metadata[series_key]["NumberOfInstances"] += 1
    
    def save_to_json(self, filename: str = "series_metadata.json"):
        """Save collected metadata to a JSON file"""
        json_path = self.output_dir / filename
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.series_metadata, f, indent=2, ensure_ascii=False)
        print(f"I: Metadata saved to {json_path}")
        return json_path
    
    def reset(self):
        """Clear collected metadata"""
        self.series_metadata.clear()
        
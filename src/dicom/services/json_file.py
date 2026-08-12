import json
from pathlib import Path
from typing import Dict, Any, List

class SeriesMetadataCollector:
    """Collect and save metadata about DICOM series during C-GET operations"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.patient_id = None
        self.series_numbers: List[int] = []
    
    def add_instance(self, dataset):
        """Add metadata from a DICOM instance to the collection"""
        # Extract required fields with fallbacks
        patient_id = getattr(dataset, 'PatientID', 'Unknown')
        series_number = getattr(dataset, 'SeriesNumber', None)
        
        
        # Set patient ID (should be the same for all instances in this collector)
        if self.patient_id is None:
            self.patient_id = patient_id
        
        # Add series number if not already in list
        if series_number is not None and series_number not in self.series_numbers:
            self.series_numbers.append(series_number)
    
    def save_to_json(self, filename: str = "series_metadata.json"):
        """Save collected metadata to a JSON file"""
        # Sort series numbers for cleaner output
        self.series_numbers.sort()
        
        output_data = {
            "PatientID": self.patient_id or "Unknown",
            "SeriesNumber": self.series_numbers
        }
        
        json_path = self.output_dir / filename
        with open(json_path, 'w', encoding='utf-8') as f:
            # Use separators to avoid extra whitespace
            json.dump(output_data, f, indent=2, ensure_ascii=False, separators=(',', ': '))
        print(f"I: Metadata saved to {json_path}")
        return json_path
    
    def reset(self):
        """Clear collected metadata"""
        self.patient_id = None
        self.series_numbers.clear()
        
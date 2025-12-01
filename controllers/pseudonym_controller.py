from services.pseudonym_service import add_mapping, DEFAULT_CSV_PATH

class PseudonymController :
    def __init__ (self, csv_path=DEFAULT_CSV_PATH):
        self.csv_path = csv_path
    
    def pseudonymize_file(self, ds):
        return add_mapping(ds, self.csv_path)

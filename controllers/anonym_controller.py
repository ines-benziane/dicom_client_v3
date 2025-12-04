from services.anonym_service import anonymize_dataset

class AnonymController :
    def __init__ (self):
        pass
    
    def anonymize_file(self, ds):
        # return add_mapping(ds, self.csv_path)
        return anonymize_dataset(ds)

import os
import csv
import click
import logging
import pydicom
import pandas as pd
from threading import Lock
from pynetdicom import evt
from pydicom.errors import InvalidDicomError
from config.server_config import TelemisConfig
from config.user_config import UserConfig
from services.find import Find
from services.move import Move
from services.search_criteria import SearchCriteria
from controllers.pseudonym_controller import PseudonymController
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
BIOMARKERS = [
    "VIBE*CUISSES",
    "VIBE*JAMBES",
    "T2mapping 2D TRA 17Echos CUISSES",
    "T2mapping 2D TRA 17Echos JAMBES",
    "TFL_B1map"
]

pseudo_lock = Lock()
stats_lock = Lock()

class TransferStats:
    def __init__(self):
        self.total_patients = 0
        self.total_series = 0
        self.total_errors = 0
        self.pseudo_files = 0
        self.pseudo_errors = 0
    
    def increment_series(self):
        with stats_lock:
            self.total_series += 1
    
    def increment_errors(self):
        with stats_lock:
            self.total_errors += 1
    
    def increment_pseudo(self):
        with stats_lock:
            self.pseudo_files += 1
    
    def increment_pseudo_errors(self):
        with stats_lock:
            self.pseudo_errors += 1


def process_single_series(p_id, series_desc, research_pseudo, stats):
    """Treats a single biomarker series for a patient."""
    mover = Move(TelemisConfig)
    finder = Find(TelemisConfig)
    
    
    try:
        logger.info(f"[{p_id}] Searching: {series_desc}")
        
        criteria = SearchCriteria(
            patient_id=p_id,
            series_description=series_desc,
            level="SERIES",
            research_pseudo=research_pseudo
        )
        
        results = finder.search_data(criteria)
        
        if not results:
            logger.warning(f"[{p_id}] Nothing found for series: {series_desc}")
            return 0
        
        logger.info(f"[{p_id}] Found {len(results)} result(s) for {series_desc}")
        transferred = 0
        
        for idx, res in enumerate(results, 1):
            s_uid = getattr(res, 'SeriesInstanceUID', None)
            std_uid = getattr(res, 'StudyInstanceUID', None)
            
            if not s_uid or not std_uid:
                logger.warning(f"[{p_id}] Missing UID for result {idx}, skipping")
                continue
            
            logger.info(f"[{p_id}] [{idx}/{len(results)}] Transferring series...")
            
            specific_criteria = SearchCriteria(
                level='SERIES',
                study_instance_uid=std_uid,
                series_instance_uid=s_uid,
                research_pseudo=research_pseudo
            )
            
            try:
                mover.move_data(specific_criteria)
                stats.increment_series()
                transferred += 1
                logger.info(f"[{p_id}] ✓ Transfer {idx}/{len(results)} successful")
            except Exception as e:
                stats.increment_errors()
                logger.error(f"[{p_id}] ✗ Transfer failed: {e}")
        
        return transferred
    
    except Exception as e:
        logger.error(f"[{p_id}] Error processing series {series_desc}: {e}")
        stats.increment_errors()
        return 0


def process_patient(p_id, research_pseudo, stats):
    """Treats all biomarker series for a single patient."""
    logger.info(f"\n{'='*60}")
    logger.info(f"[{p_id}] Starting patient processing")
    logger.info(f"{'='*60}")
    
    total_transferred = 0
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(process_single_series, p_id, series_desc, research_pseudo, stats): series_desc
            for series_desc in BIOMARKERS
        }
        
        for future in as_completed(futures):
            series_desc = futures[future]
            try:
                transferred = future.result()
                total_transferred += transferred
            except Exception as e:
                logger.error(f"[{p_id}] Unexpected error for {series_desc}: {e}")
    
    logger.info(f"[{p_id}] Completed: {total_transferred} series transferred")
    return total_transferred


# def pseudonymize_file_safe(file_path, pseudonymizer, stats):
#     """Pseudonymize"""
#     try:
#         ds = pydicom.dcmread(file_path)
    
#         with pseudo_lock:
#             ds = pseudonymizer.pseudonymize_file(ds)
        
#         ds.save_as(file_path)
#         stats.increment_pseudo()
#         return True
    
#     except pydicom.errors.InvalidDicomError:
#         logger.warning(f"Invalid DICOM file: {os.path.basename(file_path)}")
#         stats.increment_pseudo_errors()
#         return False
#     except Exception as e:
#         logger.error(f"Error pseudonymizing {os.path.basename(file_path)}: {e}")
#         stats.increment_pseudo_errors()
#         return False


def pseudonymize_file_safe(file_path, pseudonymizer, stats):
    """Pseudonymize with detailed error handling"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            stats.increment_pseudo_errors()
            return False
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            logger.warning(f"Empty file (0 bytes): {os.path.basename(file_path)}")
            stats.increment_pseudo_errors()
            return False
        
        if file_size < 128: 
            logger.warning(f"File too small ({file_size} bytes): {os.path.basename(file_path)}")
            stats.increment_pseudo_errors()
            return False
        
        # Lecture DICOM avec force=True pour être plus permissif
        ds = pydicom.dcmread(file_path, force=True)
        
        # Vérification que c'est bien un DICOM valide
        if not hasattr(ds, 'SOPInstanceUID'):
            logger.warning(f"Missing SOPInstanceUID (not a valid DICOM): {os.path.basename(file_path)}")
            stats.increment_pseudo_errors()
            return False
        
        with pseudo_lock:
            ds = pseudonymizer.pseudonymize_file(ds)
        
        ds.save_as(file_path)
        stats.increment_pseudo()
        return True
    
    except InvalidDicomError as e:
        logger.warning(f"Invalid DICOM file: {os.path.basename(file_path)} - Reason: {str(e)}")
        stats.increment_pseudo_errors()
        return False
    
    except PermissionError as e:
        logger.error(f"Permission denied: {os.path.basename(file_path)} - {str(e)}")
        stats.increment_pseudo_errors()
        return False
    
    except Exception as e:
        logger.error(f"Unexpected error for {os.path.basename(file_path)}: {type(e).__name__} - {str(e)}")
        stats.increment_pseudo_errors()
        return False
    
def load_patient_ids(file_path):
    """
    Loads PatientIDs from a CSV or Excel file.
    
    Args:
        file_path: Path to the file (.csv or .xlsx)
    
    Returns:
        List of cleaned PatientIDs (str, no spaces, non-empty)
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_ext == '.xlsx':
            df = pd.read_excel(file_path, header=0)
            logger.info(f"Excel file loaded: {file_path}")
        elif file_ext == '.csv':
            df = pd.read_csv(file_path, sep=None, engine='python', header=0)
            logger.info(f"CSV file loaded: {file_path}")
        else:
            raise ValueError(f"Unsupported file format: {file_ext}. Use .csv or .xlsx")
        
        if df.empty:
            logger.warning(f"File is empty: {file_path}")
            return []
        
        first_column = df.iloc[:, 0]
        
        patients = (
            first_column
            .astype(str)                    
            .str.strip()                   
            .replace('nan', '')            
            .replace('', pd.NA)            
            .dropna()                       
            .tolist()                     
        )
        
        patients = [p for p in patients if p]
        
        logger.info(f"Extracted {len(patients)} valid PatientIDs")
        return patients
        
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        raise


@click.command()
@click.option('--file', '-f', required=True, help='CSV or XL Path (Format: PatientID)')
@click.option('--research-pseudo', is_flag=True, default=True, help='Enable pseudonymization')
@click.option('--max-workers', '-w', default=2, help='Number of parallel patients (default: 2)')
@click.option('--pseudo-workers', '-pw', default=5, help='Number of parallel pseudonymization workers (default: 5)')
def main(file, research_pseudo, max_workers, pseudo_workers):
    """Process DICOM images: search, transfer and pseudonymize"""
    
    if not os.path.exists(file):
        logger.error(f"CSV or XL file not found: {file}")
        return
    
    stats = TransferStats()
    pseudonymizer = PseudonymController()
    
    mover_global = Move(TelemisConfig)
    handlers = [(evt.EVT_C_STORE, mover_global._handle_store)]
    scp = mover_global.ae.start_server((UserConfig.IP, UserConfig.PORT), block=False, evt_handlers=handlers)
    logger.info(f"DICOM server started at {UserConfig.IP}:{UserConfig.PORT}")
    try:
        logger.info(f"Starting OPTIMIZED processing from: {file}")
        logger.info(f"Parallel patients: {max_workers}, Pseudo workers: {pseudo_workers}")
        patients = load_patient_ids(file)
        stats.total_patients = len(patients)
        logger.info(f"Loaded {len(patients)} patients to process")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_patient, p_id, research_pseudo, stats): p_id
                for p_id in patients
            }
            
            for future in as_completed(futures):
                p_id = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Fatal error for patient {p_id}: {e}")
        
        logger.info("\n" + "="*60)
        logger.info(f"Transfer phase completed")
        logger.info(f"Series transferred: {stats.total_series}, Errors: {stats.total_errors}")
        logger.info("="*60)
    
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        raise
    
    finally:
        scp.shutdown()
        logger.info("DICOM server stopped")
        
        if research_pseudo:
            logger.info("\nStarting PARALLEL pseudonymization phase...")
            temp_dir = "output_dir/temp_transit"
            
            if not os.path.exists(temp_dir):
                logger.warning(f"Temp directory not found: {temp_dir}")
            else:
                dicom_files = []
                for root, dirs, files in os.walk(temp_dir):
                    for filename in files:
                        if filename.startswith('.') or filename == "Thumbs.db":
                            continue
                        dicom_files.append(os.path.join(root, filename))
                
                logger.info(f"Found {len(dicom_files)} files to pseudonymize")
                
                with ThreadPoolExecutor(max_workers=pseudo_workers) as executor:
                    futures = {
                        executor.submit(pseudonymize_file_safe, file_path, pseudonymizer, stats): file_path
                        for file_path in dicom_files
                    }
                    
                    completed = 0
                    for future in as_completed(futures):
                        completed += 1
                        if completed % 50 == 0:
                            logger.info(f"Pseudonymized {completed}/{len(dicom_files)} files...")
                
                logger.info(f"Pseudonymization complete: {stats.pseudo_files} files, {stats.pseudo_errors} errors")

        logger.info("\nPerforming final sort...")
        try:
            mover_global.final_global_sort()
            logger.info("Final sort completed")
        except Exception as e:
            logger.error(f"Final sort failed: {e}")
        
        logger.info("\n" + "="*60)
        logger.info("PROCESS COMPLETED")
        logger.info(f"Patients: {stats.total_patients}, Series: {stats.total_series}, Errors: {stats.total_errors}")
        logger.info("="*60)


if __name__ == "__main__":
    main()
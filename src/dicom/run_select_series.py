"""Batch retrieval of a *selection* of series per patient (search -> select -> move).

Need
----
A colleague has a list of patients, each with many exams on Telemis. For each
patient he only wants:
  - "T1_TRA_TSE": the 2 EARLIEST series (the first two ever acquired),
  - "T2mapping 2D TRA 17Echos CUISSES": the single LATEST series (most recent).
Everything else must stay on the server.

Why a separate script
---------------------
`run_process.py` (already used by BMy) transfers EVERY series
matching its BIOMARKERS list. This script reuses its building blocks (patient
file loading, stats, pseudonymization) but adds a selection step, so
`run_process.py` is left untouched.

How it works
------------
For each patient and each rule in SELECTION_RULES:
  1. C-FIND at SERIES level, across all the patient's exams. This only returns
     metadata (dates, UIDs), so it is fast.
  2. Sort the results chronologically (SeriesDate, then SeriesTime, falling
     back to StudyDate when SeriesDate is empty) and keep the N earliest or
     the N latest, as the rule says.
  3. C-MOVE only those selected series (the slow part: actual images).
Then, as in run_process.py: optional pseudonymization of the received files
and final sort into output_dir/<patient>/<series>/. Finally, one
output_dir/<patient>/series_metadata.json per patient (PatientID + list of
SeriesNumber received), same format as the C-GET path (SeriesMetadataCollector).

Usage (from PIPELINE_01/dicom, `pipeline` env, on the machine whose IP is in
UserConfig):
    python -m dicom.run_select_series -f patients.xlsx
    python -m dicom.run_select_series -f patients.csv --no-research-pseudo

The patient file has one PatientID per row in its first column (header row
expected), same format as run_process.py.

To change what is retrieved, edit SELECTION_RULES only:
    "<SeriesDescription, '*' wildcards allowed>": ("earliest" | "latest", N)
"""

import os
import click
import logging
import pydicom
from pathlib import Path
from pynetdicom import evt
from concurrent.futures import ThreadPoolExecutor, as_completed

from dicom.config.server_config import TelemisConfig
from dicom.config.user_config import UserConfig
from dicom.services.find import Find
from dicom.services.move import Move
from dicom.services.search_criteria import SearchCriteria
from dicom.controllers.pseudonym_controller import PseudonymController
from dicom.services.json_file import SeriesMetadataCollector
from dicom.run_process import TransferStats, load_patient_ids, pseudonymize_file_safe

logger = logging.getLogger(__name__)

SELECTION_RULES = {
    "T1_TRA_TSE": ("earliest", 2),
    "T2mapping 2D TRA 17Echos CUISSES": ("latest", 1),
}


def _acquisition_key(res):
    """Chronological sort key of a C-FIND result."""
    date = getattr(res, "SeriesDate", "") or getattr(res, "StudyDate", "") or ""
    time = getattr(res, "SeriesTime", "") or ""
    try:
        number = int(getattr(res, "SeriesNumber", 0) or 0)
    except (TypeError, ValueError):
        number = 0
    return (str(date), str(time), number)


def select_series(results, order, count):
    """Keep the `count` earliest or latest series of `results`.
    Undated series are dropped: they cannot be placed in time."""
    dated = [r for r in results if _acquisition_key(r)[0]]
    if len(dated) < len(results):
        logger.warning(f"{len(results) - len(dated)} undated series ignored")
    ordered = sorted(dated, key=_acquisition_key)
    if order == "earliest":
        return ordered[:count]
    if order == "latest":
        return ordered[-count:]
    raise ValueError(f"Unknown order {order!r}, expected 'earliest' or 'latest'")


def process_rule(p_id, series_desc, order, count, research_pseudo, stats):
    """Search, select and transfer the series of one rule for one patient."""
    mover = Move(TelemisConfig)
    finder = Find(TelemisConfig)

    try:
        criteria = SearchCriteria(
            patient_id=p_id,
            series_description=series_desc,
            level="SERIES",
            research_pseudo=research_pseudo,
        )
        results = finder.search_data(criteria)
        if not results:
            logger.warning(f"[{p_id}] Nothing found for series: {series_desc}")
            return 0

        selected = select_series(results, order, count)
        logger.info(f"[{p_id}] {series_desc}: {len(results)} found, keeping {order} {len(selected)} "
                    f"-> {[_acquisition_key(r)[:2] for r in selected]}")

        transferred = 0
        for res in selected:
            s_uid = getattr(res, "SeriesInstanceUID", None)
            std_uid = getattr(res, "StudyInstanceUID", None)
            if not s_uid or not std_uid:
                logger.warning(f"[{p_id}] Missing UID, skipping one {series_desc} series")
                continue
            try:
                mover.move_data(SearchCriteria(
                    level="SERIES",
                    study_instance_uid=std_uid,
                    series_instance_uid=s_uid,
                    research_pseudo=research_pseudo,
                ))
                stats.increment_series()
                transferred += 1
            except Exception as e:
                stats.increment_errors()
                logger.error(f"[{p_id}] Transfer failed for {series_desc}: {e}")
        return transferred

    except Exception as e:
        logger.error(f"[{p_id}] Error processing series {series_desc}: {e}")
        stats.increment_errors()
        return 0


def process_patient(p_id, research_pseudo, stats):
    total = 0
    for series_desc, (order, count) in SELECTION_RULES.items():
        total += process_rule(p_id, series_desc, order, count, research_pseudo, stats)
    logger.info(f"[{p_id}] Completed: {total} series transferred")
    return total


def pseudonymize_received(temp_dir, pseudonymizer, stats, workers):
    if not os.path.exists(temp_dir):
        logger.warning(f"Temp directory not found: {temp_dir}")
        return
    dicom_files = [
        os.path.join(root, name)
        for root, _, files in os.walk(temp_dir)
        for name in files
        if not name.startswith(".") and name != "Thumbs.db"
    ]
    logger.info(f"Pseudonymizing {len(dicom_files)} files...")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for future in as_completed([executor.submit(pseudonymize_file_safe, f, pseudonymizer, stats)
                                    for f in dicom_files]):
            future.result()
    logger.info(f"Pseudonymization complete: {stats.pseudo_files} files, {stats.pseudo_errors} errors")


def write_series_metadata(patient_dirs):
    """Write series_metadata.json in each patient folder, from the sorted files.
    Reads one header per series folder (the folder holds a single series)."""
    for p_dir in patient_dirs:
        collector = SeriesMetadataCollector(p_dir)
        for s_dir in sorted(d for d in p_dir.iterdir() if d.is_dir()):
            first = next((f for f in s_dir.iterdir() if f.is_file()), None)
            if first is None:
                continue
            try:
                collector.add_instance(pydicom.dcmread(first, stop_before_pixels=True, force=True))
            except Exception as e:
                logger.error(f"Cannot read {first}: {e}")
        if collector.series_numbers:
            collector.save_to_json()


@click.command()
@click.option('--file', '-f', required=True, help='CSV or XL Path (Format: PatientID)')
@click.option('--research-pseudo/--no-research-pseudo', default=True, help='Pseudonymize received files (default: on)')
@click.option('--max-workers', '-w', default=2, help='Number of parallel patients (default: 2)')
@click.option('--pseudo-workers', '-pw', default=5, help='Number of parallel pseudonymization workers (default: 5)')
def main(file, research_pseudo, max_workers, pseudo_workers):
    """Retrieve, per patient, only the series selected by SELECTION_RULES."""
    if not os.path.exists(file):
        logger.error(f"CSV or XL file not found: {file}")
        return

    stats = TransferStats()
    mover_global = Move(TelemisConfig)
    handlers = [(evt.EVT_C_STORE, mover_global._handle_store)]
    scp = mover_global.ae.start_server((UserConfig.IP, UserConfig.PORT), block=False, evt_handlers=handlers)
    logger.info(f"DICOM server started at {UserConfig.IP}:{UserConfig.PORT}")
    try:
        patients = load_patient_ids(file)
        stats.total_patients = len(patients)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_patient, p_id, research_pseudo, stats): p_id
                       for p_id in patients}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Fatal error for patient {futures[future]}: {e}")
    finally:
        scp.shutdown()
        logger.info("DICOM server stopped")
        if research_pseudo:
            pseudonymize_received(mover_global.temp_dir, PseudonymController(), stats, pseudo_workers)
        try:
            mover_global.final_global_sort()
        except Exception as e:
            logger.error(f"Final sort failed: {e}")
        write_series_metadata(d for d in Path(mover_global.output_dir).iterdir()
                              if d.is_dir() and d != Path(mover_global.temp_dir))
        logger.info(f"DONE - Patients: {stats.total_patients}, Series: {stats.total_series}, "
                    f"Errors: {stats.total_errors}")


if __name__ == "__main__":
    main()

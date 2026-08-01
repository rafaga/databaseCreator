#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
This script download the EVE online's Tranquility Server
Database and discard all the non-essential data
"""
from pathlib import Path
import shutil
from sde_parser import SdeParser
from misc_utils import MiscUtils
from external_parser import ExternalParser
import json
import shutil
from pathlib import Path

FUZZ_DB_URL = 'https://www.fuzzwork.co.uk/dump/'
SDE_URL = "https://developers.eveonline.com/static-data/tranquility/" #eve-online-static-data-latest-yaml.zip
SDE_LATEST_INDEX_URL = SDE_URL + "latest.jsonl"
MAPS_URL = 'http://evemaps.dotlan.net/svg/'
FUZZ_DB_NAME = 'sqlite-latest.sqlite.bz2'
SDE_FILENAME = 'sde.zip'
SDE_CHECKSUM = 'checksum'
OUT_FILENAME = 'sde.db'
MD5_CHECKSUM = ''
data_resources = ['fsd','bsd','universe']
MiscUtils.chunk_size = 2391975
SDE_VARIANT = "jsonl"  # o "yaml", según el formato que consuma tu app

changes = []

def download_control(file_name, retries=3):
    """
    Controls the download of file
    """
    completed = False
    transfer_try = 0
    bytes_downloaded = 0
    while transfer_try < retries and completed is False:
        try:
            bytes_downloaded = MiscUtils.download_file(file_name)
            completed = True
        except TimeoutError:
            transfer_try += 1
            print(f'Transfer timeout, Retrying ({transfer_try}/{retries})')
    if transfer_try == retries:
        print('Maximum retries exceeded, aborting...')
    return bytes_downloaded

def update_as_needed(variant="jsonl"):
    """
    Verifica el build number más reciente del SDE publicado por CCP
    (developers.eveonline.com) y descarga el zip correspondiente solo
    si hay una versión más nueva que la que tenemos guardada localmente.

    variant: "jsonl" o "yaml" -- formato de exportación deseado.

    Ref: https://developers.eveonline.com/docs/services/static-data/#schema-changes
    """
    data_dir = Path('.').joinpath('data')
    data_dir.mkdir(exist_ok=True)

    build_file = data_dir.joinpath(f"sde-{variant}.build")
    zip_file = data_dir.joinpath(f"sde-{variant}.zip")

    # 1. Descargar el índice con el build number más reciente
    downloaded_index = download_control(SDE_LATEST_INDEX_URL)
    if downloaded_index is None:
        print('SDE: ' + SDE_LATEST_INDEX_URL + ' data not found')
        return False

    index_tmp = Path('.').joinpath('latest.jsonl')
    latest_build = None
    try:
        with open(index_tmp, 'rt', encoding='UTF-8') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get('_key') == 'sde':
                    latest_build = record.get('buildNumber')
                    break
    finally:
        if index_tmp.exists():
            index_tmp.unlink()

    if latest_build is None:
        print('SDE: could not determine latest build number')
        return False

    # 2. Comparar contra el build guardado localmente
    current_build = None
    if build_file.exists():
        current_build = build_file.read_text(encoding='UTF-8').strip()

    if str(current_build) == str(latest_build) and zip_file.exists():
        print(f'SDE: {variant} data its already updated (build {latest_build})')
        return False

    print(f'SDE: New build available ({current_build} -> {latest_build}), downloading {variant} data')

    zip_url = SDE_URL + f"eve-online-static-data-{latest_build}-{variant}.zip"
    if zip_file.exists():
        zip_file.unlink()

    if download_control(zip_url) is not None:
        downloaded_name = Path('.').joinpath(f"eve-online-static-data-{latest_build}-{variant}.zip")
        shutil.move(downloaded_name, zip_file)
        build_file.write_text(str(latest_build), encoding='UTF-8')
        return True
    else:
        print('SDE: ' + zip_url + ' data not found')
        return False

# --- Verifica y descarga si hay una versión nueva ---
change = update_as_needed(SDE_VARIANT)

# --- Si hubo cambio, reconstruye la base local ---
if change:
    if Path('.').joinpath(OUT_FILENAME).exists():
        Path('.').joinpath(OUT_FILENAME).unlink()
        print("SDE: removing current sde database, because a change was detected")

    sde_path = Path('.').joinpath('sde')
    if sde_path.exists():
        shutil.rmtree(sde_path)

    zip_path = Path('.').joinpath('data').joinpath(f"sde-{SDE_VARIANT}.zip")
    if not MiscUtils.zip_decompress(zip_path, sde_path):
        print('SDE: Error decompressing ' + str(sde_path))

if not Path('.').joinpath(OUT_FILENAME).exists():
    processor = SdeParser(Path('.').joinpath('sde'), OUT_FILENAME)
    processor.configuration.projection_algorithm = 'isometric' #values are isometric, dimetric and none
    processor.configuration.projected_axis = 1 # value range 0-X, 1-Y, 2-Z
    processor.configuration.file_format = SDE_VARIANT  # antes no se enlazaba con el parser
    processor.configuration.map_abyssal = True
    processor.configuration.map_kspace = True
    processor.configuration.map_void = True
    processor.configuration.map_wspace = True
    processor.configuration.projection_algorithm = 'isometric' # values are 'isometric' and 'dimetric'
    processor.create_table_structure()
    processor.parse_data()
    processor.close()
    eParser = ExternalParser(Path('.').joinpath('sde'), Path(OUT_FILENAME))
    eParser.map_url = MAPS_URL
    eParser.configuration.with_icebelts = True
    eParser.configuration.with_triglavian_status = True
    eParser.configuration.with_jove_observatories = True
    eParser.configuration.with_special_ore = True
    eParser.process()

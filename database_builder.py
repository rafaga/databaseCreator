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

FUZZ_DB_URL = 'https://www.fuzzwork.co.uk/dump/'
SDE_URL = 'https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/'
MAPS_URL = 'http://evemaps.dotlan.net/svg/'
FUZZ_DB_NAME = 'sqlite-latest.sqlite.bz2'
SDE_FILENAME = 'sde.zip'
SDE_CHECKSUM = 'checksum'
OUT_FILENAME = 'sde.db'
MD5_CHECKSUM = ''
data_resources = ['fsd','bsd','universe']
MiscUtils.chunk_size = 2391975

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

def update_as_needed(resource_name):
    md5 = []
    files = [resource_name + ".zip.checksum",resource_name + ".zip.checksum.bak", resource_name + ".zip"]
    md5_file = Path('.').joinpath('data').joinpath(files[0])
    bak_file = Path('.').joinpath('data').joinpath(files[1])
    zip_file = Path('.').joinpath('data').joinpath(files[2])
    md5_url = SDE_URL + files[0]
    zip_url = SDE_URL + files[2]

    if md5_file.exists():
        md5_file.unlink()
    downloaded_data = download_control(md5_url)

    if downloaded_data is not None:
        shutil.move(Path('.').joinpath(files[0]),md5_file)
        with open(md5_file, 'rt', encoding="UTF-8") as file:
            md5.append(file.read())
    else:
        print('SDE: ' + md5_url + ' data not found')
        md5.append('')
    if bak_file.exists():
        with open(bak_file, 'rt', encoding="UTF-8") as file:
            md5.append(file.read())
    else:
        md5.append('')

    if md5[0] != md5[1] and len(md5[1]) > 0 or not zip_file.exists():
        print('SDE: Inconsistencies found for ' + resource_name + ' data')
        if zip_file.exists():
            zip_file.unlink()
        print('SDE: Downloading ' + resource_name + ' data ')
        if download_control(zip_url) is not None:
            shutil.move(Path('.').joinpath(files[2]),zip_file)
        shutil.copyfile(md5_file,bak_file)
        return True
    else:
        print('SDE: ' + resource_name + ' its already updated')
    return False
    

for idx in range(3):
    changes.append(update_as_needed(data_resources[idx]))
    if changes[idx]:
        if Path('.').joinpath(OUT_FILENAME).exists():
            Path('.').joinpath(OUT_FILENAME).unlink()
            print("SDE: removing current sde database, because a change was detected")
        res_path = Path('.').joinpath('sde').joinpath(data_resources[idx])
        if res_path.exists():
            shutil.rmtree(res_path)
        if not MiscUtils.zip_decompress(Path('.').joinpath('data').joinpath(data_resources[idx] + ".zip"), Path('.').joinpath('sde').joinpath(data_resources[idx])):
            print('SDE: Error decompressing ' + str(Path('.').joinpath('sde').joinpath(data_resources[idx])))

if not Path('.').joinpath(OUT_FILENAME).exists():
    processor = SdeParser(Path('.').joinpath('sde'), OUT_FILENAME)
    processor.configuration.projection_algorithm = 'isometric' #values are isometric, dimetric and none
    processor.configuration.projected_axis = 1 # value range 0-X, 1-Y, 2-Z
    processor.configuration.extended_coordinates = False
    processor.configuration.map_abbysal = True
    processor.configuration.map_kspace = True
    processor.configuration.map_void = True
    processor.configuration.map_wspace = True
    processor.configuration.projection_algorithm = 'isometric' # values are 'isometric' and 'dimetric'
    processor.create_table_structure()
    processor.parse_data()
    processor.close()
    eParser = ExternalParser(Path('.').joinpath('maps'), Path(OUT_FILENAME))
    eParser.map_url = MAPS_URL
    eParser.configuration.with_icebelts = True
    eParser.configuration.with_triglavian_status = True
    eParser.configuration.with_jove_observatories = True
    eParser.configuration.with_special_ore = True
    eParser.process()

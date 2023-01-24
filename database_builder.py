#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
This script download the EVE online's Tranquility Server
Database and discard all the non-escential data
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
OUT_FILENAME = 'smt.db'
MD5_CHECKSUM = ''
MiscUtils.chunk_size = 2391975

source = []
source.append(Path('.').joinpath('checksum'))
source.append(Path('.').joinpath('sde.md5'))
source.append(SDE_URL + SDE_CHECKSUM)
source.append(SDE_URL + SDE_FILENAME)
source.append(Path('.').joinpath(SDE_FILENAME))
source.append(Path('.').joinpath(OUT_FILENAME))


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
        print('Maximum retries exceded, aborting...')
    return bytes_downloaded


def check_md5():
    """
    Method that download and verify SDE downloads
    """
    md5_str = []
    if source[0].exists():
        print('SDE: deleting old incomplete checksum')
        source[0].unlink()
    print('SDE: Downloading MD5 Checksum ...')
    downloaded = download_control(source[2])
    print(f"SDE: Downloaded {downloaded} bytes          ")
    for cont in range(0, 2):
        if Path(source[cont]).exists():
            with open(source[cont], 'rt', encoding='UTF-8') as md5_file:
                md5_str.append(md5_file.read())
    if len(md5_str) > 1:
        if md5_str[0] == md5_str[1]:
            print("SDE: The database it is already updated")
            return True
    print("SDE: a new version has been detected, proceding to download")
    if source[1].exists():
        source[1].unlink()
        source[0].rename(source[1])
    if source[4].exists():
        source[4].unlink()
    print('SDE: Downloading SDE database ...')
    downloaded = download_control(source[3])
    print(f"SDE: Downloaded {(downloaded/(1024**2)),2} Mb          ")
    md5_str.append(MiscUtils.md5sum(source[4]))
    if md5_str[-1] != md5_str[-2]:
        print('SDE: Error in Downloaded Database, Aborting ...')
        return False
    return True


if check_md5():
    # we delete the uncompessed directory
    sdePath = Path('.').joinpath('sde')
    if sdePath.exists():
        shutil.rmtree(sdePath)
    if source[5].exists():
        source[5].unlink()

    # decompressing the database
    if MiscUtils.zip_decompress(source[4], Path('.')):
        processor = SdeParser(sdePath, source[5])
        processor.configuration.extended_coordinates = False
        processor.configuration.map_abbysal = False
        processor.configuration.map_kspace = True
        processor.configuration.map_void = False
        processor.configuration.map_wspace = False
        processor.create_table_structure()
        processor.parse_data()
        processor.close()
        eParser = ExternalParser(Path('.').joinpath('maps'), Path(OUT_FILENAME))
        eParser.configuration.with_icebelts = True
        eParser.configuration.with_triglavian_status = True
        eParser.configuration.with_jove_observatories = True
        eParser.configuration.with_special_ore = True
        eParser.process()

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
MiscUtils.chunk_size = 2391975

source = []
source.append(Path('.').joinpath('checksum'))
source.append(Path('.').joinpath('sde.md5'))
source.append(SDE_URL + SDE_CHECKSUM)
source.append(SDE_URL + SDE_FILENAME)
source.append(Path('.').joinpath(SDE_FILENAME))
source.append(Path('.').joinpath(OUT_FILENAME))

# Download the MD5 Checksum
MiscUtils.download_file(source[2])

# this chunk of code detects if a new File exists
UPDATE_DETECTED = False
if Path(source[1]).exists():
    md5File = []
    md5File.append(open(source[0], 'rt', encoding='UTF-8'))
    md5File.append(open(source[1], 'rt', encoding='UTF-8'))
    if md5File[0].read() != md5File[1].read():
        UPDATE_DETECTED = True
    md5File[0].close()
    md5File[1].close()
    # Avoiding an Error on Windows OS, because the file its in use
    if UPDATE_DETECTED:
        source[1].unlink()
else:
    UPDATE_DETECTED = True

# we take an action based on what was detected
if UPDATE_DETECTED:
    print("SDE: a new version has been detected, proceding to download")
    if source[0].exists():
        source[0].rename(source[1].name)
    if source[4].exists():
        print("A previous version has been detected... deleting")
        source[4].unlink()
    # if Fuzzworks is not being used, then we delete the uncompessed directory
    sdePath = Path('.').joinpath('sde')
    if sdePath.exists():
        shutil.rmtree(sdePath)
    mbytesDownloaded = MiscUtils.download_file(source[3]) / (1024 * 1024)
    print(f"SDE: Downloaded {mbytesDownloaded,2}Mb          ")
else:
    print("SDE: The database it is already updated")

# remove the database if already exists, because we don't know the state of such file
if source[5].exists():
    source[5].unlink()

# decompressing the database
MiscUtils.zip_decompress(source[4], Path('.'))
processor = SdeParser(Path('.').joinpath('sde'), source[5])
processor.configuration.extended_coordinates = False
processor.configuration.map_abbysal = False
processor.configuration.map_kspace = True
processor.configuration.map_void = False
processor.configuration.map_wspace = False
processor.configuration.with_icebelts = True
processor.configuration.with_triglavian_status = True
processor.configuration.with_special_ore = True
processor.create_table_structure()
processor.parse_data()
processor.close()

if processor is not None:
    eParser = ExternalParser(Path('.').joinpath('maps'), Path(OUT_FILENAME))
    eParser.process()

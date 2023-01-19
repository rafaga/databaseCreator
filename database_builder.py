#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
This script download the EVE online's Tranquility Server
Database and discard all the non-escential data
"""
from pathlib import Path
import shutil
from external_parser import externalParser
from sde_parser import SdeParser
from misc_utils import miscUtils

FUZZ_DB_URL = 'https://www.fuzzwork.co.uk/dump/'
SDE_URL = 'https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/'
MAPS_URL = 'http://evemaps.dotlan.net/svg/'
FUZZ_DB_NAME = 'sqlite-latest.sqlite.bz2'
SDE_FILENAME = 'sde.zip'
SDE_CHECKSUM = 'checksum'
OUT_FILENAME = 'smt.db'
miscUtils.chunkSize = 2391975
updateDetected = False
fromFuzzWorks = False

source = []
if fromFuzzWorks:
    source.append(Path('.').joinpath(FUZZ_DB_NAME + '.md5'))
    source.append(Path('.').joinpath(FUZZ_DB_NAME + '.md5.old'))
    source.append(FUZZ_DB_URL + FUZZ_DB_NAME + '.md5')
    source.append(FUZZ_DB_URL + FUZZ_DB_NAME)
    source.append(Path('.').joinpath(FUZZ_DB_NAME))
else:
    source.append(Path('.').joinpath('checksum'))
    source.append(Path('.').joinpath('sde.md5'))
    source.append(SDE_URL + SDE_CHECKSUM)
    source.append(SDE_URL + SDE_FILENAME)
    source.append(Path('.').joinpath(SDE_FILENAME))
source.append(Path('.').joinpath(OUT_FILENAME))

""" Download the MD5 Checksum """
miscUtils.downloadFile(source[2])

""" this chunk of code detects if a new File exists """
if Path(source[1]).exists():
    md5File = []
    md5File.append(open(source[0], 'rt', encoding='UTF-8'))
    md5File.append(open(source[1], 'rt', encoding='UTF-8'))
    if md5File[0].read() != md5File[1].read():
        updateDetected = True
    md5File[0].close()
    md5File[1].close()
    """ Avoiding an Error on Windows OS, because the file its in use """
    if updateDetected:
        source[1].unlink()
else:
    updateDetected = True

""" we take an action based on what was detected """
if updateDetected:
    print("SDE: a new version has been detected, proceding to download")
    if source[0].exists():
        source[0].rename(source[1].name)
    if source[4].exists():
        print("A previous version has been detected... deleting")
        source[4].unlink()
    # if Fuzzworks is not being used, then we delete the uncompessed directory
    sdePath = Path('.').joinpath('sde')
    if not fromFuzzWorks and sdePath.exists():
        shutil.rmtree(sdePath)
    mbytesDownloaded = miscUtils.downloadFile(source[3]) / (1024 * 1024)
    print("SDE: Downloaded %0.2f Mb          " % mbytesDownloaded)
else:
    print("SDE: The database it is already updated")

""" remove the database if already exists, because we don't know the state of such file """
if source[5].exists():
    source[5].unlink()

# decompressing the database
if fromFuzzWorks:
    raise NotImplementedError
else:
    miscUtils.zipDecompress(source[4], Path('.'))
    processor = SdeParser(Path('.').joinpath('sde'), source[5])
    processor.configuration.extendedCoordinates = False
    processor.configuration.mapAbbysal = False
    processor.configuration.mapKSpace = True
    processor.configuration.mapVoid = False
    processor.configuration.mapWSpace = False
    processor.create_table_structure()
    processor.parse_data()
    processor.close()

if processor is not None:
    eParser = externalParser(Path('.').joinpath('maps'), Path(OUT_FILENAME))
    eParser.process()

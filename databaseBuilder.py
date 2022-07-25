#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""This script download the EVE online's Tranquility Server Database and discard all the non-escential data """
from pathlib import Path
import shutil
from externalParser import externalParser
from sdeParser import sdeParser
from miscUtils import miscUtils

fuzzDbUrl = 'https://www.fuzzwork.co.uk/dump/'
sdeUrl = 'https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/'
mapsURL = 'http://evemaps.dotlan.net/svg/'
fuzzDbName = 'sqlite-latest.sqlite.bz2'
sdeFileName = 'sde.zip'
sdeChecksum = 'checksum' 
outFileName = 'smt.db'
miscUtils.chunkSize = 2391975
updateDetected = False
fromFuzzWorks = False

source = []
if fromFuzzWorks:
    source.append(Path('.').joinpath(fuzzDbName + '.md5'))
    source.append(Path('.').joinpath(fuzzDbName + '.md5.old'))
    source.append(fuzzDbUrl + fuzzDbName + '.md5')
    source.append(fuzzDbUrl + fuzzDbName)
    source.append(Path('.').joinpath(fuzzDbName))
else:
    source.append(Path('.').joinpath('checksum'))
    source.append(Path('.').joinpath('sde.md5'))
    source.append(sdeUrl + sdeChecksum)
    source.append(sdeUrl + sdeFileName)
    source.append(Path('.').joinpath(sdeFileName))
source.append(Path('.').joinpath(outFileName))

""" Download the MD5 Checksum """ 
miscUtils.downloadFile(source[2])

""" this chunk of code detects if a new File exists """
if Path(source[1]).exists():
    md5File = []
    md5File.append(open(source[0],'rt'))
    md5File.append(open(source[1],'rt'))
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
    mbytesDownloaded = miscUtils.downloadFile(source[3])/(1024*1024)
    print("SDE: Downloaded %0.2f Mb          "%mbytesDownloaded)
else:
    print("SDE: The database it is already updated")

""" remove the database if already exists, because we don't know the state of such file """ 
if source[5].exists():
    source[5].unlink()

# decompressing the database 
if fromFuzzWorks:
    # TODO
    pass
else:
    miscUtils.zipDecompress(source[4],Path('.'))
    processor = sdeParser(Path('.').joinpath('sde'),source[5])
    processor.configuration.extendedCoordinates = False
    processor.configuration.mapAbbysal = False
    processor.configuration.mapKSpace= True
    processor.configuration.mapVoid = False
    processor.configuration.mapWSpace = False
    processor.createTableStructure()
    processor.parseData()
    processor.close()

if processor is not None:
    eParser = externalParser(Path('.').joinpath('maps'),Path(outFileName))
    eParser.process()
    



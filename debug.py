#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""This script download the EVE online's Tranquility Server Database and discard all the non-escential data """
import requests
import os
import bz2

from databaseUtils import DatabaseUtils
from pathlib import Path
import xml.etree.ElementTree
import zipfile
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
chunkSize = 2391975
miscUtils.chunkSize = 2391975
updateDetected = False
fromFuzzWorks = False

source = []
if fromFuzzWorks:
    source.append(os.path.join('.',fuzzDbName + '.md5'))
    source.append(os.path.join('.',fuzzDbName + '.md5.old'))
    source.append(fuzzDbUrl + fuzzDbName + '.md5')
    source.append(fuzzDbUrl + fuzzDbName)
    source.append(os.path.join('.',fuzzDbName))
else:
    source.append(os.path.join('.','checksum'))
    source.append(os.path.join('.','sde.md5'))
    source.append(sdeUrl + sdeChecksum)
    source.append(sdeUrl + sdeFileName)
    source.append(os.path.join('.',sdeFileName))
source.append(os.path.join('.',outFileName))

eParser = externalParser(Path('.').joinpath('maps'),Path(outFileName))
eParser.process()
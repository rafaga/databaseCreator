#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""This script download the EVE online's Tranquility Server Database and discard all the non-escential data """
import requests
import os
import bz2

from sqlalchemy import false
from databaseUtils import DatabaseUtils
from pathlib import Path
import xml.etree.ElementTree
import zipfile
from sdeParser import sdeParser,sdeConfig

fuzzDbUrl = 'https://www.fuzzwork.co.uk/dump/'
sdeUrl = 'https://eve-static-data-export.s3-eu-west-1.amazonaws.com/tranquility/'
mapsURL = 'http://evemaps.dotlan.net/svg/'
fuzzDbName = 'sqlite-latest.sqlite.bz2'
sdeFileName = 'sde.zip'
sdeChecksum = 'checksum' 
outFileName = 'smt.db'
chunksize = 2391975
updateDetected = False
fromFuzzWorks = False

def iterateList(array):
    for value in array:
        yield (value,)

def extractMapData(mapFileName, dbConnection):
    """Function that serach all the icebetls and abstract coordinates 
       in the dotlan maps and updates its status in Database"""
    eTree = xml.etree.ElementTree.ElementTree()
    root = eTree.parse(source=mapFileName)
    solarSystemIds = []

    """ here we are iterating over Ice Belts and adding to Database """
    tags = root.findall(".//{http://www.w3.org/2000/svg}rect[@class='i']")
    for tag in tags:
        tagID = tag.attrib.get('id')
        if tagID is not None:
            solarSystemIds.append(tagID[3::])
    if len(solarSystemIds) > 0:
        query = "UPDATE mapSolarSystems SET hasIceBelt=1 WHERE solarSystemID IN (?)"
        cur = dbConnection.cursor()
        cur.executemany(query,iterateList(solarSystemIds))
        cur.close()
    
    solarSystemIds.clear()
    """ here we retrieving all the coordionates from the Regional maps """
    tags = root.findall(".//{http://www.w3.org/2000/svg}use")
    regionId = int(Path(mapFileName).name.split('.')[0])
    cur = dbConnection.cursor()
    for tag in tags:
        tagID = tag.attrib.get('id')[3::]
        solarSystemIds = {"id": tagID, "regionId": regionId, "X": tag.attrib.get('x'), "Y": tag.attrib.get('y')}
        query = "INSERT INTO mapAbstractSystems (solarSystemId,regionId,x,y) VALUES (:id,:regionId,:X,:Y);"
        cur.execute(query,solarSystemIds)
    cur.close()
    dbConnection.commit()

def getAllRegions(conn):
    """Function to get all regions from SDE and download the svg maps from dotlan"""
    cur = conn.cursor()
    try:
        cur.execute("SELECT regionID, regionName FROM mapRegions WHERE regionID < :regionID ;",{"regionID": 11000000})
        rows = cur.fetchall()
    except:
        print("Dotlan: Error ... ")
        conn.rollback()
    cur.close()
    return rows


def downloadFile(url, filename = None):
    """Download a file from Internet, but it assumes it should be on the current path
     and no other parameters are present on the url. This methond doesn't overwrite files,
     so you need to be sure that file doesn't exists before download anything."""
    filePath= ""
    total_length = 0
    if(filename != None):
        filePath = os.path.join('.', filename)
    else:
        # TODO: implement a way to discard any no-esscential parameter from url
        filePath = url.split('/')[-1]
    r = requests.get(url, stream=True)
    with open(filePath, "wb") as zFile:
        total_length = 0
        bytes_downloaded = 0
        percentDownloaded = "--"
        if r.headers.get('content-length') != None:
           total_length = int(r.headers.get('content-length'))
        for chunk in r.iter_content(chunksize):
            if chunk:
                zFile.write(chunk)
                bytes_downloaded += len(chunk)
                kbDownloaded = round(bytes_downloaded/1024)
                if total_length > 0:
                    percentDownloaded = bytes_downloaded/total_length
                print('Downloading: %d kb [%s%%]\r'%(kbDownloaded,percentDownloaded),end="")
    return bytes_downloaded

def bz2Decompress(compressedFilePath,uncompressedFilePath):
    """Decompress the database that we get from fuzzworks"""
    nbytes = 0
    zFile = None
    uzFile = None
    bzDecomp = bz2.BZ2Decompressor()
    filesize = os.stat(compressedFilePath).st_size
    DecompressedTotal = 0
    with open(compressedFilePath, 'rb') as zFile:
        uzFile = open(uncompressedFilePath,"wb")
        for chunk in iter(lambda: zFile.read(chunksize), b''):
            a = bzDecomp.decompress(chunk)
            if len(a) != 0:
                nbytes += uzFile.write(a)
                DecompressedTotal += len(chunk)
                print(f'SDE: Decompressing [{round((DecompressedTotal / filesize)*100,2)}%]  \r',end="")
    uzFile.close()
    print('SDE: Decompressing Done       ')
    return nbytes

def zipDecompress(compressedFilePath,outputPath):
    with zipfile.ZipFile(compressedFilePath, 'r') as zip_ref:
        zip_ref.extractall(outputPath)

source = []
if fromFuzzWorks:
    source.append(os.path.join('.',fuzzDbName + '.md5'))
    source.append(os.path.join('.',fuzzDbName + '.md5.old'))
    source.append(fuzzDbUrl + fuzzDbName + '.md5')
    source.append(fuzzDbUrl + fuzzDbName)
    source.append(os.path.join('.',fuzzDbName))
else:
    source.append(os.path.join('.','sde.md5'))
    source.append(os.path.join('.','sde.md5.old'))
    source.append(sdeUrl + sdeChecksum)
    source.append(sdeUrl + sdeFileName)
    source.append(os.path.join('.',sdeFileName))
source.append(os.path.join('.',outFileName))

""" Download the MD5 Checksum """ 
downloadFile(source[2])

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
        os.remove(source[1]) 
else:
    updateDetected = True

""" we take an action based on what was detected """ 
if updateDetected:
    print("SDE: a new version has been detected, proceding to download")
    os.rename(source[0],source[1])
    if Path(source[4]).exists():
        print("A previous version has been detected... deleting")
        os.remove(source[4])
    # if Fuzzworks is not being used, then we delete the uncompessed directory
    if not fromFuzzWorks:
        os.removedirs(os.path.join('.','sde'))
    mbytesDownloaded = downloadFile(source[3])/(1024*1024)
    print("SDE: Downloaded %0.2f Mb          "%mbytesDownloaded)
else:
    print("SDE: The database it is already updated")

""" remove the database if already exists, because we don't know the state of such file """ 
if Path(source[5]).exists():
    os.remove(source[5])

# decompressing the database 
if fromFuzzWorks:
    bz2Decompress(source[4],source[5])
    """ We have the SDE database in all its full glory, let's to slim dat thicc file now """
    processor = DatabaseUtils(source[5])
    processor.syncTables()
    processor.addAdditionalData()
else:
    zipDecompress(source[4],os.path.join('.','sde'))
    processor = sdeParser(os.path.join('.','sde'),source[5])
    processor.configuration.extendedCoordinates = False
    processor.configuration.mapAbbysal = False
    processor.configuration.mapKSpace= True
    processor.configuration.mapVoid = False
    processor.configuration.mapWSpace = False
    processor.createTableStructure()
    processor.parseData()

if processor is not None:
    """ Retrieving all Regions from Dotlan to parse the SVG data """
    eveRegions = getAllRegions(processor.conn)
    for region in eveRegions:
        fileSize = 0
        mapFilePath = os.path.join('./maps/', str(region[0]) + '.svg')
        if not Path(mapFilePath).exists():
            mapUrl = mapsURL + region[1].replace(' ','_') + ".svg"
            fileSize = downloadFile(mapUrl,"maps/" + str(region[0]) + ".svg")
            if fileSize <= 100:
                os.remove("maps/" + str(region[0]) + ".svg")
                print("Dotlan: Invalid data was recieved for " + region[1])
            else:
                print("Dotlan: Downloaded Map for " + region[1])
        print("Dotlan: parsing data for " + region[1])
        extractMapData(mapFilePath, sdeParser.conn)
    



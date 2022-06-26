#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""This script download the EVE online's Tranquility Server Database and discard all the non-escential data """
import requests
import os
import bz2
from databaeUtils import DatabaseUtils
from pathlib import Path

dbUrl = 'https://www.fuzzwork.co.uk/dump/'
zName = 'sqlite-latest.sqlite.bz2'
uzName = 'smt.db'
chunksize = 2391975
updateDetected = False

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

""" Download the MD5 Checksum """ 
downloadFile(dbUrl + zName + '.md5')

""" this chunk of code detects if a new File exists """
filenames = [os.path.join('.',zName + '.md5'),os.path.join('.',zName + '.md5.old')]
if Path(filenames[1]).exists():
    md5File = []
    md5File.append(open(filenames[0],'rt'))
    md5File.append(open(filenames[1],'rt'))
    if md5File[0].read() != md5File[1].read():
        updateDetected = True
    md5File[0].close()
    md5File[1].close()
    """ Avoiding an Error on Windows OS, because the file its in use """ 
    if updateDetected:
        os.remove(filenames[1]) 
else:
    updateDetected = True

""" we take an action based on what was detected """ 
if updateDetected:
    print("SDE: a new version has been detected, proceding to download")
    os.rename(filenames[0],filenames[1])
    try:
        os.remove(os.path.join('.', zName))
    except:
        print("SDE Error: previous file does not exists.")
    mbytesDownloaded = downloadFile(dbUrl + zName)/(1024*1024)
    print("SDE: Downloaded %0.2f "%mbytesDownloaded)
else:
    print("SDE: The database it is already updated")

""" remove the database if already exists, because we don't know the state of such file """ 
if Path(os.path.join('.', uzName)).exists():
    os.remove(os.path.join('.', uzName))

""" decompressing the database """ 
bz2Decompress(os.path.join('.', zName),os.path.join('.', uzName))

""" We have the SDE database in all its full glory, let's to slim dat thicc file now """
SDEprocessor = DatabaseUtils(os.path.join('.', uzName))
SDEprocessor.syncTables()
SDEprocessor.addAddtionalData()
SDEprocessor.vacumm()

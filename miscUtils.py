# -*- coding: UTF-8 -*-
from pathlib import Path
import requests
import zipfile
import bz2
import classutilities

class miscUtils(object):
    __chunksize = 2391975

    @classutilities.classproperty
    def chunkSize(self):
        """the size of the chunk downloaded"""
        return self.__chunksize

    @chunkSize.setter
    def chunkSize(self, size):
        self.__chunksize = size

    @classmethod
    #TODO: Convertir este metodo en algo mas adecuado para uso de clases
    def downloadFile(cls, url, filename = None):
        """Download a file from Internet, but it assumes it should be on the current path
        and no other parameters are present on the url. This methond doesn't overwrite files,
        so you need to be sure that file doesn't exists before download anything."""
        filePath= ""
        total_length = 0
        if isinstance(filename,str):
            filePath = Path('.').joinpath(filename)
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
            for chunk in r.iter_content(cls.chunkSize):
                if chunk:
                    zFile.write(chunk)
                    bytes_downloaded += len(chunk)
                    kbDownloaded = round(bytes_downloaded/1024)
                    if total_length > 0:
                        percentDownloaded = round((bytes_downloaded/total_length)*100,2)
                    print('Downloading: %d kb [%s%%]\r'%(kbDownloaded,percentDownloaded),end="")
        return bytes_downloaded

    @classmethod
    def bz2Decompress(cls, compressedFilePath,uncompressedFilePath):
        """Decompress the database that we get from fuzzworks"""
        nbytes = 0
        zFile = None
        uzFile = None
        bzDecomp = bz2.BZ2Decompressor()
        filesize = Path(compressedFilePath).stat['st_size']
        #filesize = os.stat(compressedFilePath).st_size
        DecompressedTotal = 0
        with open(compressedFilePath, 'rb') as zFile:
            uzFile = open(uncompressedFilePath,"wb")
            for chunk in iter(lambda: zFile.read(cls.chunkSize), b''):
                a = bzDecomp.decompress(chunk)
                if len(a) != 0:
                    nbytes += uzFile.write(a)
                    DecompressedTotal += len(chunk)
                    print(f'SDE: Decompressing [{round((DecompressedTotal / filesize)*100,2)}%]  \r',end="")
        uzFile.close()
        print('SDE: Decompressing Done       ')
        return nbytes

    @classmethod
    def zipDecompress(cls, compressedFilePath,outputPath):
        with zipfile.ZipFile(compressedFilePath, 'r') as zip_ref:
            zip_ref.extractall(outputPath)
            print('SDE: Decompressing File')
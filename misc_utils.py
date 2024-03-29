# -*- coding: UTF-8 -*-
"""
Provide a wide range of tools to download and.
decompress files from internet
"""
from pathlib import Path
import zipfile
import bz2
import hashlib
from functools import partial
import classutilities
import requests


class MiscUtils(object):
    __chunk_size = 2391975

    @classutilities.classproperty
    def chunk_size(cls):
        """the size of the chunk downloaded"""
        return cls.__chunk_size

    @chunk_size.setter
    def chunk_size(cls, size):
        cls.__chunk_size = size

    @classmethod
    # TODO: Convertir este metodo en algo mas adecuado para uso de clases
    def download_file(cls, url, filename=None):
        """
        Download a file from Internet, but it assumes it should be on the current path
        and no other parameters are present on the url. This methond doesn't overwrite files,
        so you need to be sure that file doesn't exists before download anything.
        """
        file_path = ""
        total_length = 0
        if isinstance(filename, str):
            file_path = Path('.').joinpath(filename)
        else:
            # TODO: implement a way to discard any no-esscential parameter from url
            file_path = url.split('/')[-1]
        # check if URL exists
        r = requests.head(url, allow_redirects=True, timeout=500)
        if r.status_code == 200:
            request_obj = requests.get(url, stream=True, timeout=500)
            with open(file_path, "wb") as zip_file:
                total_length = 0
                bytes_downloaded = 0
                downloaded_percent = "--"
                if request_obj.headers.get('content-length') is not None:
                    total_length = int(request_obj.headers.get('content-length'))
                for chunk in request_obj.iter_content(cls.chunk_size):
                    if chunk:
                        zip_file.write(chunk)
                        bytes_downloaded += len(chunk)
                        downloaded_kb = round(bytes_downloaded / 1024)
                        if total_length > 0:
                            downloaded_percent = round((bytes_downloaded / total_length) * 100, 2)
                        print(f'Downloading: {downloaded_kb} kb [{downloaded_percent}%]\r', end="")
            return bytes_downloaded
        return 0

    @classmethod
    def bz2_decompress(cls, compressed_filepath, uncompressed_filepath):
        """
        Decompress the BZ2 files
        """
        nbytes = 0
        zip_file = None
        unzip_file = None
        bz_decomp = bz2.BZ2Decompressor()
        filesize = Path(compressed_filepath).stat['st_size']
        decompressed_total = 0
        with open(compressed_filepath, 'rb') as zip_file:
            unzip_file = open(uncompressed_filepath, "wb")
            for chunk in iter(lambda: zip_file.read(cls.chunk_size), b''):
                decomp_chunk = bz_decomp.decompress(chunk)
                if len(decomp_chunk) != 0:
                    nbytes += unzip_file.write(decomp_chunk)
                    decompressed_total += len(chunk)
                    print('SDE: Decompressing '
                          f'[{round((decompressed_total / filesize)*100,2)}%]  \r', end="")
        unzip_file.close()
        print('SDE: Decompressing Done       ')
        return nbytes

    @classmethod
    def zip_decompress(cls, compressed_filepath, output_path):
        """
        Extract content from a zip file using a path as output
        """
        try:
            with zipfile.ZipFile(compressed_filepath, 'r') as zip_ref:
                zip_ref.extractall(output_path)
                print(f'SDE: Decompressing {compressed_filepath}')
                return True
        except zipfile.BadZipFile:
            return False

    @classmethod
    def md5sum(cls, filename):
        """
        Calculate MD5 checksum for file, this is not needed in 3.11 or later 
        because it has a native function
        """
        with open(filename, mode='rb') as f:
            d = hashlib.md5()
            for buf in iter(partial(f.read, 128), b''):
                d.update(buf)
        return d.hexdigest()

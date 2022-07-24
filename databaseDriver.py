#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Autor: Rafael Amador Galván
# Fecha: 11/07/2022

import enum
import sqlite3
from pathlib import Path

class DatabaseType(enum.Enum):
    NONE = 0
    SQLITE = 1

class DatabaseDriver:
    """Module that works as a simple abstraction layer for database operations"""
    # Internal Variables
    __databaseType = None
    __dataSource = None

    # Propiedades
    @property
    def dataSource(self):
        """the database file name"""
        return self.__dataSource

    @dataSource.setter
    def dataSource(self, dataSource):
        # a validation should be done here
        if self.databaseType == DatabaseType.SQLITE:
            if isinstance(dataSource,Path):
                self.__dataSource = dataSource
            if isinstance(dataSource,str):
                self.__dataSource = Path(dataSource)
            if self.__dataSource.exists() and self.__dataSource.is_file():
                if self.__isSqLite3(self.__dataSource):
                    self.__createConnection(self.__dataSource)
            else:
                self.__createConnection(self.__dataSource)
        if dataSource is None:
            self.__dataSource = None

    @property
    def databaseType(self):
        return self.__databaseType

    @property
    def connection(self):
        return self.__connection

    # Constructor
    def __init__(self, databaseType=DatabaseType.NONE, datasourceString=None):
        if not isinstance(databaseType,DatabaseType):
            raise(IndexError)
        if databaseType is databaseType.NONE:
            raise(NotImplementedError)
        self.__databaseType=databaseType
        if datasourceString is not None:
            self.dataSource=datasourceString
        
    def __isSqLite3(self,databaseFile):
        """Function that checks if given file has a valid SQLite format"""
        # SQLite database file header is 100 bytes
        if databaseFile.stat().st_size < 100:
            return False
        with open(databaseFile, 'rb') as file:
            header = file.read(100)
        return header[:16] == b'SQLite format 3\x00'
    
    def __createConnection(self, dataSourceString):
        if self.databaseType == DatabaseType.SQLITE:
            self.__connection = sqlite3.connect(self.__dataSource.resolve())



#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Autor: Rafael Amador Galván
# Fecha: 11/07/2022
"""
Provides a conosolidated way to access databases
"""
import enum
import sqlite3
from pathlib import Path


class DatabaseType(enum.Enum):
    """
    Enum for every database engine supported by the driver
    """
    NONE = 0
    SQLITE = 1


class DatabaseDriver:
    """Module that works as a simple abstraction layer for database operations"""
    # Internal Variables
    __database_type = None
    __data_source = None
    __connection = None

    # Propiedades
    @property
    def data_source(self):
        """the database file name"""
        return self.__data_source

    @data_source.setter
    def data_source(self, data_source):
        # a validation should be done here
        if self.database_type == DatabaseType.SQLITE:
            if isinstance(data_source, Path):
                self.__data_source = data_source
            if isinstance(data_source, str):
                self.__data_source = Path(data_source)
            if self.__data_source.exists() and self.__data_source.is_file():
                if self.__is_sqlite3(self.__data_source):
                    self.__create_connection(self.__data_source)
            else:
                self.__create_connection(self.__data_source)
        if data_source is None:
            self.__data_source = None

    @property
    def database_type(self):
        """
        Property to set the database type used by the driver
        """
        return self.__database_type

    @property
    def connection(self):
        """
        Property to return the connection object
        """
        return self.__connection

    # Constructor
    def __init__(self, database_type=DatabaseType.NONE, datasource_string=None):
        if not isinstance(database_type, DatabaseType):
            raise IndexError
        if database_type is database_type.NONE:
            raise NotImplementedError
        self.__database_type = database_type
        if datasource_string is not None:
            self.data_source = datasource_string

    def __is_sqlite3(self, database_file):
        """Function that checks if given file has a valid SQLite format"""
        # SQLite database file header is 100 bytes
        if database_file.stat().st_size < 100:
            return False
        with open(database_file, 'rb', encoding='UTF-8') as file:
            header = file.read(100)
        return header[:16] == b'SQLite format 3\x00'

    def __create_connection(self, datasource_string):
        if self.database_type == DatabaseType.SQLITE:
            self.__connection = sqlite3.connect(self.__data_source.resolve())

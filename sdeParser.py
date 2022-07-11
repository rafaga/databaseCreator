#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
""" This script provides a Class to parse SDE structure into a SQLite Database"""
import sqlite3
from databaseDriver import DatabaseDriver, DatabaseType
import yaml
from pathlib import Path

class DirectoryNotFoundError(Exception):
    pass

class sdeParser:
    # Propiedades
    _yamlDirectory = None
    _dbDriver = None
    _dbType = None

    @property
    def yamlDirectory(self):
        """the database file name"""
        return self._yamlDirectory

    @yamlDirectory.setter
    def yamlDirectory(self, filename):
        self._yamlDirectory = filename

    # Constructor
    def __init__(self, directory, databaseFile, type = DatabaseType.SQLITE):
        if Path(directory).is_dir():
            self.yamlDirectory= directory
        else:
            raise(DirectoryNotFoundError('The specified directory does not exists.'))
        self._dbDriver = DatabaseDriver(type,databaseFile)
        self._dbType = type
        pass

    def readDirectory(self, directoryPath):
        for element in directoryPath.iterdir():
            if element.is_dir():
                self.readDiretory(element.name)
            if element.is_file():
                pass

    def createTableStructure(self):
        if self._dbType == DatabaseType.SQLITE:
            #mapSolarSystems - SQLite
            query = ('CREATE TABLE IF NOT EXISTS mapSolarSystems (solarSystemID INT NOT NULL PRIMARY KEY'
                    ',constellationID INT NOT NULL REFERENCES mapConstellations(constellationID) ON UPDATE CASCADE'
                    'ON DELETE SET NULL ,center_x FLOAT NOT NULL ,center_y FLOAT NOT NULL ,center_z FLOAT NOT NULL'
                    ',corridor BOOL NOT NULL ,fringe BOOL NOT NULL ,hub BOOL NOT NULL ,international BOOL NOT NULL'
                    ',luminosity FLOAT NOT NULL ,max_x FLOAT NOT NULL ,max_y FLOAT NOT NULL ,max_z FLOAT NOT NULL'
                    ',min_x FLOAT NOT NULL ,min_y FLOAT NOT NULL ,min_z FLOAT NOT NULL')

            #Constelations - SQLite
            
            #SolarSystemGates - SQLite

            #SolarSystemPlanets - SQLite

            #SolarSystemStar - SQLite

            #Regions - SQLite

    """'CREATE TABLE mapAbstractSystems (solarSystemID INT '
                        'REFERENCES mapSolarSystems(solarSystemID) ON UPDATE CASCADE ON DELETE SET NULL,'
                        'regionID INT NOT NULL REFERENCES mapRegions(RegionID) ON UPDATE CASCADE ON DELETE SET NULL,'
                        'x INT NOT NULL, y INT NOT NULL, CONSTRAINT pkey PRIMARY KEY (solarSystemID, regionID) '
                        'ON CONFLICT FAIL);'"""
        
    def readUniverse(self, withKSpace=True,  withWSpace=True, withAbbysal=True, withVoid=False):
        universeDirectory = Path(self._yamlDirectory).joinpath('fsd','universe')
        if withKSpace:
            self.readDirectory(universeDirectory.joinpath('eve'))
        if withWSpace:
            self.readDirectory(universeDirectory.joinpath('wormhole'))
        if withAbbysal:
            self.readDirectory(universeDirectory.joinpath('abyssal'))
        if withVoid:
            self.readDirectory(universeDirectory.joinpath('void'))
        pass



    @classmethod
    def fromFuzzworks(cls,databaseUrl):
        raise(NotImplementedError)

    def syncTables(self):
        pass

    def addAdditionalData(self):
        pass
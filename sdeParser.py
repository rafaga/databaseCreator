#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
""" This script provides a Class to parse SDE structure into a SQLite Database"""
import sqlite3
from databaseDriver import DatabaseDriver, DatabaseType
import yaml
from pathlib import Path

class sdeConfig:
    extendedCoordinates=True
    mapKSpace=True
    mapWSpace=True
    mapAbbysal=True
    mapVoid=False

class DirectoryNotFoundError(Exception):
    pass

class sdeParser:
    # Propiedades
    _yamlDirectory = None
    _dbDriver = None
    _dbType = None
    _config = None

    @property
    def configuration(self):
        return self._config

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
        self._config = sdeConfig()
        pass

    def _readDirectory(self, directoryPath):
        for element in directoryPath.iterdir():
            if element.is_dir():
                self.readDiretory(element.name)
            if element.is_file():
                if element.name == "region.staticdata":
                    self._parseRegion(element)
                if element.name == "constellation.staticdata":
                    self._parseConstellation(element)
                if element.name == "solarsystem.staticdata":
                    self._parseSolarSystem(element)

    def createTableStructure(self):
        if self._dbType == DatabaseType.SQLITE:
            cur = self._dbDriver.connection.cursor()
            #categories - SQLite
            query = ('CREATE TABLE IF NOT EXISTS invCategories( categoryId INT NOT NULL PRIMARY KEY'
                     ',categoryName TEXT NOT NULL ,published BOOL NOT NULL);')
            cur.execute(query)

            #GroupIds - SQLite
            query = ('CREATE TABLE IF NOT EXISTS invGroups( groupId INT NOT NULL PRIMARY KEY'
                     ',categoryName TEXT NOT NULL ,categoryId INT NOT NULL REFERENCES invCategories(categoryId) '
                     'ON UPDATE CASCADE ON DELETE SET NULL, anchorable BOOL NOT NULL'
                     ');')
            cur.execute(query)

            #InvType - SQLite
            query = ('CREATE TABLE IF NOT EXISTS invTypes(typeId INT NOT NULL PRIMARY KEY '
                    ',groupId INT NOT NULL REFERENCES invGroups(groupId) ON UPDATE CASCADE ON DELETE SET NULL'
                    ',iconId INT, typeName TEXT NOT NULL, published BOOL NOT NULL, volume FLOAT '
                    ');')
            cur.execute(query)

            #Regions - SQLite
            query = ('CREATE TABLE IF NOT EXISTS mapRegions (regionId INT NOT NULL PRIMARY KEY'
                     ',regionName TEXT NOT NULL, nebula INT NOT NULL, wormholeClassId INT NOT NULL '
                     ',centerX FLOAT NOT NULL ,centerY FLOAT NOT NULL ,centerZ FLOAT NOT NULL ')

            if self._config.extendedCoordinates :
                query += (',maxX FLOAT NOT NULL ,maxY FLOAT NOT NULL ,maxZ FLOAT NOT NULL '
                          ',minX FLOAT NOT NULL ,minY FLOAT NOT NULL ,minZ FLOAT NOT NULL ')
            query += ');'
            cur.execute(query)

            #Constelations - SQLite
            query = ('CREATE TABLE IF NOT EXISTS mapConstellations (constellationId INT NOT NULL PRIMARY KEY '
                     ',constellationName TEXT NOT NULL ,regionId INT NOT NULL REFERENCES '
                     'mapRegions(regionId) ON UPDATE CASCADE ON DELETE SET NULL ,radius FLOAT NOT NULL '
                     ',centerX FLOAT NOT NULL ,centerY FLOAT NOT NULL ,centerZ FLOAT NOT NULL ')

            if self._config.extendedCoordinates :
                query += (',maxX FLOAT NOT NULL ,maxY FLOAT NOT NULL ,maxZ FLOAT NOT NULL '
                          ',minX FLOAT NOT NULL ,minY FLOAT NOT NULL ,minZ FLOAT NOT NULL ')
            query += ');'
            cur.execute(query)

            #SolarSystems - SQLite
            query = ('CREATE TABLE IF NOT EXISTS mapSolarSystems (solarSystemId INT NOT NULL PRIMARY KEY'
                    ',solarSystemName TEXT NOT NULL ,constellationId INT NOT NULL REFERENCES '
                    'mapConstellations(constellationId) ON UPDATE CASCADE ON DELETE SET NULL'
                    ',corridor BOOL NOT NULL ,fringe BOOL NOT NULL ,hub BOOL NOT NULL ,international BOOL NOT NULL'
                    ',luminosity FLOAT NOT NULL ,radius FLOAT NOT NULL '
                    ',centerX FLOAT NOT NULL ,centerY FLOAT NOT NULL ,centerZ FLOAT NOT NULL ')
            cur.execute(query)

            if self._config.extendedCoordinates :
                query += (',maxX FLOAT NOT NULL ,maxY FLOAT NOT NULL ,maxZ FLOAT NOT NULL '
                          ',minX FLOAT NOT NULL ,minY FLOAT NOT NULL ,minZ FLOAT NOT NULL ')

            query += (',regional BOOL NOT NULL, security FLOAT NOT NULL, securityClass FLOAT NOT NULL '
                      ');')
            cur.execute(query)

            #Gates - SQLite (typeId here)
            query = ('CREATE TABLE IF NOT EXISTS mapSystemGates (systemGateId INT NOT NULL '
                     ',solarSystemID INT NOT NULL REFERENCES mapSolarSystems(solarSystemId) '
                     'ON UPDATE CASCADE ON DELETE SET NULL ,typeId INT NOT NULL '
                     'REFERENCES invTypes(typeId) ON UPDATE CASCADE ON DELETE SET NULL '
                     ',positionX FLOAT NOT NULL ,positionY FLOAT NOT NULL ,positionZ FLOAT NOT NULL '
                     ',CONSTRAINT pkey PRIMARY KEY (systemGateId,solarSystemID) ON CONFLICT FAIL '
                     ');')
            cur.execute(query)

            #Planets - SQLite (typeId here)
            query = ('CREATE TABLE IF NOT EXISTS mapPlanets (solarSystemId INT NOT NULL REFERENCES '
                    'mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL ,planetaryIndex INT NOT NULL '
                    ',fragmented BOOL NOT NULL ,radius FLOAT NOT NULL ,locked BOOL NOT NULL '
                    ',typeId INT NOT NULL REFERENCES invTypes(typeId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ',positionX FLOAT NOT NULL ,positionY FLOAT NOT NULL ,positionZ FLOAT NOT NULL '
                    ',CONSTRAINT pkey PRIMARY KEY (solarSystemId, planetaryIndex) ON CONFLICT FAIL '
                    ');')
            cur.execute(query)

            #Stars - SQLite (typeId Here)
            query = ('CREATE TABLE IF NOT EXISTS mapStars (starId INT NOT NULL PRIMARY KEY ,solarSystemId INT '
                    'NOT NULL REFERENCES mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ',locked BOOL NOT NULL ,radius INT NOT NULL '
                    ',typeId INT NOT NULL REFERENCES invTypes(typeId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ',CONSTRAINT pkey PRIMARY KEY (solarSystemId, starId) ON CONFLICT FAIL '
                    ');')
            cur.execute(query)

            #star index
            query = 'CREATE UNIQUE INDEX starId ON mapstars(starId);'
            cur.execute(query)

            #Moons - SQLite
            query = ('CREATE TABLE IF NOT EXISTS mapMoons (moonId INT NOT NULL ,solarSystemId INT '
                    'NOT NULL REFERENCES mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ',positionX FLOAT NOT NULL ,positionY FLOAT NOT NULL ,positionZ FLOAT NOT NULL '
                    ',typeId INT NOT NULL REFERENCES invTypes(typeId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ',radius INT NOT NULL ,CONSTRAINT pkey PRIMARY KEY (solarSystemId, moonId) ON CONFLICT FAIL '
                    ');')
            cur.execute(query)

            #star index
            query = 'CREATE UNIQUE INDEX moonId ON mapstars(moonId);'
            cur.execute(query)
        
    def parseData(self):
        universeDirectory = Path(self._yamlDirectory).joinpath('fsd','universe')
        if self._config.withKSpace:
            self._readDirectory(universeDirectory.joinpath('eve'))
        if self._config.withWSpace:
            self._readDirectory(universeDirectory.joinpath('wormhole'))
        if self._config.withAbbysal:
            self._readDirectory(universeDirectory.joinpath('abyssal'))
        if self._config.withVoid:
            self._readDirectory(universeDirectory.joinpath('void'))

    def _parseType(self):
        pass
    
    def _parseGroups(self):
        pass

    def _parseCategories(self):
        pass

    def _parseSolarSystem(self,pathObject):
        pass

    def _parseConstellation(self,pathObject):
        pass

    def _parseRegion(self,pathObject):
        pass

    @classmethod
    def fromFuzzworks(cls,databaseUrl):
        raise(NotImplementedError)

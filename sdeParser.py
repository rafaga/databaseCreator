#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
""" This script provides a Class to parse SDE structure into a SQLite Database"""
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
    # this counter permits to detect what item we are iterating now
    _counter = -1
    # this representes the current location (Region,Constellation,System)
    _Location = [{"name":None, "id":None},{"name":None, "id":None},{"name":None, "id":None}]

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

    def _readDirectory(self, directoryPath): 
        for element in directoryPath.iterdir():
            if element.is_dir():
                self._counter += 1
                self._Location[self._counter]["name"] = element.name
                if self._counter < 2:
                    if self._counter == 0:
                        self._parseRegion(element.joinpath('region.staticdata'))
                    else:
                        self._parseConstellation(element.joinpath('constellation.staticdata'))
                self._readDirectory(element)
                self._counter -= 1
            if element.is_file() and self._counter == 2:
                if element.name == "solarsystem.staticdata":
                    print('SDE: parsing data for system ' + self._Location[self._counter]["name"])
                    self._parseSolarSystem(element)

    #Not used for now
    def spinner(self, value, lenght=3, width=7, message = None):
        print('[',end='')
        calculatedValue = (value%lenght)
        for x in range(0,width):
            if x >= calculatedValue  or x < calculatedValue-lenght:
                print('▉',end='')
            else:
                print(' ',end='')
        if message is not None:
            print('] ' + message)
        else:
            print(']')

    def createTableStructure(self):
        if self._dbType == DatabaseType.SQLITE:
            print("SDE: Using SQLite as Database Engine...")
            #categories - SQLite
            query = ('CREATE TABLE IF NOT EXISTS invCategories (categoryId INT NOT NULL PRIMARY KEY'
                     ',categoryName TEXT NOT NULL ,published BOOL NOT NULL);')
            self._dbDriver.execute(query,delayCommit=True)

            #GroupIds - SQLite
            query = ('CREATE TABLE IF NOT EXISTS invGroups (groupId INT NOT NULL PRIMARY KEY'
                     ',groupName TEXT NOT NULL ,categoryId INT NOT NULL REFERENCES invCategories(categoryId) '
                     'ON UPDATE CASCADE ON DELETE SET NULL, anchorable BOOL NOT NULL'
                     ');')
            self._dbDriver.execute(query,delayCommit=True)

            #InvType - SQLite
            query = ('CREATE TABLE IF NOT EXISTS invTypes (typeId INT NOT NULL PRIMARY KEY '
                    ',groupId INT REFERENCES invGroups(groupId) ON UPDATE CASCADE ON DELETE SET NULL'
                    ',iconId INT, typeName TEXT NOT NULL, published BOOL NOT NULL, volume FLOAT '
                    ');')
            self._dbDriver.execute(query,delayCommit=True)

            #Races - SQLite
            query = 'CREATE TABLE IF NOT EXISTS races (raceId INT NOT NULL PRIMARY KEY, raceName TEXT NOT NULL);'
            self._dbDriver.execute(query,delayCommit=True)

            #Corporations - SQLite TODO and WIP
            query = ('CREATE TABLE IF NOT EXISTS npcCorporations (corporationId INT NOT NULL PRIMARY KEY '
                     ',corporationName TEXT NOT NULL, tickerName TEXT NOT NULL, deleted BOOL NOT NULL'
                     ',iconId INT NOT NULL'
                     ',raceId INT REFERENCES races(raceId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ');')
            self._dbDriver.execute(query,delayCommit=True)


            #Factions - SQLite
            query = ('CREATE TABLE IF NOT EXISTS factions (factionId INT NOT NULL PRIMARY KEY, factionName TEXT NOT NULL '
                     ',iconId INT NOT NULL ,sizeFactor FLOAT NOT NULL ,uniqueName BOOL NOT NULL '
                     ',corporationId INT REFERENCES npcCorporations(corporationId) ON UPDATE CASCADE ON DELETE SET NULL '
                     ');')
            self._dbDriver.execute(query,delayCommit=True)

            #Faction-Races -SQLite
            query = ('CREATE TABLE IF NOT EXISTS factionRace ('
                     'factionId INT REFERENCES factions(factionId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',raceId INT REFERENCES races(raceId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',CONSTRAINT pkey PRIMARY KEY (factionId,raceId) ON CONFLICT FAIL);')
            self._dbDriver.execute(query,delayCommit=True)

            #Regions - SQLite
            query = ('CREATE TABLE IF NOT EXISTS mapRegions (regionId INT NOT NULL PRIMARY KEY'
                     ',regionName TEXT NOT NULL, nebula INT NOT NULL, wormholeClassId INT '
                     ',factionId INT REFERENCES factions(factionId) ON UPDATE CASCADE ON DELETE SET NULL '
                     ',centerX FLOAT NOT NULL ,centerY FLOAT NOT NULL ,centerZ FLOAT NOT NULL ')

            if self._config.extendedCoordinates :
                query += (',maxX FLOAT NOT NULL ,maxY FLOAT NOT NULL ,maxZ FLOAT NOT NULL '
                          ',minX FLOAT NOT NULL ,minY FLOAT NOT NULL ,minZ FLOAT NOT NULL ')
            query += ');'
            self._dbDriver.execute(query,delayCommit=True)

            #Constelations - SQLite
            query = ('CREATE TABLE IF NOT EXISTS mapConstellations (constellationId INT NOT NULL PRIMARY KEY '
                     ',constellationName TEXT NOT NULL ,regionId INT NOT NULL REFERENCES '
                     'mapRegions(regionId) ON UPDATE CASCADE ON DELETE SET NULL ,radius FLOAT NOT NULL '
                     ',centerX FLOAT NOT NULL ,centerY FLOAT NOT NULL ,centerZ FLOAT NOT NULL ')

            if self._config.extendedCoordinates :
                query += (',maxX FLOAT NOT NULL ,maxY FLOAT NOT NULL ,maxZ FLOAT NOT NULL '
                          ',minX FLOAT NOT NULL ,minY FLOAT NOT NULL ,minZ FLOAT NOT NULL ')
            query += ');'
            self._dbDriver.execute(query,delayCommit=True)

            #SolarSystems - SQLite
            query = ('CREATE TABLE IF NOT EXISTS mapSolarSystems (solarSystemId INT NOT NULL PRIMARY KEY'
                    ',solarSystemName TEXT NOT NULL ,constellationId INT NOT NULL REFERENCES '
                    'mapConstellations(constellationId) ON UPDATE CASCADE ON DELETE SET NULL'
                    ',corridor BOOL NOT NULL ,fringe BOOL NOT NULL ,hub BOOL NOT NULL ,international BOOL NOT NULL'
                    ',luminosity FLOAT NOT NULL ,radius FLOAT NOT NULL '
                    ',centerX FLOAT NOT NULL ,centerY FLOAT NOT NULL ,centerZ FLOAT NOT NULL ')

            if self._config.extendedCoordinates :
                query += (',maxX FLOAT NOT NULL ,maxY FLOAT NOT NULL ,maxZ FLOAT NOT NULL '
                          ',minX FLOAT NOT NULL ,minY FLOAT NOT NULL ,minZ FLOAT NOT NULL ')

            query += (',regional BOOL NOT NULL, security FLOAT NOT NULL, securityClass FLOAT NOT NULL '
                      ');')
            self._dbDriver.execute(query,delayCommit=True)

            #faction/solarsystem- - SQLite
            query = ('CREATE TABLE IF NOT EXISTS factionSolarSystem ('
                     'solarSystemId INT REFERENCES mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',factionId INT REFERENCES factions(factionId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',CONSTRAINT pkey PRIMARY KEY (solarSystemId,factionId) ON CONFLICT FAIL'
                     ');')
            self._dbDriver.execute(query,delayCommit=True)

            #faction/solarSystem Index
            query = 'CREATE UNIQUE INDEX factionId ON factionSolarSystem (factionId);'
            self._dbDriver.execute(query,delayCommit=True)

            #Gates - SQLite (typeId here)
            query = ('CREATE TABLE IF NOT EXISTS mapSystemGates (systemGateId INT NOT NULL '
                     ',solarSystemID INT NOT NULL REFERENCES mapSolarSystems(solarSystemId) '
                     'ON UPDATE CASCADE ON DELETE SET NULL ,typeId INT NOT NULL '
                     'REFERENCES invTypes(typeId) ON UPDATE CASCADE ON DELETE SET NULL '
                     ',positionX FLOAT NOT NULL ,positionY FLOAT NOT NULL ,positionZ FLOAT NOT NULL '
                     ',CONSTRAINT pkey PRIMARY KEY (systemGateId,solarSystemID) ON CONFLICT FAIL '
                     ');')
            self._dbDriver.execute(query,delayCommit=True)

            #Planets - SQLite (typeId here)
            query = ('CREATE TABLE IF NOT EXISTS mapPlanets (solarSystemId INT REFERENCES '
                    'mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL ,planetaryIndex INT NOT NULL '
                    ',fragmented BOOL NOT NULL ,radius FLOAT NOT NULL ,locked BOOL NOT NULL '
                    ',typeId INT NOT NULL REFERENCES invTypes(typeId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ',positionX FLOAT NOT NULL ,positionY FLOAT NOT NULL ,positionZ FLOAT NOT NULL '
                    ',CONSTRAINT pkey PRIMARY KEY (solarSystemId, planetaryIndex) ON CONFLICT FAIL '
                    ');')
            self._dbDriver.execute(query,delayCommit=True)

            #Stars - SQLite (typeId Here)
            query = ('CREATE TABLE IF NOT EXISTS mapStars (starId INT NOT NULL PRIMARY KEY ,solarSystemId INT '
                    'REFERENCES mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ',locked BOOL NOT NULL ,radius INT NOT NULL '
                    ',typeId INT NOT NULL REFERENCES invTypes(typeId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ');')
            self._dbDriver.execute(query,delayCommit=True)

            #star index
            query = 'CREATE UNIQUE INDEX starId ON mapStars (solarSystemId, starId);'
            self._dbDriver.execute(query,delayCommit=True)

            #Moons - SQLite
            query = ('CREATE TABLE IF NOT EXISTS mapMoons (moonId INT NOT NULL ,solarSystemId INT '
                    'NOT NULL REFERENCES mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ',positionX FLOAT NOT NULL ,positionY FLOAT NOT NULL ,positionZ FLOAT NOT NULL '
                    ',typeId INT NOT NULL REFERENCES invTypes(typeId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ',radius INT NOT NULL ,CONSTRAINT pkey PRIMARY KEY (solarSystemId, moonId) ON CONFLICT FAIL '
                    ');')
            self._dbDriver.execute(query,delayCommit=True)

            #Stations - SQLite
            query = ('CREATE TABLE IF EXISTS staStation (idStation INT NOT NULL PRIMARY KEY ,stationName TEXT NOT NULL'
                     ',solarSystemId INT REFERENCES mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',stationType INT NOT NULL'
                     ');')

            # Corporation/Station - SQLite
            # ',stationId INT REFERENCES stations(stationId) ON UPDATE CASCADE ON DELETE SET NULL'
            query = ('CREATE TABLE IF EXISTS staCorporations ('
                    ',solarSystemId INT REFERENCES mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL'
                    ',corporationId INT REFERENCES npcCorporations(corporationId) ON UPDATE CASCADE ON DELETE SET NULL'
                    ',CONSTRAINT pkey PRIMARY KEY (solarSystemId, corporationId) ON CONFLICT FAIL '
                    ');')


            #star index
            query = 'CREATE UNIQUE INDEX moonId ON mapMoons(moonId);'
            self._dbDriver.execute(query,delayCommit=True)

            self._dbDriver.connection.commit()
            print("SDE: Tables created from scratch...")
        
    def parseData(self):
        self._parseCategories(Path(self._yamlDirectory).joinpath('fsd','categoryIDs.yaml'))
        self._parseGroups(Path(self._yamlDirectory).joinpath('fsd','groupIDs.yaml'))
        self._parseTypes(Path(self._yamlDirectory).joinpath('fsd','typeIDs.yaml'))
        universeDirectory = Path(self._yamlDirectory).joinpath('fsd','universe')
        if self._config.mapKSpace:
            print('SDE: parsing High,Low and Nullsec Systems')
            self._readDirectory(universeDirectory.joinpath('eve'))
        if self._config.mapWSpace:
            print('SDE: parsing Wormhole Systems')
            self._readDirectory(universeDirectory.joinpath('wormhole'))
        if self._config.mapAbbysal:
            print('SDE: parsing Abyssal Systems')
            self._readDirectory(universeDirectory.joinpath('abyssal'))
        if self._config.mapVoid:
            print('SDE: parsing Void Systems')
            self._readDirectory(universeDirectory.joinpath('void'))

    def _parseTypes(self,pathObject):
        with pathObject.open() as file:
            yTypes = yaml.safe_load(file)
            total = len(yTypes)
            cont=0
            for type in yTypes.items():
                params = {}
                query = ('INSERT INTO invTypes(typeId, groupId, typeName, iconId, published, volume) VALUES (:id ,:groupId, :name, :iconId, :published, :volume)')
                params['id'] = type[0]
                params['name'] = type[1]['name']['en']
                params['groupId'] = type[1]["groupID"]
                if 'iconID' in type[1]:
                    params['iconId'] = type[1]["iconID"]
                else:
                    params['iconId'] = None
                params['published'] =  type[1]["published"]
                if 'volume' in type[1]:
                    params['volume'] = type[1]["volume"]
                else:
                    params['volume'] = None
                self._dbDriver.execute(query, params)
                cont+=1
                print(f'SDE: parsing {total} Types [{round((cont / total)*100,2)}%]  \r',end="")
            print(f'SDE: {total} Types parsed           ')
    
    def _parseGroups(self,pathObject):
        with pathObject.open() as file:
            yGroups = yaml.safe_load(file)
            total = len(yGroups)
            cont=0
            for group in yGroups.items():
                params = {}
                query = ('INSERT INTO invGroups(groupId, categoryId, groupName, anchorable) VALUES (:id ,:catId, :name, :anchor)')
                params['id'] = group[0]
                params['catId'] = group[1]["categoryID"]
                params['name'] = group[1]["name"]["en"]
                params['anchor'] = group[1]["anchorable"]
                cont+=1
                self._dbDriver.execute(query, params)
                print(f'SDE: parsing {total} groups [{round((cont / total)*100,2)}%]  \r',end="")
            print(f'SDE: {total} Groups parsed            ')

    def _parseCategories(self,pathObject):
        with pathObject.open() as file:
            yCategories = yaml.safe_load(file)
            total = len(yCategories)
            cont=0
            for category in yCategories.items():
                params = {}
                query = ('INSERT INTO invCategories(categoryID, categoryName, published) VALUES (:id ,:name, :publish)')
                params['id'] = category[0]
                params['name'] = category[1]["name"]["en"]
                params['publish'] = category[1]["published"]
                cont+=1
                print(f'SDE: parsing {total} categories [{round((cont / total)*100,2)}%]  \r',end="")
                self._dbDriver.execute(query, params)
            print(f'SDE: {total} Categories parsed          ')

    def _parseSolarSystem(self,pathObject):
        self._parseMoons('')
        self._parseGates('')
        self._parsePlanets('')
        self._parseStar('')

    def _parseConstellation(self,pathObject):
        with pathObject.open() as file:
            element = yaml.safe_load(file)
            print('SDE: parsing data for constellation ' + self._Location[self._counter]["name"])
            params = {}
            query = ('INSERT INTO mapConstellations(constellationId ,constellationName ,regionId ,radius '
                        ',centerX ,centerY ,centerZ ')
            if self._config.extendedCoordinates:
                query += ',maxX ,maxY ,maxZ ,minX ,minY ,minZ'
            query += ') VALUES (:id ,:name ,:regionId ,:radius ,:centerX ,:centerY ,:centerZ '
            if self._config.extendedCoordinates:
                query += ',:maxX ,:maxY ,:maxZ ,:minX ,:minY ,:minZ'
            query += ')'
            params['id'] = element['constellationID']
            params['name'] = self._Location[self._counter]["name"]
            params['regionId'] = self._Location[0]["id"]
            params['radius'] = element["radius"]
            params['centerX'] = element["center"][0]
            params['centerY'] = element["center"][1]
            params['centerZ'] = element["center"][2]
            if self._config.extendedCoordinates:
                params['maxX'] = element["max"][0]
                params['maxY'] = element["max"][1]
                params['maxZ'] = element["max"][2]
                params['minX'] = element["min"][0]
                params['minY'] = element["min"][1]
                params['minZ'] = element["min"][2]
            self._dbDriver.execute(query, params)

    def _parseRegion(self,pathObject):
        print(pathObject.exists())
        with pathObject.open() as file:
            region = yaml.safe_load(file)
            print('SDE: parsing data for region ' + self._Location[self._counter]["name"])
            params = {}
            query = ('INSERT INTO mapRegions(regionId, regionName, factionId, centerX, centerY, centerZ'
                        ',nebula ,wormholeClassId ')
            if self._config.extendedCoordinates:
                query += ',maxX ,maxY ,maxZ ,minX ,minY ,minZ'
            query += ') VALUES (:id , :name, :factionId, :centerX, :centerY, :centerZ, :nebula, :whclass'
            if self._config.extendedCoordinates:
                query += ',:maxX ,:maxY ,:maxZ ,:minX ,:minY ,:minZ'
            query += ')'
            params['id'] = region['regionID']
            self._Location[self._counter]["id"] = region['regionID']
            params['name'] = self._Location[self._counter]["name"]
            params['nebula'] = region["nebula"]
            if 'wormholeClassID' in region:
                params['whclass'] =  region["wormholeClassID"]
            else:
                params['whclass'] = None
            params['centerX'] = region["center"][0]
            params['centerY'] = region["center"][1]
            params['centerZ'] = region["center"][2]
            if self._config.extendedCoordinates:
                params['maxX'] = region["max"][0]
                params['maxY'] = region["max"][1]
                params['maxZ'] = region["max"][2]
                params['minX'] = region["min"][0]
                params['minY'] = region["min"][1]
                params['minZ'] = region["min"][2]
            self._dbDriver.execute(query, params)
    
    def _parseGates(self,node):
        pass

    def _parseMoons(self,node):
        pass

    def _parsePlanets(self,node):
        pass

    def _parseStar(self,node):
        pass

    @classmethod
    def fromFuzzworks(cls,databaseUrl):
        raise(NotImplementedError)

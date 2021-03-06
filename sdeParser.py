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
    #TODO: implement these flags, these flags depend upon map Flags.
    mapMoons=True
    mapGates=True

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
        if type == DatabaseType.SQLITE:
            print("SDE: Using SQLite as Database Engine...")
        self._dbDriver = DatabaseDriver(type,databaseFile)
        self._dbType = type
        self._config = sdeConfig()

    def _readDirectory(self, directoryPath): 
        for element in directoryPath.iterdir():
            if element.is_dir():
                self._counter += 1
                if self._counter == 0:
                    self._parseRegion(element.joinpath('region.staticdata'))
                if self._counter == 1:
                    self._parseConstellation(element.joinpath('constellation.staticdata'))
                self._readDirectory(element)
                self._counter -= 1
            if element.is_file() and element.name == "solarsystem.staticdata":
                self._parseSolarSystem(element)

    #Not used for now
    def spinner(self, value, lenght=3, width=7, message = None):
        print('[',end='')
        calculatedValue = (value%lenght)
        for x in range(0,width):
            if x >= calculatedValue  or x < calculatedValue-lenght:
                print('???',end='')
            else:
                print(' ',end='')
        if message is not None:
            print('] ' + message)
        else:
            print(']')

    def createTableStructure(self):
        if self._dbType == DatabaseType.SQLITE:
            cur = self._dbDriver.connection.cursor()
            query = 'CREATE TABLE invNames (itemId INT NOT NULL PRIMARY KEY, itemName TEXT NOT NULL);'
            cur.execute(query)

            #categories - SQLite
            query = ('CREATE TABLE invCategories (categoryId INT NOT NULL PRIMARY KEY'
                     ',categoryName TEXT NOT NULL ,published BOOL NOT NULL);')
            cur.execute(query)

            #GroupIds - SQLite
            query = ('CREATE TABLE invGroups (groupId INT NOT NULL PRIMARY KEY'
                     ',groupName TEXT NOT NULL ,categoryId INT NOT NULL REFERENCES invCategories(categoryId) '
                     'ON UPDATE CASCADE ON DELETE SET NULL, anchorable BOOL NOT NULL'
                     ');')
            cur.execute(query)

            #InvType - SQLite
            query = ('CREATE TABLE invTypes (typeId INT NOT NULL PRIMARY KEY '
                    ',groupId INT REFERENCES invGroups(groupId) ON UPDATE CASCADE ON DELETE SET NULL'
                    ',iconId INT, typeName TEXT NOT NULL, published BOOL NOT NULL, volume FLOAT '
                    ');')
            cur.execute(query)

            #Races - SQLite
            query = 'CREATE TABLE races (raceId INT NOT NULL PRIMARY KEY, raceName TEXT NOT NULL);'
            cur.execute(query)

            #Corporations - SQLite TODO and WIP
            query = ('CREATE TABLE npcCorporations (corporationId INT NOT NULL PRIMARY KEY '
                     ',corporationName TEXT NOT NULL, tickerName TEXT NOT NULL, deleted BOOL NOT NULL'
                     ',iconId INT NOT NULL'
                     ',raceId INT REFERENCES races(raceId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ');')
            cur.execute(query)


            #Factions - SQLite
            query = ('CREATE TABLE factions (factionId INT NOT NULL PRIMARY KEY, factionName TEXT NOT NULL '
                     ',iconId INT NOT NULL ,sizeFactor FLOAT NOT NULL ,uniqueName BOOL NOT NULL '
                     ',corporationId INT REFERENCES npcCorporations(corporationId) ON UPDATE CASCADE ON DELETE SET NULL '
                     ');')
            cur.execute(query)

            #Faction-Races -SQLite
            query = ('CREATE TABLE factionRace ('
                     'factionId INT REFERENCES factions(factionId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',raceId INT REFERENCES races(raceId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',CONSTRAINT pkey PRIMARY KEY (factionId,raceId) ON CONFLICT FAIL);')
            cur.execute(query)

            #Regions - SQLite
            query = ('CREATE TABLE mapRegions (regionId INT NOT NULL PRIMARY KEY'
                     ',regionName TEXT NOT NULL, nebula INT NOT NULL, wormholeClassId INT '
                     ',factionId INT REFERENCES factions(factionId) ON UPDATE CASCADE ON DELETE SET NULL '
                     ',centerX FLOAT NOT NULL ,centerY FLOAT NOT NULL ,centerZ FLOAT NOT NULL ')

            if self._config.extendedCoordinates :
                query += (',maxX FLOAT NOT NULL ,maxY FLOAT NOT NULL ,maxZ FLOAT NOT NULL '
                          ',minX FLOAT NOT NULL ,minY FLOAT NOT NULL ,minZ FLOAT NOT NULL ')
            query += ');'
            cur.execute(query)

            #Constelations - SQLite
            query = ('CREATE TABLE mapConstellations (constellationId INT NOT NULL PRIMARY KEY '
                     ',constellationName TEXT NOT NULL ,regionId INT NOT NULL REFERENCES '
                     'mapRegions(regionId) ON UPDATE CASCADE ON DELETE SET NULL ,radius FLOAT NOT NULL '
                     ',centerX FLOAT NOT NULL ,centerY FLOAT NOT NULL ,centerZ FLOAT NOT NULL ')

            if self._config.extendedCoordinates :
                query += (',maxX FLOAT NOT NULL ,maxY FLOAT NOT NULL ,maxZ FLOAT NOT NULL '
                          ',minX FLOAT NOT NULL ,minY FLOAT NOT NULL ,minZ FLOAT NOT NULL ')
            query += ');'
            cur.execute(query)

            #SolarSystems - SQLite
            query = ('CREATE TABLE mapSolarSystems (solarSystemId INT NOT NULL PRIMARY KEY'
                    ',solarSystemName TEXT NOT NULL ,constellationId INT REFERENCES '
                    'mapConstellations(constellationId) ON UPDATE CASCADE ON DELETE SET NULL'
                    ',corridor BOOL NOT NULL ,fringe BOOL NOT NULL ,hub BOOL NOT NULL ,international BOOL NOT NULL'
                    ',luminosity FLOAT NOT NULL ,radius FLOAT NOT NULL '
                    ',centerX FLOAT NOT NULL ,centerY FLOAT NOT NULL ,centerZ FLOAT NOT NULL ')

            if self._config.extendedCoordinates :
                query += (',maxX FLOAT NOT NULL ,maxY FLOAT NOT NULL ,maxZ FLOAT NOT NULL '
                          ',minX FLOAT NOT NULL ,minY FLOAT NOT NULL ,minZ FLOAT NOT NULL ')

            query += (',regional BOOL NOT NULL, security FLOAT NOT NULL, securityClass TEXT'
                      ');')
            cur.execute(query)

            #faction/solarsystem- - SQLite
            query = ('CREATE TABLE factionSolarSystem ('
                     'solarSystemId INT REFERENCES mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',factionId INT REFERENCES factions(factionId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',CONSTRAINT pkey PRIMARY KEY (solarSystemId,factionId) ON CONFLICT FAIL'
                     ');')
            cur.execute(query)

            #faction/solarSystem Index
            query = 'CREATE UNIQUE INDEX factionId ON factionSolarSystem (factionId);'
            cur.execute(query)

            #Gates - SQLite (typeId here)
            query = ('CREATE TABLE mapSystemGates (systemGateId INT NOT NULL '
                     ',solarSystemID INT NOT NULL REFERENCES mapSolarSystems(solarSystemId) '
                     'ON UPDATE CASCADE ON DELETE SET NULL ,typeId INT NOT NULL '
                     'REFERENCES invTypes(typeId) ON UPDATE CASCADE ON DELETE SET NULL '
                     ',positionX FLOAT NOT NULL ,positionY FLOAT NOT NULL ,positionZ FLOAT NOT NULL '
                     ',CONSTRAINT pkey PRIMARY KEY (systemGateId,solarSystemID) ON CONFLICT FAIL '
                     ');')
            cur.execute(query)

            #Planets - SQLite (typeId here)
            query = ('CREATE TABLE mapPlanets (planetId INT NOT NULL PRIMARY KEY'
                    ',solarSystemId INT REFERENCES mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL'
                    ' ,planetaryIndex INT NOT NULL, fragmented BOOL NOT NULL, radius FLOAT NOT NULL, locked BOOL NOT NULL '
                    ',typeId INT NOT NULL REFERENCES invTypes(typeId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ',positionX FLOAT NOT NULL ,positionY FLOAT NOT NULL ,positionZ FLOAT NOT NULL '
                    ');')
            cur.execute(query)

            query = 'CREATE UNIQUE INDEX planetSystem ON mapPlanets(solarSystemId, planetaryIndex);'
            cur.execute(query)

            #Stars - SQLite (typeId Here)
            query = ('CREATE TABLE mapStars (starId INT NOT NULL PRIMARY KEY ,solarSystemId INT '
                    'REFERENCES mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ',locked BOOL NOT NULL ,radius INT NOT NULL '
                    ',typeId INT NOT NULL REFERENCES invTypes(typeId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ');')
            cur.execute(query)

            #star index
            query = 'CREATE UNIQUE INDEX starId ON mapStars (solarSystemId, starId);'
            cur.execute(query)

            #Moons - SQLite
            query = ('CREATE TABLE mapMoons (moonId INT NOT NULL ,solarSystemId INT '
                    'REFERENCES mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL, '
                    'moonIndex INT NOT NULL, positionX FLOAT NOT NULL ,positionY FLOAT NOT NULL , '
                    'positionZ FLOAT NOT NULL, radius INT,'
                    'typeId INT REFERENCES invTypes(typeId) ON UPDATE CASCADE ON DELETE SET NULL '
                    ',CONSTRAINT pkey PRIMARY KEY (solarSystemId, moonId) ON CONFLICT FAIL '
                    ');')
            cur.execute(query)

            #Stations - SQLite
            query = ('CREATE TABLE staStation (idStation INT NOT NULL PRIMARY KEY ,stationName TEXT NOT NULL'
                     ',solarSystemId INT REFERENCES mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',stationType INT NOT NULL'
                     ');')

            # Corporation/Station - SQLite
            # ',stationId INT REFERENCES stations(stationId) ON UPDATE CASCADE ON DELETE SET NULL'
            query = ('CREATE TABLE staCorporations ('
                    ',solarSystemId INT REFERENCES mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL'
                    ',corporationId INT REFERENCES npcCorporations(corporationId) ON UPDATE CASCADE ON DELETE SET NULL'
                    ',CONSTRAINT pkey PRIMARY KEY (solarSystemId, corporationId) ON CONFLICT FAIL '
                    ');')


            #star index
            query = 'CREATE UNIQUE INDEX moonId ON mapMoons(moonId);'
            cur.execute(query)

            self._dbDriver.connection.commit()
            cur.close()
            print("SDE: Tables created from scratch...")
        
    def parseData(self):
        self._parseNames()
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
        cur = self._dbDriver.connection.cursor()
        query = ('INSERT INTO invTypes(typeId, groupId, typeName, iconId, published, volume) VALUES (:id ,:groupId, :name, :iconId, :published, :volume)')
        with pathObject.open() as file:
            yTypes = yaml.safe_load(file)
            total = len(yTypes)
            cont=0
            for type in yTypes.items():
                params = {}
                params['id'] = type[0]
                params['name'] = type[1]['name']['en']
                params['groupId'] = type[1]["groupID"]
                params['iconId'] = None
                if 'iconID' in type[1]:
                    params['iconId'] = type[1]["iconID"]
                params['published'] =  type[1]["published"]
                params['volume'] = None
                if 'volume' in type[1]:
                    params['volume'] = type[1]["volume"]
                cur.execute(query, params)
                cont+=1
                print(f'SDE: parsing {total} Types [{round((cont / total)*100,2)}%]  \r',end="")
            print(f'SDE: {total} Types parsed           ')
        cur.close()
    
    def _parseGroups(self,pathObject):
        cur = self._dbDriver.connection.cursor()
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
                cur.execute(query, params)
                print(f'SDE: parsing {total} groups [{round((cont / total)*100,2)}%]  \r',end="")
            print(f'SDE: {total} Groups parsed            ')
        cur.close()

    def _parseCategories(self,pathObject):
        cur = self._dbDriver.connection.cursor()
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
                cur.execute(query, params)
            print(f'SDE: {total} Categories parsed          ')
        cur.close()

    def _parseSolarSystem(self,pathObject):
        cur = self._dbDriver.connection.cursor()
        params = {}

        #query creation
        query = ('INSERT INTO mapSolarSystems (solarSystemId ,solarSystemName ,constellationId '
            ',corridor ,fringe ,hub ,international ,luminosity ,radius ,centerX ,centerY ,centerZ '
            ',regional ,security ,securityClass ')
        if self._config.extendedCoordinates :
            query += ',maxX ,maxY ,maxZ ,minX ,minY ,minZ '     
        query += (') VALUES ( :id, :name, :constellationId, :corridor, :fringe, :hub, :international, '
                    ':luminosity, :radius, :centerX, :centerY, :centerZ, :regional, :security, :securityClass')  
        if self._config.extendedCoordinates :
            query += ',:maxX ,:maxY ,:maxZ ,:minX ,:minY ,:minZ '
        query += ');'

        with pathObject.open() as file:
            element = yaml.safe_load(file)

            #set the solar system Id
            self._Location[self._counter]['id'] = element['solarSystemID']
            self._Location[self._counter]['name'] = self._getName(element['solarSystemID'])
            print('SDE: parsing data for system ' + self._Location[self._counter]["name"])

            params['id'] = element['solarSystemID']
            params['name'] = self._Location[self._counter]['name']
            params['constellationId'] = self._Location[1]['id']
            params['corridor'] = element['corridor']
            params['fringe'] = element['fringe']
            params['hub'] = element['hub']
            params['international'] = element['international']
            params['luminosity'] = element['luminosity']
            params['radius'] = element['radius']
            params['centerX'] = element['center'][0]
            params['centerY'] = element['center'][1]
            params['centerZ'] = element['center'][2]
            if self._config.extendedCoordinates :
                params['minX'] = element['min'][0]
                params['minY'] = element['min'][1]
                params['minZ'] = element['min'][2]
                params['maxX'] = element['max'][0]
                params['maxY'] = element['max'][1]
                params['maxZ'] = element['max'][2]
            params['regional'] = element['regional']
            params['security'] = element['security']
            params['securityClass'] = None
            if 'securityClass' in element:
                params['securityClass'] = element['securityClass']
            cur.execute(query, params)

            self._parseGates(element['stargates'])
            self._parsePlanets(element['planets'])
            self._parseStar(element['star'])
        cur.close()

    def _parseConstellation(self,pathObject):
        cur = self._dbDriver.connection.cursor()
        #query creation
        query = ('INSERT INTO mapConstellations (constellationId ,constellationName ,regionId ,radius '
            ',centerX ,centerY ,centerZ ')
        if self._config.extendedCoordinates:
            query += ',maxX ,maxY ,maxZ ,minX ,minY ,minZ'
        query += ') VALUES (:id ,:name ,:regionId ,:radius ,:centerX ,:centerY ,:centerZ '
        if self._config.extendedCoordinates:
            query += ',:maxX ,:maxY ,:maxZ ,:minX ,:minY ,:minZ'
        query += ')'
        with pathObject.open() as file:
            element = yaml.safe_load(file)

            self._Location[self._counter]["id"] = element['constellationID']
            self._Location[self._counter]["name"] = self._getName(element['constellationID'])

            print('SDE: parsing data for constellation ' + self._Location[self._counter]["name"])
            params = {}
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
            cur.execute(query, params)
        cur.close()

    def _parseRegion(self,pathObject):
        cur = self._dbDriver.connection.cursor()
        #query creation
        query = ('INSERT INTO mapRegions(regionId, regionName, factionId, centerX, centerY, centerZ'
            ',nebula ,wormholeClassId ')
        if self._config.extendedCoordinates:
            query += ',maxX ,maxY ,maxZ ,minX ,minY ,minZ'
        query += ') VALUES (:id , :name, :factionId, :centerX, :centerY, :centerZ, :nebula, :whclass'
        if self._config.extendedCoordinates:
            query += ',:maxX ,:maxY ,:maxZ ,:minX ,:minY ,:minZ'
        query += ')'

        with pathObject.open() as file:
            region = yaml.safe_load(file)
            self._Location[self._counter]["id"] = region['regionID']
            self._Location[self._counter]["name"] = self._getName(region['regionID'])

            print('SDE: parsing data for region ' + self._Location[self._counter]["name"])
            params = {}
            params['id'] = region['regionID']
            params['name'] = self._Location[self._counter]["name"]
            params['factionId'] = None
            if 'factionID' in region:
                params['factionId'] = region['factionID']
            params['nebula'] = region["nebula"]
            params['whclass'] = None
            if 'wormholeClassID' in region:
                params['whclass'] =  region["wormholeClassID"]
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
            cur.execute(query, params)
        cur.close()
    
    def _parseGates(self,node):
        cur = self._dbDriver.connection.cursor()
        query = ('INSERT INTO mapSystemGates (systemGateId, solarSystemId, typeId, positionX, positionY, positionZ)'
            ' VALUES (:id, :solarSystemId, :typeId, :posX, :posY, :posZ );')
        for element in node.items():
            params = {}
            params['id'] = element[0]
            params['solarSystemId'] = self._Location[2]["id"]
            params['typeId'] = element[1]['typeID']
            params['posX'] = element[1]['position'][0]
            params['posY'] = element[1]['position'][1]
            params['posZ'] = element[1]['position'][2]
            cur.execute(query,params)
        cur.close()

    def _parseMoons(self,node):
        cur = self._dbDriver.connection.cursor()
        cont = 1
        query = ('INSERT INTO mapMoons (moonId, solarSystemId, moonIndex, typeid, radius, positionX, '
            'positionY, positionZ) VALUES (:id, :solarSystemId, :moonIndex, :typeId, :radius, :posX, '
            ':posY, :posZ );')
        for element in node.items():
            params = {}
            params['id'] = element[0]
            params['solarSystemId'] = self._Location[2]['id']
            params['moonIndex'] = cont
            params['typeId'] = element[1]["typeID"]
            params['radius'] = None
            if 'statistics' in element[1]:
                params['radius'] = element[1]['statistics']['radius']
            params['posX'] = element[1]['position'][0]
            params['posY'] = element[1]['position'][1]
            params['posZ'] = element[1]['position'][2]
            cur.execute(query,params)
            cont += 1
        cur.close()


    def _parsePlanets(self,node):
        cur = self._dbDriver.connection.cursor()
        query = ('INSERT INTO mapPlanets (planetId, solarSystemId, planetaryIndex, fragmented, radius, locked, typeId,'
                 'positionX, positionY, positionZ) VALUES (:id, :solarSystemId, :planetIndex, :fragmented, :radius, '
                 ':locked, :typeId, :posX, :posY, :posZ );')
        for element in node.items():
            params = {}
            params['id'] = element[0]
            params['solarSystemId'] = self._Location[2]["id"]
            params['planetIndex'] = element[1]['celestialIndex']
            params['fragmented'] = element[1]['statistics']['fragmented']
            params['radius'] = element[1]['statistics']['radius']
            params['locked'] = element[1]['statistics']['locked']
            params['typeId'] = element[1]['typeID']
            params['posX'] = element[1]['position'][0]
            params['posY'] = element[1]['position'][1]
            params['posZ'] = element[1]['position'][2]
            cur.execute(query,params)
            if 'moons' in element[1]:
                self._parseMoons(element[1]['moons'])
        cur.close()

    def _parseStar(self,node):
        params = {}
        cur = self._dbDriver.connection.cursor()
        query = ('INSERT INTO mapStars ( starId, solarSystemId, locked, radius, typeId ) VALUES '
                 '(:starId, :solarSystemId, :locked, :radius, :typeId)')
        params['starId'] = node['id']
        params['solarSystemId'] = self._Location[2]['id']
        params['locked'] = node['statistics']['locked']
        params['radius'] = node['statistics']['radius']
        params['typeId'] = node['typeID']
        cur.execute(query, params)
        cur.close()

    def _parseNames(self):
        cur = self._dbDriver.connection.cursor()
        """Load the all the names used by entities and dump it into a temp table"""
        namesFile = Path(self.yamlDirectory).joinpath('bsd','invNames.yaml')
        if not namesFile.exists():
            raise(FileNotFoundError)
        
        query = 'INSERT INTO invNames (itemId, itemName) VALUES (:id, :name);'
        with namesFile.open() as file:
            names = yaml.safe_load(file)

        total = len(names)
        cont = 0
        for name in names:
            params = {}
            params['id'] = name['itemID']
            params['name'] = name['itemName']
            cur.execute(query,params)
            cont+=1
            print(f'SDE: Parsing {total} names [{round((cont / total)*100,2)}%]  \r',end="")
        cur.close()
        print(f'SDE: {total} names parsed                  ')

    def _getName(self,id):
        result = ''
        cur = self._dbDriver.connection.cursor()
        query = 'SELECT itemName FROM invNames WHERE itemId = ?;'
        rows = cur.execute(query,(id,))
        for row in rows:
            result = row[0]
        cur.close()
        return result

    def close(self):
        """Drop unnecesary data, commit transactions and close the database"""
        query = 'DROP TABLE invNames;'
        cur = self._dbDriver.connection.cursor()
        cur.execute(query)
        self._dbDriver.connection.commit()
        if self._dbType == DatabaseType.SQLITE:
            query = 'VACUUM;'
            cur.execute(query)
        cur.close()

    @classmethod
    def fromFuzzworks(cls,databaseUrl):
        raise(NotImplementedError)

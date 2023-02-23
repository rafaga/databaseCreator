#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
""" This script provides a Class to parse SDE structure into a SQLite Database"""
from pathlib import Path
import yaml
from database_driver import DatabaseDriver, DatabaseType
from data_object import GenericEntity


class SdeConfig:
    """
    Provides default configuration for importing data from SDE
    """
    extended_coordinates = True
    map_kspace = True
    map_wspace = True
    map_abbysal = True
    map_void = False

    # TODO: implement these flags, these flags depend upon map Flags.
    with_moons = True
    with_gates = True
    with_star_catalog = True


class Data_Brigde():
    __star_group_id = 0
    __star_type_id = {}

    @property
    def star_group_id(self):
        """
        Property to get Star GroupID
        """
        return self.__star_group_id

    @star_group_id.setter
    def star_group_id(self, value):
        """
        Property to set Star GroupID
        """
        if isinstance(value,int):
            self.__star_group_id = value

    @property
    def star(self, type_id):
        return self.__star_type_id[type_id]

    @star.setter
    def star(self, type_id, value):
        self.__star_type_id[type_id] = value


class DirectoryNotFoundError(Exception):
    """
    Generic class for Directory Not found error
    """


class SdeParser:
    # Propiedades
    _yaml_directory = None
    _db_driver = None
    _db_type = None
    _config = SdeConfig()
    # this counter permits to detect what item we are iterating now
    _counter = -1
    # this representes the current location (Region,Constellation,System)
    _Location = [{"name": None, "id": None}, {"name": None, "id": None}, {"name": None, "id": None}]
    _stars = GenericEntity()

    @property
    def configuration(self):
        return self._config

    @property
    def yaml_directory(self):
        """the database file name"""
        return self._yaml_directory

    @yaml_directory.setter
    def yaml_directory(self, filename):
        self._yaml_directory = filename

    # Constructor
    def __init__(self, directory, database_file, db_type=DatabaseType.SQLITE):
        if Path(directory).is_dir():
            self.yaml_directory = directory
        else:
            raise DirectoryNotFoundError('The specified directory does not exists.')
        if db_type == DatabaseType.SQLITE:
            print("SDE: Using SQLite as Database Engine...")
        self._db_driver = DatabaseDriver(db_type, database_file)
        self._db_type = db_type
        self._config = SdeConfig()

    def _read_directory(self, directory_path):
        for element in directory_path.iterdir():
            if element.is_dir():
                self._counter += 1
                if self._counter == 0:
                    self._parse_region(element.joinpath('region.staticdata'))
                if self._counter == 1:
                    self._parse_constellation(element.joinpath('constellation.staticdata'))
                self._read_directory(element)
                self._counter -= 1
            if element.is_file() and element.name == "solarsystem.staticdata":
                self._parse_solar_system(element)

    # Not used for now
    def spinner(self, value, lenght=3, width=7, message=None):
        """
        This method prints a spinner on terminal screen (Not used)
        """
        print('[', end='')
        calculated_value = (value % lenght)
        for character in range(0, width):
            if character >= calculated_value or character < calculated_value - lenght:
                print('▉', end='')
            else:
                print(' ', end='')
        if message is not None:
            print('] ' + message)
        else:
            print(']')

    def create_table_structure(self):
        """
        This method create the database Structure to populate the data from SDE and external sources
        """
        if self._db_type == DatabaseType.SQLITE:
            cur = self._db_driver.connection.cursor()
            query = ('CREATE TABLE invNames (itemId INT NOT NULL PRIMARY KEY '
                     ',itemName TEXT NOT NULL);')
            cur.execute(query)

            # categories - SQLite
            query = ('CREATE TABLE invCategories (categoryId INT NOT NULL PRIMARY KEY'
                     ',categoryName TEXT NOT NULL ,published BOOL NOT NULL);')
            cur.execute(query)

            # GroupIds - SQLite
            query = ('CREATE TABLE invGroups (groupId INT NOT NULL PRIMARY KEY '
                     ',groupName TEXT NOT NULL ,categoryId INT NOT NULL REFERENCES '
                     'invCategories(categoryId) ON UPDATE CASCADE ON DELETE SET NULL, '
                     'anchorable BOOL NOT NULL);')
            cur.execute(query)

            # InvType - SQLite
            query = ('CREATE TABLE invTypes (typeId INT NOT NULL PRIMARY KEY '
                     ',groupId INT REFERENCES invGroups(groupId) ON UPDATE CASCADE '
                     'ON DELETE SET NULL ,iconId INT, typeName TEXT NOT NULL,'
                     'published BOOL NOT NULL, volume FLOAT );')
            cur.execute(query)

            # Races - SQLite
            query = 'CREATE TABLE races (raceId INT NOT NULL PRIMARY KEY, raceName TEXT NOT NULL);'
            cur.execute(query)

            # Corporations - SQLite TODO and WIP
            query = ('CREATE TABLE npcCorporations (corporationId INT NOT NULL PRIMARY KEY '
                     ',corporationName TEXT NOT NULL, tickerName TEXT NOT NULL '
                     ',deleted BOOL NOT NULL ,iconId INT NOT NULL'
                     ',raceId INT REFERENCES races(raceId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ');')
            cur.execute(query)

            # Factions - SQLite
            query = ('CREATE TABLE factions (factionId INT NOT NULL PRIMARY KEY '
                     ',factionName TEXT NOT NULL ,iconId INT NOT NULL'
                     ',sizeFactor FLOAT NOT NULL ,uniqueName BOOL NOT NULL '
                     ',corporationId INT REFERENCES npcCorporations(corporationId) '
                     'ON UPDATE CASCADE ON DELETE SET NULL);')
            cur.execute(query)

            # Faction-Races -SQLite
            query = ('CREATE TABLE factionRace ('
                     'factionId INT REFERENCES factions(factionId) ON UPDATE CASCADE'
                     ' ON DELETE SET NULL '
                     ',raceId INT REFERENCES races(raceId) ON UPDATE CASCADE ON DELETE SET NULL '
                     ',CONSTRAINT pkey PRIMARY KEY (factionId,raceId) ON CONFLICT FAIL);')
            cur.execute(query)

            # Regions - SQLite
            query = ('CREATE TABLE mapRegions (regionId INT NOT NULL PRIMARY KEY'
                     ',regionName TEXT NOT NULL, nebula INT NOT NULL, wormholeClassId INT '
                     ',factionId INT REFERENCES factions(factionId) ON UPDATE CASCADE '
                     'ON DELETE SET NULL '
                     ',centerX FLOAT NOT NULL ,centerY FLOAT NOT NULL ,centerZ FLOAT NOT NULL ')

            if self._config.extended_coordinates:
                query += (',maxX FLOAT NOT NULL ,maxY FLOAT NOT NULL ,maxZ FLOAT NOT NULL '
                          ',minX FLOAT NOT NULL ,minY FLOAT NOT NULL ,minZ FLOAT NOT NULL ')
            query += ');'
            cur.execute(query)

            # Constelations - SQLite
            query = ('CREATE TABLE mapConstellations (constellationId INT NOT NULL PRIMARY KEY '
                     ',constellationName TEXT NOT NULL ,regionId INT NOT NULL REFERENCES '
                     'mapRegions(regionId) ON UPDATE CASCADE ON DELETE SET NULL ,radius FLOAT NOT NULL '
                     ',centerX FLOAT NOT NULL ,centerY FLOAT NOT NULL ,centerZ FLOAT NOT NULL ')

            if self._config.extended_coordinates:
                query += (',maxX FLOAT NOT NULL ,maxY FLOAT NOT NULL ,maxZ FLOAT NOT NULL '
                          ',minX FLOAT NOT NULL ,minY FLOAT NOT NULL ,minZ FLOAT NOT NULL ')
            query += ');'
            cur.execute(query)

            # SolarSystems - SQLite
            query = ('CREATE TABLE mapSolarSystems (solarSystemId INT NOT NULL PRIMARY KEY'
                     ',solarSystemName TEXT NOT NULL ,constellationId INT REFERENCES '
                     'mapConstellations(constellationId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',corridor BOOL NOT NULL ,fringe BOOL NOT NULL ,hub BOOL NOT NULL '
                     ',international BOOL NOT NULL ,luminosity FLOAT NOT NULL '
                     ',radius FLOAT NOT NULL ,centerX FLOAT NOT NULL ,centerY FLOAT NOT NULL '
                     ',centerZ FLOAT NOT NULL ')

            if self._config.extended_coordinates:
                query += (',maxX FLOAT NOT NULL ,maxY FLOAT NOT NULL ,maxZ FLOAT NOT NULL '
                          ',minX FLOAT NOT NULL ,minY FLOAT NOT NULL ,minZ FLOAT NOT NULL ')

            query += (',regional BOOL NOT NULL, security FLOAT NOT NULL, securityClass TEXT'
                      ');')
            cur.execute(query)

            # faction/solarsystem- - SQLite
            query = ('CREATE TABLE factionSolarSystem ('
                     'solarSystemId INT REFERENCES mapSolarSystems(solarSystemId)'
                     ' ON UPDATE CASCADE ON DELETE SET NULL'
                     ',factionId INT REFERENCES factions(factionId) ON UPDATE CASCADE'
                     ' ON DELETE SET NULL'
                     ',CONSTRAINT pkey PRIMARY KEY (solarSystemId,factionId)'
                     ');')
            cur.execute(query)

            # faction/solarSystem Index
            query = 'CREATE UNIQUE INDEX factionId ON factionSolarSystem (factionId);'
            cur.execute(query)

            # Gates - SQLite (typeId here)
            query = ('CREATE TABLE mapSystemGates (systemGateId INT NOT NULL '
                     ',solarSystemId INTEGER NOT NULL REFERENCES mapSolarSystems '
                     '(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL, '
                     'destination INTEGER REFERENCES mapSystemGates(systemGateId), '
                     'typeId INT NOT NULL REFERENCES invTypes(typeId) ON '
                     'UPDATE CASCADE ON DELETE SET NULL ,positionX FLOAT '
                     'NOT NULL, positionY FLOAT NOT NULL, positionZ FLOAT '
                     'NOT NULL, CONSTRAINT pkey PRIMARY KEY (systemGateId,solarSystemId) '
                     'ON CONFLICT FAIL );')
            cur.execute(query)

            # Planets - SQLite (typeId here)
            query = ('CREATE TABLE mapPlanets (planetId INT NOT NULL '
                     'PRIMARY KEY,solarSystemId INTEGER REFERENCES '
                     'mapSolarSystems(solarSystemId) ON UPDATE '
                     'CASCADE ON DELETE SET NULL,planetaryIndex INTEGER '
                     'NOT NULL, fragmented BOOL NOT NULL ,radius FLOAT '
                     'NOT NULL, locked BOOL NOT NULL ,typeId INT NOT '
                     'NULL REFERENCES invTypes(typeId) ON UPDATE CASCADE '
                     'ON DELETE SET NULL ,positionX FLOAT NOT NULL, '
                     'positionY FLOAT NOT NULL, positionZ FLOAT NOT NULL '
                     ');')
            cur.execute(query)

            query = ('CREATE UNIQUE INDEX planetSystem ON mapPlanets'
                     '(solarSystemId, planetaryIndex);')
            cur.execute(query)

            # type - Star - SQLite
            query = ('CREATE TABLE typeStar ('
                     'starTypeId INTEGER PRIMARY KEY AUTOINCREMENT,'
                     'typeId INTEGER NOT NULL REFERENCES invTypes(typeId) '
                     'ON UPDATE CASCADE ON DELETE CASCADE, '
                     'name VARCHAR(4) NOT NULL,'
                     'color VARCHAR(20) NOT NULL)')
            cur.execute(query)

            # Stars - SQLite (typeId Here)
            query = ('CREATE TABLE mapStars (starId INT NOT NULL PRIMARY KEY '
                     ',solarSystemId INTEGER REFERENCES mapSolarSystems'
                     '(solarSystemId) ON UPDATE CASCADE ON DELETE RESTRICT '
                     ',locked BOOL NOT NULL ,radius INTEGER NOT NULL, '
                     'starTypeId INT NOT NULL REFERENCES typeStar(starTypeId) '
                     'ON UPDATE CASCADE ON DELETE CASCADE'
                     ');')
            cur.execute(query)

            # star index
            query = ('CREATE UNIQUE INDEX starId ON mapStars '
                     '(solarSystemId, starId);')
            cur.execute(query)

            # Moons - SQLite
            query = ('CREATE TABLE mapMoons (moonId INT NOT NULL '
                     ',solarSystemId INTEGER REFERENCES mapSolarSystems'
                     '(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL, '
                     'moonIndex INTEGER NOT NULL, planetId INTEGER REFERENCES '
                     'mapPlanets(planetId) ON UPDATE CASCADE ON DELETE SET NULL,'
                     'positionX FLOAT NOT NULL, positionY FLOAT NOT NULL,'
                     'positionZ FLOAT NOT NULL, radius INTEGER, '
                     'typeId INT REFERENCES invTypes(typeId) ON UPDATE CASCADE '
                     'ON DELETE SET NULL ,CONSTRAINT pkey PRIMARY KEY '
                     '(solarSystemId, moonId) ON CONFLICT FAIL '
                     ');')
            cur.execute(query)

            # Stations - SQLite
            query = ('CREATE TABLE staStation (idStation INT NOT NULL PRIMARY KEY, '
                     'stationName TEXT NOT NULL,solarSystemId INT REFERENCES '
                     'mapSolarSystems(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',stationType INT NOT NULL'
                     ');')
            cur.execute(query)

            # Corporation/Station - SQLite
            # ',stationId INT REFERENCES stations(stationId) ON UPDATE CASCADE ON DELETE SET NULL'
            query = ('CREATE TABLE staCorporations ('
                     'solarSystemId INT REFERENCES mapSolarSystems'
                     '(solarSystemId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',corporationId INT REFERENCES npcCorporations'
                     '(corporationId) ON UPDATE CASCADE ON DELETE SET NULL'
                     ',CONSTRAINT pkey PRIMARY KEY (solarSystemId,'
                     'corporationId) ON CONFLICT FAIL '
                     ');')
            cur.execute(query)

            # star index
            query = 'CREATE UNIQUE INDEX moonId ON mapMoons(moonId);'
            cur.execute(query)

            cur.connection.commit()
            cur.close()
            print("SDE: Tables created from scratch...")

    def parse_data(self):
        """
        This method provides centralized point to parse all data
        and put it into tables
        """
        self._parse_names()
        self._parse_categories(Path(self._yaml_directory).joinpath('fsd', 'categoryIDs.yaml'))
        self._parse_groups(Path(self._yaml_directory).joinpath('fsd', 'groupIDs.yaml'))
        self._parse_types(Path(self._yaml_directory).joinpath('fsd', 'typeIDs.yaml'))
        universe_dir = Path(self._yaml_directory).joinpath('fsd', 'universe')
        if self._config.map_kspace:
            print('SDE: parsing High,Low and Nullsec Systems')
            self._read_directory(universe_dir.joinpath('eve'))
        if self._config.map_wspace:
            print('SDE: parsing Wormhole Systems')
            self._read_directory(universe_dir.joinpath('wormhole'))
        if self._config.map_abbysal:
            print('SDE: parsing Abyssal Systems')
            self._read_directory(universe_dir.joinpath('abyssal'))
        if self._config.map_void:
            print('SDE: parsing Void Systems')
            self._read_directory(universe_dir.joinpath('void'))

    def add_star_type(self,type_id, name, color):
        """
        Method that insert star data into custom table
        """
        cur = self._db_driver.connection.cursor()
        query = 'INSERT INTO typeStar (typeId, name, color) VALUES (?,?,?)'
        params = [type_id,name,color]
        cur.execute(query,params)
        query = 'SELECT starTypeId FROM typeStar WHERE typeId=?'
        params=[type_id]
        results=cur.execute(query,params)
        row = results.fetchone()
        return row[0]

    def _parse_types(self, path_object):
        cur = self._db_driver.connection.cursor()
        process = {}
        query = ('INSERT INTO invTypes(typeId, groupId, typeName, iconId, published, volume) VALUES (:id ,:groupId, :name, :iconId, :published, :volume)')
        with path_object.open(encoding='UTF-8') as file:
            yaml_types = yaml.safe_load(file)
            total = len(yaml_types)
            cont = 0
            for object_type in yaml_types.items():
                if process.get(object_type[1]["groupID"]) is not None:
                    pass
                else:
                    params = {}
                    params['id'] = object_type[0]
                    params['name'] = object_type[1]['name']['en']
                    params['groupId'] = object_type[1]["groupID"]
                    params['iconId'] = None
                    if 'iconID' in object_type[1]:
                        params['iconId'] = object_type[1]["iconID"]
                    params['published'] = object_type[1]["published"]
                    params['volume'] = None
                    if 'volume' in object_type[1]:
                        params['volume'] = object_type[1]["volume"]
                    cur.execute(query, params)
                    if params['groupId'] == self._stars.id:
                        parse_name = params['name'].split(' ')
                        star_id = self.add_star_type(object_type[0],parse_name[1],parse_name[2][1:-1])
                        self._stars.entity_type[object_type[0]]=star_id
                    cont += 1
                print(f'SDE: parsing {total} Types [{round((cont / total)*100,2)}%]  \r', end="")
            print(f'SDE: {total} Types parsed           ')
        cur.close()

    def _parse_groups(self, path_object):
        cur = self._db_driver.connection.cursor()
        with path_object.open(encoding='UTF-8') as file:
            yGroups = yaml.safe_load(file)
            total = len(yGroups)
            cont = 0
            for group in yGroups.items():
                params = {}
                query = ('INSERT INTO invGroups(groupId, categoryId, groupName, anchorable) '
                         'VALUES (:id ,:catId, :name, :anchor)')
                params['id'] = group[0]
                params['catId'] = group[1]["categoryID"]
                params['name'] = group[1]["name"]["en"]
                params['anchor'] = group[1]["anchorable"]
                cont += 1
                cur.execute(query, params)

                # Detecting Sun Type to parse data on stars
                if params['name'] == 'Sun':
                    self._stars.id=params['id']

                print(f'SDE: parsing {total} groups [{round((cont / total)*100,2)}%]  \r', end="")
            print(f'SDE: {total} Groups parsed            ')
        cur.close()

    def _parse_categories(self, path_object):
        cur = self._db_driver.connection.cursor()
        with path_object.open(encoding='UTF-8') as file:
            yCategories = yaml.safe_load(file)
            total = len(yCategories)
            cont = 0
            for category in yCategories.items():
                params = {}
                query = ('INSERT INTO invCategories(categoryId, categoryName,'
                         ' published) VALUES (:id ,:name, :publish)')
                params['id'] = category[0]
                params['name'] = category[1]["name"]["en"]
                params['publish'] = category[1]["published"]
                cont += 1
                print(f'SDE: parsing {total} categories [{round((cont / total)*100,2)}%]  \r', end="")
                cur.execute(query, params)
            print(f'SDE: {total} Categories parsed          ')
        cur.close()

    def _parse_solar_system(self, path_object):
        cur = self._db_driver.connection.cursor()
        params = {}

        # query creation
        query = ('INSERT INTO mapSolarSystems (solarSystemId ,solarSystemName ,constellationId '
                 ',corridor ,fringe ,hub ,international ,luminosity ,radius ,centerX '
                 ',centerY ,centerZ ,regional ,security ,securityClass ')
        if self._config.extended_coordinates:
            query += ',maxX ,maxY ,maxZ ,minX ,minY ,minZ '
        query += (') VALUES ( :id, :name, :constellationId, :corridor, :fringe, :hub, :international, '
                  ':luminosity, :radius, :centerX, :centerY, :centerZ, :regional, :security, :securityClass')
        if self._config.extended_coordinates:
            query += ',:maxX ,:maxY ,:maxZ ,:minX ,:minY ,:minZ '
        query += ');'

        with path_object.open(encoding='UTF-8') as file:
            element = yaml.safe_load(file)

            # set the solar system Id
            self._Location[self._counter]['id'] = element['solarSystemID']
            self._Location[self._counter]['name'] = self._get_name(element['solarSystemID'])
            # print('SDE: parsing data for system ' + self._Location[self._counter]["name"])
            print(f'SDE: Parsing {self._Location[0]["name"]} > {self._Location[1]["name"]} > {self._Location[2]["name"]}')

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
            if self._config.extended_coordinates:
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

            self._parse_gates(element['stargates'])
            self._parse_planets(element['planets'])
            self._parse_star(element['star'])
        cur.close()

    def _parse_constellation(self, path_object):
        cur = self._db_driver.connection.cursor()
        # query creation
        query = ('INSERT INTO mapConstellations (constellationId ,constellationName ,regionId ,radius '
                 ',centerX ,centerY ,centerZ ')
        if self._config.extended_coordinates:
            query += ',maxX ,maxY ,maxZ ,minX ,minY ,minZ'
        query += ') VALUES (:id ,:name ,:regionId ,:radius ,:centerX ,:centerY ,:centerZ '
        if self._config.extended_coordinates:
            query += ',:maxX ,:maxY ,:maxZ ,:minX ,:minY ,:minZ'
        query += ')'
        with path_object.open(encoding='UTF-8') as file:
            element = yaml.safe_load(file)

            self._Location[self._counter]["id"] = element['constellationID']
            self._Location[self._counter]["name"] = self._get_name(element['constellationID'])

            # print('SDE: parsing data for constellation ' + self._Location[self._counter]["name"])
            print(f'SDE: Parsing {self._Location[0]["name"]} > {self._Location[1]["name"]} >')
            params = {}
            params['id'] = element['constellationID']
            params['name'] = self._Location[self._counter]["name"]
            params['regionId'] = self._Location[0]["id"]
            params['radius'] = element["radius"]
            params['centerX'] = element["center"][0]
            params['centerY'] = element["center"][1]
            params['centerZ'] = element["center"][2]
            if self._config.extended_coordinates:
                params['maxX'] = element["max"][0]
                params['maxY'] = element["max"][1]
                params['maxZ'] = element["max"][2]
                params['minX'] = element["min"][0]
                params['minY'] = element["min"][1]
                params['minZ'] = element["min"][2]
            cur.execute(query, params)
        cur.close()

    def _parse_region(self, path_object):
        cur = self._db_driver.connection.cursor()
        # query creation
        query = ('INSERT INTO mapRegions(regionId, regionName, factionId, centerX, centerY, centerZ'
                 ',nebula ,wormholeClassId ')
        if self._config.extended_coordinates:
            query += ',maxX ,maxY ,maxZ ,minX ,minY ,minZ'
        query += ') VALUES (:id , :name, :factionId, :centerX, :centerY, :centerZ, :nebula, :whclass'
        if self._config.extended_coordinates:
            query += ',:maxX ,:maxY ,:maxZ ,:minX ,:minY ,:minZ'
        query += ')'

        with path_object.open(encoding='UTF-8') as file:
            region = yaml.safe_load(file)
            self._Location[self._counter]["id"] = region['regionID']
            self._Location[self._counter]["name"] = self._get_name(region['regionID'])

            print(f'SDE: Parsing {self._Location[0]["name"]} > > ')
            # print('SDE: parsing data for region ' + self._Location[self._counter]["name"])
            params = {}
            params['id'] = region['regionID']
            params['name'] = self._Location[self._counter]["name"]
            params['factionId'] = None
            if 'factionID' in region:
                params['factionId'] = region['factionID']
            params['nebula'] = region["nebula"]
            params['whclass'] = None
            if 'wormholeClassID' in region:
                params['whclass'] = region["wormholeClassID"]
            params['centerX'] = region["center"][0]
            params['centerY'] = region["center"][1]
            params['centerZ'] = region["center"][2]
            if self._config.extended_coordinates:
                params['maxX'] = region["max"][0]
                params['maxY'] = region["max"][1]
                params['maxZ'] = region["max"][2]
                params['minX'] = region["min"][0]
                params['minY'] = region["min"][1]
                params['minZ'] = region["min"][2]
            cur.execute(query, params)
        cur.close()

    def _parse_gates(self, node):
        cur = self._db_driver.connection.cursor()
        query = ('INSERT INTO mapSystemGates (systemGateId, solarSystemId, typeId, '
                 'positionX, positionY, positionZ, destination) '
                 'VALUES (:id, :solarSystemId, :typeId, :posX, '
                 ':posY, :posZ, :destination );')
        for element in node.items():
            params = {}
            params['id'] = element[0]
            params['solarSystemId'] = self._Location[2]["id"]
            params['typeId'] = element[1]['typeID']
            params['posX'] = element[1]['position'][0]
            params['posY'] = element[1]['position'][1]
            params['posZ'] = element[1]['position'][2]
            params['destination'] = element[1]['destination']
            cur.execute(query, params)
        cur.close()

    def _parse_moons(self, planet_id, node):
        cur = self._db_driver.connection.cursor()
        cont = 1
        query = ('INSERT INTO mapMoons (moonId, solarSystemId, moonIndex, planetId, typeid, radius, positionX, '
                 'positionY, positionZ) VALUES (:id, :solarSystemId, :moonIndex, :planetId ,:typeId, :radius, '
                 ':posX, :posY, :posZ );')
        for element in node.items():
            params = {}
            params['id'] = element[0]
            params['solarSystemId'] = self._Location[2]['id']
            params['moonIndex'] = cont
            params['planetId'] = planet_id
            params['typeId'] = element[1]["typeID"]
            params['radius'] = None
            if 'statistics' in element[1]:
                params['radius'] = element[1]['statistics']['radius']
            params['posX'] = element[1]['position'][0]
            params['posY'] = element[1]['position'][1]
            params['posZ'] = element[1]['position'][2]
            cur.execute(query, params)
            cont += 1
        cur.close()

    def _parse_planets(self, node):
        cur = self._db_driver.connection.cursor()
        query = ('INSERT INTO mapPlanets (planetId, solarSystemId, planetaryIndex,'
                 'fragmented, radius, locked, typeId, '
                 'positionX, positionY, positionZ) VALUES (:id, :solarSystemId, '
                 ':planetIndex, :fragmented, :radius, '
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
            cur.execute(query, params)
            if 'moons' in element[1]:
                self._parse_moons(element[0], element[1]['moons'])
        cur.close()

    def _parse_star(self, node):
        params = {}
        cur = self._db_driver.connection.cursor()
        query = ('INSERT INTO mapStars ( starId, solarSystemId, locked, '
                 'radius, startypeId ) VALUES '
                 '(:starId, :solarSystemId, :locked, :radius, :typeId)')
        params['starId'] = node['id']
        params['solarSystemId'] = self._Location[2]['id']
        params['locked'] = node['statistics']['locked']
        params['radius'] = node['statistics']['radius']
        params['typeId'] = self._stars.entity_type[node['typeID']]
        cur.execute(query, params)
        cur.close()

    def _parse_names(self):
        """
        Load the all the names used by entities and dump it into a temp table
        """
        cur = self._db_driver.connection.cursor()
        names_file = Path(self.yaml_directory).joinpath('bsd', 'invNames.yaml')
        if not names_file.exists():
            raise FileNotFoundError
        query = 'INSERT INTO invNames (itemId, itemName) VALUES (:id, :name);'
        with names_file.open(encoding='UTF-8') as file:
            names = yaml.safe_load(file)

        total = len(names)
        cont = 0
        for name in names:
            params = {}
            params['id'] = name['itemID']
            params['name'] = name['itemName']
            cur.execute(query, params)
            cont += 1
            print(f'SDE: Parsing {total} names [{round((cont / total)*100,2)}%]  \r', end="")
        cur.close()
        print(f'SDE: {total} names parsed                  ')

    def _get_name(self, name_id):
        result = ''
        cur = self._db_driver.connection.cursor()
        query = 'SELECT itemName FROM invNames WHERE itemId = ?;'
        rows = cur.execute(query, (name_id,))
        for row in rows:
            result = row[0]
        cur.close()
        return result

    def close(self):
        """Drop unnecesary data, commit transactions and close the database"""
        query = 'DROP TABLE invNames;'
        cur = self._db_driver.connection.cursor()
        cur.execute(query)
        self._db_driver.connection.commit()
        if self._db_type == DatabaseType.SQLITE:
            query = 'VACUUM;'
            cur.execute(query)
        cur.close()

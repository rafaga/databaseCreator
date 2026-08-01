#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
This script provides a Class to parse SDE structure into a SQLite Database.

IMPORTANT - SDE REWORK (Sept 2025)
-----------------------------------
On 22 Sept 2025 CCP replaced the old SDE with a new, NOT backwards
compatible format ("Reworking the SDE: a fresh start for static data" -
https://developers.eveonline.com/blog/reworking-the-sde-a-fresh-start-for-static-data).
This module targets the NEW format. The main differences from the old
per-directory YAML export this file used to parse:

  * No more directory tree. `region.yaml` / `constellation.yaml` /
    `solarsystem.yaml` nested under `universe/eve/<region>/<const>/<system>/`
    are gone. Every entity type is now a single flat top-level file:
    mapRegions, mapConstellations, mapSolarSystems, mapStargates,
    mapPlanets, mapMoons, mapStars ... Each line/entry is one record keyed
    by `_key` (the id).
  * The `bsd/` folder (and `invNames.yaml` with it) is gone. Region,
    constellation and solar system names now live directly on each
    record as a localized `name` object (e.g. `name['en']`). There is no
    separate ID -> name lookup table to build anymore.
  * K-space, W-space, Abyssal and "Void" systems are no longer split into
    separate directories (`eve/`, `wormhole/`, `abyssal/`, `void/`). They
    all live in the same mapSolarSystems file now.
  * `centerX/Y/Z` + the `min`/`max` bounding box are replaced by a single
    `position: {x, y, z}` object. There is no bounding box anymore, so the
    old `extended_coordinates` config flag and the maxX/maxY/maxZ/minX/
    minY/minZ columns it controlled are gone. Solar systems additionally
    get an optional `position2D` (the in-game 2D map coordinates).
  * Regions and constellations no longer carry a `radius` field (only
    solar systems still do).
  * Stargates now carry a `destination` object with BOTH the destination
    `solarSystemID` and `stargateID`, instead of a bare gate id.
  * CCP also added a JSON Lines (.jsonl) format alongside YAML,
    specifically recommended for large files like mapMoons.

Field names below come from the official docs
(https://developers.eveonline.com/docs/services/static-data/) and from
https://sde.riftforeve.online (a community schema reference regenerated
against every SDE release). mapRegions / mapConstellations / mapSolarSystems
/ mapStargates / mapMoons were verified field-by-field. mapPlanets and
mapStars follow the same shape confirmed for mapMoons (celestialIndex,
top-level radius, optional `statistics`, solarSystemID back-reference) but
weren't independently verified line-by-line against a live SDE build --
diff `_parse_planets`/`_parse_stars` against one real record before relying
on this in production, and adjust the `.get(...)` fallbacks if needed.

NOTE ON YOUR DATABASE SCHEMA (schema_corregido_strict.sql)
------------------------------------------------------------
This parser keeps your existing column names where the underlying concept
didn't change (e.g. centerX/Y/Z still hold what is now `position.x/y/z`;
`nebula` still holds what is now `nebulaID`) to minimize the amount of SQL
you need to touch. You will still need to update the schema itself for:
  * DROP the maxX/maxY/maxZ/minX/minY/minZ columns on mapRegions,
    mapConstellations and mapSolarSystems (no bounding box anymore).
  * DROP (or make nullable) the `radius` column on mapRegions and
    mapConstellations -- the new SDE doesn't provide it at those levels.
  * mapSystemGates needs a `destinationGateId` column (replacing the old
    bare `destination` scalar) plus, optionally, `destinationSystemId`.
  * The old `invNames` staging table is no longer needed at all -- names
    arrive pre-embedded on each record.
Happy to draft the updated .sql with you once you share the current file.
"""
from pathlib import Path
import json
import yaml
from database_driver import DatabaseDriver, DatabaseType
from data_object import GenericEntity


class SdeConfig:
    """
    Provides default configuration for importing data from SDE
    """
    file_format = 'jsonl'  # 'jsonl' or 'yaml' -- must match the SDE zip you downloaded
    language = 'en'        # which localized string to pull out of name/description objects
    map_kspace = True
    map_wspace = True
    map_abyssal = True
    map_void = False
    projection_algorithm = 'isometric'  # possible values are 'isometric' and 'dimetric'
    projected_axis = 1  # 0 for X axis, 1 for Y and 2 for Z
    with_moons = True
    with_gates = True


class DataBrigde():
    """
    Class for storing star type
    """
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
        if isinstance(value, int):
            self.__star_group_id = value

    @property
    def star(self, type_id):
        """ Property to to store start type """
        return self.__star_type_id[type_id]

    @star.setter
    def star(self, type_id, value):
        self.__star_type_id[type_id] = value


class DirectoryNotFoundError(Exception):
    """
    Generic class for Directory Not found error
    """


class SdeParser:
    """
    Class that parse the data from SDE information
    """
    # Propiedades
    _sde_directory = None
    _db_driver = None
    _db_type = None
    _config = SdeConfig()
    _stars = GenericEntity()

    # Name caches, populated while parsing mapRegions/mapConstellations/
    # mapSolarSystems, used only for progress-printing (the new SDE embeds
    # names directly on every record, so there's no more per-id lookup
    # table/query the way `_get_name()` used to work against invNames).
    _region_names = {}
    _constellation_names = {}
    _system_names = {}

    # solarSystemID -> True for every system that passed the map_kspace /
    # map_wspace / map_abyssal / map_void filter. Populated by
    # `_parse_solar_systems()`, consumed by every child parser (stargates,
    # planets, moons, stars) so we only import celestials that belong to a
    # system we actually kept.
    _systems_in_scope = None

    @property
    def configuration(self):
        """Object that stores the parsing configuration"""
        return self._config

    @property
    def sde_directory(self):
        """the directory holding the (flat) SDE files"""
        return self._sde_directory

    @sde_directory.setter
    def sde_directory(self, directory):
        self._sde_directory = directory

    # Constructor
    def __init__(self, directory, database_file, db_type=DatabaseType.SQLITE):
        if Path(directory).is_dir():
            self.sde_directory = directory
        else:
            raise DirectoryNotFoundError('The specified directory does not exists.')
        if db_type == DatabaseType.SQLITE:
            print("SDE: Using SQLite as Database Engine...")
        self._db_driver = DatabaseDriver(db_type, database_file)
        self._db_type = db_type
        self._config = SdeConfig()
        self._systems_in_scope = set()

    def calculate_isometric_projection(self, x_coord, y_coord, z_coord, projected_axis):
        """
        calculate isometric projection coordinates over 3D points
        based upon https://www.compuphase.com/axometr.htm formulas
        Alternative Formula but not verified
        https://gamedev.stackexchange.com/questions/159434/how-to-convert-3d-coordinates-to-2d-isometric-coordinates
        """
        n = [0.0, 0.0, 0.0]
        if projected_axis == 2:
            n[0] = x_coord - z_coord
            n[1] = y_coord + ((x_coord + z_coord) / 2)
        if projected_axis == 1:
            n[0] = x_coord - y_coord
            n[2] = z_coord + ((x_coord + y_coord) / 2)
        if projected_axis == 0:
            n[1] = y_coord - x_coord
            n[2] = z_coord + ((y_coord + x_coord) / 2)
        return (n)

    def calculate_dimetric_projection(self, x_coord, y_coord, z_coord, projected_axis):
        """
        calculate military oblique projection coordinates over 3D points
        based upon https://www.compuphase.com/axometr.htm formulas
        """
        n = [0.0, 0.0, 0.0]
        if projected_axis == 2:
            n[0] = x_coord + (z_coord / 4)
            n[1] = y_coord + (z_coord / 2)
        if projected_axis == 1:
            n[0] = x_coord + (y_coord / 4)
            n[2] = z_coord + (y_coord / 2)
        if projected_axis == 0:
            n[1] = y_coord + (x_coord / 4)
            n[2] = z_coord + (x_coord / 2)
        return (n)

    # ------------------------------------------------------------------
    # Generic flat-file reader: the new SDE has no more directory tree,
    # so every `_parse_*` method below just streams one top-level file.
    # ------------------------------------------------------------------
    def _iter_records(self, stem):
        """
        Yield one dict per record from <sde_directory>/<stem>.jsonl (or
        .yaml, depending on configuration.file_format). Every record is
        guaranteed to have an `_key` entry (the id), matching the new
        SDE convention -- for YAML files stored as a top-level mapping of
        id -> object (rather than a JSONL-style list of docs) the id is
        injected as `_key` automatically.
        """
        base = Path(self.sde_directory) / stem
        if self._config.file_format == 'jsonl':
            path = base.with_suffix('.jsonl')
            with path.open(encoding='UTF-8') as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue
                    yield json.loads(line)
        else:
            path = base.with_suffix('.yaml')
            with path.open(encoding='UTF-8') as file:
                data = yaml.safe_load(file)
            if isinstance(data, dict):
                for key, value in data.items():
                    record = dict(value) if isinstance(value, dict) else {'value': value}
                    record.setdefault('_key', key)
                    yield record
            elif isinstance(data, list):
                yield from data

    def _localized(self, record, field='name'):
        """Pull the configured language out of a localized name/description
        object, e.g. {'en': 'Jita', 'es': 'Jita', ...} -> 'Jita'."""
        value = record.get(field)
        if isinstance(value, dict):
            return value.get(self._config.language) or value.get('en')
        return value

    def _system_in_scope(self, wormhole_class_id):
        """
        Decide whether a solar system should be imported, based on the
        map_kspace / map_wspace / map_abyssal / map_void flags.

        The old SDE told k-space/w-space/abyssal/void apart by directory
        (`eve/`, `wormhole/`, `abyssal/`, `void/`). The new flat
        mapSolarSystems file doesn't have that split anymore; the only
        confirmed discriminator on the record itself is `wormholeClassID`
        (present only for non-k-space systems). CCP doesn't expose a
        finer-grained "this is Abyssal vs this is Void" flag at this
        level, so map_wspace/map_abyssal/map_void currently all gate on
        the same "has a wormholeClassID" check below.

        TODO(Rafael): si necesitas distinguir wormhole space, abyssal
        deadspace y "void" entre sí (hoy los tres caen en la misma rama),
        tu propio external_parser.get_all_regions() ya usa el corte
        `regionId < 11000000` para separar regiones de New Eden ("k-space
        real", donde Dotlan tiene mapas) del resto -- probablemente puedas
        reusar/afinar ese mismo criterio por regionId aquí en vez de
        wormholeClassID, pero confírmalo contra un SDE real antes de
        confiar en un corte numérico fijo.
        """
        if wormhole_class_id is None:
            return self._config.map_kspace
        return self._config.map_wspace or self._config.map_abyssal or self._config.map_void

    def create_table_structure(self):
        """
        This method create the database Structure to populate the data from SDE and external sources
        """
        if self._db_type == DatabaseType.SQLITE:
            cur = self._db_driver.connection.cursor()
            q = Path("schema_corregido_strict.sql")
            query = ""
            with q.open() as f:
                query = f.read()
            cur.executescript(query)

            cur.connection.commit()
            cur.close()

    def parse_data(self):
        """
        This method provides centralized point to parse all data
        and put it into tables
        """
        if self._db_driver is None:
            print("SDE: Error on database object Creation")
            return
        self._parse_categories(self._config.file_format and 'categories' or 'categories')
        self._parse_groups('groups')
        self._parse_types('types')
        self._parse_races()
        self._parse_npc_corporations()
        self._parse_factions()
        self._parse_regions()
        self._parse_constellations()
        self._parse_solar_systems()
        if self.configuration.with_gates:
            self._parse_stargates()
        self._parse_stars()
        self._parse_planets()
        if self.configuration.with_moons:
            self._parse_moons()
        self.parse_connections()

    def add_star_type(self, type_id, name, color):
        """
        Method that insert star data into custom table
        """
        cur = self._db_driver.connection.cursor()
        query = 'INSERT INTO typeStar (typeId, name, color) VALUES (?,?,?)'
        params = [type_id, name, color]
        cur.execute(query, params)
        query = 'SELECT starTypeId FROM typeStar WHERE typeId=?'
        params = [type_id]
        results = cur.execute(query, params)
        row = results.fetchone()
        return row[0]

    def _parse_types(self, stem):
        cur = self._db_driver.connection.cursor()
        process = {}
        query = ('INSERT INTO invTypes(typeId, groupId, typeName, iconId,'
                 ' published, volume) VALUES (:id ,:groupId, :name, '
                 ':iconId, :published, :volume)')
        records = list(self._iter_records(stem))
        total = len(records)
        cont = 0
        for object_type in records:
            if process.get(object_type["groupID"]) is not None:
                pass
            else:
                params = {}
                params['id'] = object_type['_key']
                params['name'] = self._localized(object_type)
                params['groupId'] = object_type["groupID"]
                params['iconId'] = object_type.get("iconID")
                params['published'] = object_type.get("published")
                params['volume'] = object_type.get("volume")
                cur.execute(query, params)
                if params['groupId'] == self._stars.id:
                    parse_name = params['name'].split(' ')
                    star_id = self.add_star_type(params['id'],
                                                  parse_name[1],
                                                  parse_name[2][1:-1])
                    self._stars.entity_type[params['id']] = star_id
                cont += 1
            print(f'SDE: parsing {total} Types [{round((cont / total) * 100, 2)}%]  \r', end="")
        print(f'SDE: {total} Types parsed           ')
        cur.close()

    def _parse_groups(self, stem):
        cur = self._db_driver.connection.cursor()
        records = list(self._iter_records(stem))
        total = len(records)
        cont = 0
        query = ('INSERT INTO invGroups(groupId, categoryId, groupName, anchorable) '
                  'VALUES (:id ,:catId, :name, :anchor)')
        for group in records:
            params = {}
            params['id'] = group['_key']
            params['catId'] = group["categoryID"]
            params['name'] = self._localized(group)
            params['anchor'] = group.get("anchorable")
            cont += 1
            cur.execute(query, params)

            # Detecting Sun Type to parse data on stars
            if params['name'] == 'Sun':
                self._stars.id = params['id']

            print(f'SDE: parsing {total} groups [{round((cont / total) * 100, 2)}%]  \r', end="")
        print(f'SDE: {total} Groups parsed            ')
        cur.close()

    def _parse_categories(self, stem):
        cur = self._db_driver.connection.cursor()
        records = list(self._iter_records(stem))
        total = len(records)
        for cont, category in enumerate(records, 1):
            params = {}
            query = ('INSERT INTO invCategories(categoryId, categoryName,'
                      ' published) VALUES (:id ,:name, :publish)')
            params['id'] = category['_key']
            params['name'] = self._localized(category)
            params['publish'] = category.get("published")
            print(f'SDE: parsing {total} categories [{round((cont / total) * 100, 2)}%]  \r',
                  end="")
            cur.execute(query, params)
        print(f'SDE: {total} Categories parsed          ')
        cur.close()

    # ------------------------------------------------------------------
    # Races / NPC corporations / factions. mapRegions.factionId has a FK
    # against factions, so these must be populated before the map data.
    # ------------------------------------------------------------------
    def _parse_races(self):
        cur = self._db_driver.connection.cursor()
        query = 'INSERT INTO races (raceId, raceName) VALUES (:id, :name)'
        records = list(self._iter_records('races'))
        for race in records:
            params = {
                'id': race['_key'],
                'name': self._localized(race),
            }
            cur.execute(query, params)
        print(f'SDE: {len(records)} Races parsed          ')
        cur.close()

    def _parse_npc_corporations(self):
        cur = self._db_driver.connection.cursor()
        query = ('INSERT INTO npcCorporations (corporationId, corporationName,'
                  ' tickerName, deleted, iconId, raceId) VALUES (:id, :name,'
                  ' :ticker, :deleted, :iconId, :raceId)')
        records = list(self._iter_records('npcCorporations'))
        for corporation in records:
            params = {
                'id': corporation['_key'],
                'name': self._localized(corporation),
                'ticker': corporation['tickerName'],
                'deleted': corporation['deleted'],
                'iconId': corporation.get('iconID'),
                'raceId': corporation.get('raceID'),
            }
            cur.execute(query, params)
        print(f'SDE: {len(records)} NPC Corporations parsed          ')
        cur.close()

    def _parse_factions(self):
        cur = self._db_driver.connection.cursor()
        query = ('INSERT INTO factions (factionId, factionName, iconId,'
                  ' sizeFactor, uniqueName, corporationId) VALUES (:id, :name,'
                  ' :iconId, :sizeFactor, :uniqueName, :corporationId)')
        race_query = ('INSERT INTO factionRace (factionId, raceId)'
                      ' VALUES (:factionId, :raceId)')
        records = list(self._iter_records('factions'))
        for faction in records:
            params = {
                'id': faction['_key'],
                'name': self._localized(faction),
                'iconId': faction['iconID'],
                'sizeFactor': faction['sizeFactor'],
                'uniqueName': faction['uniqueName'],
                'corporationId': faction.get('corporationID'),
            }
            cur.execute(query, params)
            for race_id in faction.get('memberRaces', []):
                cur.execute(race_query, {'factionId': faction['_key'],
                                         'raceId': race_id})
        print(f'SDE: {len(records)} Factions parsed          ')
        cur.close()

    # ------------------------------------------------------------------
    # Map data -- regions / constellations / solar systems / stargates /
    # stars / planets / moons. All flat top-level files in the new SDE.
    # ------------------------------------------------------------------
    def _parse_regions(self):
        cur = self._db_driver.connection.cursor()
        query = ('INSERT INTO mapRegions(regionId, regionName, factionId, centerX, centerY, centerZ'
                  ', nebula, wormholeClassId) VALUES (:id , :name, :factionId, :centerX, :centerY,'
                  ' :centerZ, :nebula, :whclass)')
        records = list(self._iter_records('mapRegions'))
        total = len(records)
        for cont, region in enumerate(records, 1):
            name = self._localized(region)
            self._region_names[region['_key']] = name
            print(f'SDE: Parsing {name} > > [{round((cont / total) * 100, 2)}%]  \r', end="")
            params = {
                'id': region['_key'],
                'name': name,
                'factionId': region.get('factionID'),
                'nebula': region.get('nebulaID'),
                'whclass': region.get('wormholeClassID'),
                'centerX': region['position']['x'],
                'centerY': region['position']['y'],
                'centerZ': region['position']['z'],
            }
            cur.execute(query, params)
        print(f'SDE: {total} Regions parsed                  ')
        cur.close()

    def _parse_constellations(self):
        cur = self._db_driver.connection.cursor()
        query = ('INSERT INTO mapConstellations (constellationId ,constellationName ,regionId '
                  ',centerX ,centerY ,centerZ) VALUES (:id ,:name ,:regionId ,:centerX ,:centerY ,:centerZ)')
        records = list(self._iter_records('mapConstellations'))
        total = len(records)
        for cont, element in enumerate(records, 1):
            name = self._localized(element)
            self._constellation_names[element['_key']] = name
            region_name = self._region_names.get(element['regionID'], '?')
            print(f'SDE: Parsing {region_name} > {name} > [{round((cont / total) * 100, 2)}%]  \r', end="")
            params = {
                'id': element['constellationID'] if 'constellationID' in element else element['_key'],
                'name': name,
                'regionId': element['regionID'],
                'centerX': element['position']['x'],
                'centerY': element['position']['y'],
                'centerZ': element['position']['z'],
            }
            cur.execute(query, params)
        print(f'SDE: {total} Constellations parsed                  ')
        cur.close()

    def _parse_solar_systems(self):
        cur = self._db_driver.connection.cursor()
        query = ('INSERT INTO mapSolarSystems (solarSystemId ,solarSystemName ,constellationId '
                  ',corridor ,fringe ,hub ,international ,luminosity ,radius ,centerX '
                  ',centerY ,centerZ ,regional ,security ,securityClass ,projX ,projY ,projZ '
                  ',position2DX ,position2DY) '
                  'VALUES ( :id, :name, :constellationId, :corridor, :fringe, :hub, '
                  ':international, :luminosity, :radius, :centerX, :centerY, :centerZ, '
                  ':regional, :security, :securityClass, :projX, :projY, :projZ, '
                  ':position2DX, :position2DY);')
        records = list(self._iter_records('mapSolarSystems'))
        total = len(records)
        for cont, element in enumerate(records, 1):
            system_id = element['_key']
            in_scope = self._system_in_scope(element.get('wormholeClassID'))
            print(f'SDE: parsing {total} solar systems [{round((cont / total) * 100, 2)}%]  \r', end="")
            if not in_scope:
                continue
            self._systems_in_scope.add(system_id)
            name = self._localized(element)
            self._system_names[system_id] = name

            params = {}
            params['id'] = system_id
            params['name'] = name
            params['constellationId'] = element['constellationID']
            params['corridor'] = element.get('corridor')
            params['fringe'] = element.get('fringe')
            params['hub'] = element.get('hub')
            params['international'] = element.get('international')
            params['luminosity'] = element.get('luminosity')
            params['radius'] = element['radius']
            position = element['position']
            params['centerX'] = position['x']
            params['centerY'] = position['y']
            params['centerZ'] = position['z']
            if self._config.projection_algorithm == 'isometric':
                projection = self.calculate_isometric_projection(x_coord=position['x'],
                                                                   y_coord=position['y'],
                                                                   z_coord=position['z'],
                                                                   projected_axis=self._config.projected_axis)
                params['projX'], params['projY'], params['projZ'] = projection
            elif self._config.projection_algorithm == 'dimetric':
                projection = self.calculate_dimetric_projection(x_coord=position['x'],
                                                                  y_coord=position['y'],
                                                                  z_coord=position['z'],
                                                                  projected_axis=self._config.projected_axis)
                params['projX'], params['projY'], params['projZ'] = projection
            else:
                params['projX'] = position['x']
                params['projY'] = position['y']
                params['projZ'] = position['z']
            params['regional'] = element.get('regional')
            params['security'] = element['securityStatus']
            params['securityClass'] = element.get('securityClass')
            position_2d = element.get('position2D')
            params['position2DX'] = position_2d.get('x') if position_2d else None
            params['position2DY'] = position_2d.get('y') if position_2d else None
            cur.execute(query, params)
        print(f'SDE: {total} solar systems parsed ({len(self._systems_in_scope)} kept)            ')
        cur.close()

    def _parse_stargates(self):
        cur = self._db_driver.connection.cursor()
        query = ('INSERT INTO mapSystemGates (systemGateId, solarSystemId, typeId, '
                  'positionX, positionY, positionZ, destinationGateId, destinationSystemId) '
                  'VALUES (:id, :solarSystemId, :typeId, :posX, :posY, :posZ, '
                  ':destinationGateId, :destinationSystemId);')
        cont = 0
        for gate in self._iter_records('mapStargates'):
            if gate['solarSystemID'] not in self._systems_in_scope:
                continue
            params = {
                'id': gate['_key'],
                'solarSystemId': gate['solarSystemID'],
                'typeId': gate['typeID'],
                'posX': gate['position']['x'],
                'posY': gate['position']['y'],
                'posZ': gate['position']['z'],
                'destinationGateId': gate['destination']['stargateID'],
                'destinationSystemId': gate['destination']['solarSystemID'],
            }
            cur.execute(query, params)
            cont += 1
        print(f'SDE: {cont} stargates parsed')
        cur.close()

    def parse_connections(self):
        cur = self._db_driver.connection.cursor()
        query = ('INSERT INTO mapSystemConnections (systemConnectionId, systemA, systemB) '
                  'SELECT LOWER(HEX(RANDOMBLOB(4))), msga.solarSystemId, msgb.solarSystemId '
                  'FROM mapSystemGates AS msga '
                  'INNER JOIN mapSystemGates AS msgb ON (msgb.systemGateId = msga.destinationGateId) '
                  'WHERE msga.solarSystemId > msgb.solarSystemId')
        cur.execute(query)
        cur.close()

    def _parse_stars(self):
        """
        NOTE: per CCP's own map-data guide, star objects don't carry an
        explicit position in the SDE -- a star is always the origin
        (0, 0, 0) of its own solar system's local coordinate system. See
        https://developers.eveonline.com/docs/guides/map-data/
        `radius`/`locked` shape below follows the confirmed mapMoons
        pattern (top-level `radius`, optional nested `statistics`) --
        verify against a real mapStars record before trusting in prod.
        """
        cur = self._db_driver.connection.cursor()
        query = ('INSERT INTO mapStars ( starId, solarSystemId, locked, '
                  'radius, startypeId ) VALUES '
                  '(:starId, :solarSystemId, :locked, :radius, :typeId)')
        cont = 0
        for star in self._iter_records('mapStars'):
            if star['solarSystemID'] not in self._systems_in_scope:
                continue
            statistics = star.get('statistics') or {}
            params = {
                'starId': star['_key'],
                'solarSystemId': star['solarSystemID'],
                'locked': star.get('locked', statistics.get('locked')),
                'radius': star.get('radius', statistics.get('radius')),
                'typeId': self._stars.entity_type.get(star['typeID'], star['typeID']),
            }
            cur.execute(query, params)
            cont += 1
        print(f'SDE: {cont} stars parsed')
        cur.close()

    def _parse_planets(self):
        """
        See the docstring on `_parse_stars` re: mapPlanets field names
        being inferred from the confirmed mapMoons shape rather than
        independently verified.
        """
        cur = self._db_driver.connection.cursor()
        query = ('INSERT INTO mapPlanets (planetId, solarSystemId, planetaryIndex,'
                  'fragmented, radius, locked, typeId, '
                  'positionX, positionY, positionZ) VALUES (:id, :solarSystemId, '
                  ':planetIndex, :fragmented, :radius, '
                  ':locked, :typeId, :posX, :posY, :posZ );')
        cont = 0
        for planet in self._iter_records('mapPlanets'):
            if planet['solarSystemID'] not in self._systems_in_scope:
                continue
            statistics = planet.get('statistics') or {}
            position = planet['position']
            params = {
                'id': planet['_key'],
                'solarSystemId': planet['solarSystemID'],
                'planetIndex': planet.get('celestialIndex'),
                'fragmented': planet.get('fragmented', statistics.get('fragmented')),
                'radius': planet.get('radius', statistics.get('radius')),
                'locked': planet.get('locked', statistics.get('locked')),
                'typeId': planet['typeID'],
                'posX': position['x'],
                'posY': position['y'],
                'posZ': position['z'],
            }
            cur.execute(query, params)
            cont += 1
        print(f'SDE: {cont} planets parsed')
        cur.close()

    def _parse_moons(self):
        """
        mapMoons.jsonl fields confirmed: _key, attributes, celestialIndex,
        npcStationIDs, orbitID (id of the parent planet), orbitIndex
        (the moon's index around that planet), position, radius,
        solarSystemID, statistics, typeID, uniqueName.
        """
        cur = self._db_driver.connection.cursor()
        query = ('INSERT INTO mapMoons (moonId, solarSystemId, moonIndex, planetId, typeid, radius,'
                  ' positionX, positionY, positionZ) VALUES (:id, :solarSystemId, :moonIndex, '
                  ':planetId ,:typeId, :radius, :posX, :posY, :posZ );')
        cont = 0
        for moon in self._iter_records('mapMoons'):
            if moon['solarSystemID'] not in self._systems_in_scope:
                continue
            position = moon['position']
            statistics = moon.get('statistics') or {}
            params = {
                'id': moon['_key'],
                'solarSystemId': moon['solarSystemID'],
                'moonIndex': moon.get('orbitIndex'),
                'planetId': moon.get('orbitID'),
                'typeId': moon['typeID'],
                'radius': moon.get('radius', statistics.get('radius')),
                'posX': position['x'],
                'posY': position['y'],
                'posZ': position['z'],
            }
            cur.execute(query, params)
            cont += 1
        print(f'SDE: {cont} moons parsed')
        cur.close()

    def close(self):
        """Commit transactions and close the database.

        The old invNames staging table doesn't exist anymore -- the new
        SDE embeds names directly on each record instead of a separate
        lookup table -- so there's nothing left to DROP here."""
        if self._db_type == DatabaseType.SQLITE:
            cur = self._db_driver.connection.cursor()
            self._db_driver.connection.commit();
            query = 'VACUUM;'
            cur.execute(query)
            cur.close()

#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# DataProcessor - CLase encargada del registro de datos y
# la consistencia de los mismos
# Autor: Rafael Amador Galván
# Fecha: 3/06/2017
"""Module that works as framework to data processing, creating basic database structure
 and filling the data if it is missing on filesystem"""
import sqlite3
from os.path import isfile, getsize

class DatabaseUtils:
    """Module that performs basic database check-ins"""
    conn = None

    # Propiedades
    @property
    def db_file(self):
        """the database file name"""
        return self.__db_file

    @db_file.setter
    def db_file(self, filename):
        self.__db_file = filename

    # Constructor
    def __init__(self, filename):
        if filename is not None:
            self.db_file = filename
        self.conn = sqlite3.connect(self.db_file)

    def isSqLite3(self):
        """Function that checks if given file has a valid SQLite format"""
        if not isfile(self.db_file):
            return False
        # SQLite database file header is 100 bytes
        if getsize(self.db_file) < 100:
            return False
        with open(self.db_file, 'rb') as file:
            header = file.read(100)
        return header[:16] == b'SQLite format 3\x00'

    def syncTables(self):
        """Remove all the unnecesary tables in the database"""
        cur = self.conn.cursor()
        print("SMT: Droping uneeded SDE tables")
        tables = ('agtAgents','agtAgentsInSpace','agtAgentTypes','agtResearchAgents','certCerts',
                  'certMasteries','certSkills','chrAncestries','chrAttributes','chrBloodlines','chrFactions',
                  'chrRaces','crpActivities','crpNPCDivisions','crpNPCCorporationDivisions',
                  'crpNPCCorporationResearchFields','crpNPCCorporations','crpNPCCorporationTrades',
                  'dgmAttributeCategories','dgmAttributeTypes','dgmEffects','dgmExpressions','dgmTypeAttributes',
                  'dgmTypeEffects','eveGraphics','eveIcons','eveUnits','industryActivity','industryActivityMaterials',
                  'industryActivityProbabilities','industryActivityProducts','industryActivityRaces',
                  'industryActivitySkills','industryBlueprints','invContrabandTypes','invControlTowerResourcePurposes',
                  'invControlTowerResources','invFlags','invMarketGroups','invMetaGroups','invMetaTypes',
                  'invTraits','invTypeMaterials','invTypeReactions','mapLandmarks','mapLocationScenes','mapDenormalize',
                  'mapCelestialGraphics','planetSchematics','planetSchematicsPinMap','planetSchematicsTypeMap',
                  'ramActivities','ramAssemblyLineStations','ramAssemblyLineTypeDetailPerCategory',
                  'ramAssemblyLineTypeDetailPerGroup','ramAssemblyLineTypes','ramInstallationTypeContents',
                  'skinLicense','skinMaterials','skins','skinShip','translationTables','trnTranslationColumns',
                  'trnTranslationLanguages','trnTranslations','warCombatZones','warCombatZoneSystems')
        try:
            for table in tables:
                cur.execute('DROP TABLE IF EXISTS ' + table)

            print("SDE: removing unnecesary Data..")
            cur.execute('DELETE FROM invItems WHERE flagID > 0')
            
            print("SDE: Removing unecessary fields fropm tables ...")
            # staStationTypes Table
            cur.execute('ALTER TABLE staStationTypes DROP COLUMN dockEntryX;')
            cur.execute('ALTER TABLE staStationTypes DROP COLUMN dockEntryY;')
            cur.execute('ALTER TABLE staStationTypes DROP COLUMN dockEntryZ;')
            cur.execute('ALTER TABLE staStationTypes DROP COLUMN dockOrientationX;')
            cur.execute('ALTER TABLE staStationTypes DROP COLUMN dockOrientationY;')
            cur.execute('ALTER TABLE staStationTypes DROP COLUMN dockOrientationZ;')

            #staStations Table
            cur.execute('ALTER TABLE staStations DROP COLUMN dockingCostPerVolume;')
            cur.execute('ALTER TABLE staStations DROP COLUMN officeRentalCost;')
            cur.execute('ALTER TABLE staStations DROP COLUMN reprocessingEfficiency;')
            cur.execute('ALTER TABLE staStations DROP COLUMN reprocessingStationsTake;')
            cur.execute('ALTER TABLE staStations DROP COLUMN reprocessingHangarFlag;')

            #staOperations Table
            cur.execute('ALTER TABLE staOperations DROP COLUMN caldariStationTypeID;')
            cur.execute('ALTER TABLE staOperations DROP COLUMN amarrStationTypeID;')
            cur.execute('ALTER TABLE staOperations DROP COLUMN minmatarStationTypeID;')
            cur.execute('ALTER TABLE staOperations DROP COLUMN gallenteStationTypeID;')
            cur.execute('ALTER TABLE staOperations DROP COLUMN joveStationTypeID;')

            #invTypes table
            cur.execute('ALTER TABLE invTypes DROP COLUMN iconID;')
            cur.execute('ALTER TABLE invTypes DROP COLUMN soundID;')
            cur.execute('ALTER TABLE invTypes DROP COLUMN graphicID;')
            self.conn.commit()
        except:
            self.conn.rollback()
        cur.close()
        del cur

    def addAddtionalData(self):
        # TODO: crear tabla para sistemas jove y para sistemas triglavian
        cur = self.conn.cursor()
        try:
            print("SMT: Adding Triglavian Status Catalog Table")
            cur.execute('CREATE TABLE mapTriglavianStatus (trigStatusID INT NOT NULL PRIMARY KEY,'
                        'trigStatusName TEXT NOT NULL);')

            print("SMT: Filling Triglavian Status Table")
            values = ([ 0, 'None'],
                      [ 1, 'Edencom Minor Victory'],
                      [ 2, 'Final Liminality'],
                      [ 3, 'Fortress'],
                      [ 4, 'Triglavian Minor Victory'],)
            query = ('INSERT INTO mapTriglavianStatus(trigStatusID,trigStatusName)'
                     ' VALUES(?,?);')
            cur.executemany(query, values)

            print("SMT: Adding IceBelt field to the mapSolarSystems")
            cur.execute('ALTER TABLE mapSolarSystems ADD COLUMN hasIceBelts BOOL NOT NULL DEFAULT 0;')
            
            print("SMT: Adding Jove Observatory field to the mapSolarSystems")
            cur.execute('ALTER TABLE mapSolarSystems ADD COLUMN hasJoveObservatory BOOL NOT NULL DEFAULT 0;')

            print("SMT: Adding  Triglavian Invasion Status Field to the mapSolarSystems")
            cur.execute('ALTER TABLE mapSolarSystems ADD COLUMN trigStatusID INT NOT NULL DEFAULT 0 '
                        'REFERENCES mapTriglavianStatus (trigStatusID) ON UPDATE CASCADE ON DELETE CASCADE;')

            #Adding Edecom Minor victory systems
            print("SMT: Adding Edecom Minor victory systems")
            cur.execute('UPDATE mapSolarSystems SET trigStatusID=1 WHERE solarSystemID IN (30003088,30003894'
                        ',30004302,30005074,30003570,30003463,30003788,30002724,30002999,30000102,30003919'
                        ',30004978,30004287,30002051,30003823,30005267,30003587,30003904,30005209,30005219'
                        ',30002755,30003824,30002239,30003794,30003927,30000109,30000060,30000160,30004999'
                        ',30004295,30004231,30004284,30003932,30004254,30002513,30002048,30003090,30003478'
                        ',30004289,30003061,30003078,30003900,30002644,30003480,30001696,30002772,30005284'
                        ',30005222,30005086,30003918,30003908,30000012,30003481,30003460,30005213,30005308'
                        ',30003058,30005334,30002506,30003931,30005255,30004263,30000062,30002241,30003558'
                        ',30001376,30004257,30004108,30000048,30003482,30005263,30005066,30004268,30005236'
                        ',30003829,30005034,30003074,30003809,30001718,30004256,30004301,30002397,30003854'
                        ',30001660)') 
            
            #Adding Final Liminality Systems
            print("SMT: Adding Final Liminality systems")
            cur.execute('UPDATE mapSolarSystems SET trigStatusID=2 WHERE solarSystemID IN (30002079,30002652'
                        ',30002411,30005005,30000021,30002797,30031392,30001413,30000206,30040141,30045328'
                        ',30002770,30003504,30002737,30000192,30000157,30001372,30002702,30003046,30020141'
                        ',30045329,30002225,30001381,30001445,30010141,30005029,30003495)') 

            #Adding Fortress Systems
            print("SMT: Adding Fortress systems")
            cur.execute('UPDATE mapSolarSystems SET trigStatusID=3 WHERE solarSystemID IN (30003539,30003573'
                        ',30005251,30004103,30000118,30004090,30003548,30000113,30002386,30004973,30002266'
                        ',30002530,30004141,30002253,30003398,30003490,30003556,30002385,30002704,30005058'
                        ',30004305,30003883,30003397,30004084,30003574,30002665,30000188,30003514,30005052'
                        ',30000004,30002242,30005252,30002986,30002700,30003050,30000005,30004250,30003392'
                        ',30003515,30004100,30002662,30045322,30003885,30004248,30003541,30002651,30004150'
                        ',30002251,30005260,30000105,30004992,30002243,30003553)')

            #Adding Triglavian Minor Victory Systems
            print("SMT: Adding Triglavian Minor Victory systems")
            cur.execute('UPDATE mapSolarSystems SET trigStatusID=4 WHERE solarSystemID IN (30045331,30001400'
                        ',30004244,30045345,30001358,30001401,30045354,30002557,30002760,30002795,30004981'
                        ',30001447,30001390,30003076,30000163,30003073,30001391,30002771,30005330,30000205'
                        ',30003856,30002645,30045338,30002575,30001383,30003464,30000182,30001685)')

            #updating Jove Systems Part 1
            print("SMT: Adding Jove Systems Part 1")
            cur.execute('UPDATE mapSolarSystems SET hasJoveObservatory=1 WHERE solarSystemName IN ("0-4VQL"'
                        ',"0-ARFO","0-G8NO","0-U2M4","0-VG7A","0-WVQS","0-XIDJ","01TG-J","08S-39","0D-CHA"'
                        ',"0LTQ-C","0LY-W1","0MV-4W","0P-U0Q","12YA-2","15U-JY","16AM-3","1GT-MA","1KAW-T"'
                        ',"1N-FJ8","1NZV-7","1PF-BC","1QZ-Y9","1VK-6B","1W-0KS","1ZF-PJ","2-F3OE","2-KPW6"'
                        ',"25S-6P","28O-JY","2B-3M4","2B7A-3","2G38-I","2IGP-1","2PLH-3","2UK4-N","2ULC-J"'
                        ',"2V-CS5","2WU-XT","3-BADZ","3-JG3X","3-LJW3","33RB-O","373Z-7","37S-KO","39-DGG"'
                        ',"3D5K-R","3DR-CR","3GD6-8","3IK-7O","3JN9-Q","3L3N-X","3PPT-9","3Q-VZA","4-07MU"'
                        ',"4-1ECP","4-ABS8","4-CUM5","4-EFLU","4-QDIX","42-UOW","4AZV-W","4CJ-AC","4DTQ-K"'
                        ',"4E-EZS","4K0N-J","4LJ6-Q","4M-P1I","4NDT-W","4O-ZRI","4OIV-X","4RX-EE","4XW2-D"'
                        ',"5-2PQU","5-FGQI","5-O8B1","5-T0PZ","5-VKCN","51-5XG","52G-NZ","57-YRU","5C-RPA"'
                        ',"5E-EZC","5ED-4E","5HN-D6","5J4K-9","5NQI-E","5T-KM3","5W3-DG","5ZXX-K","6-4V20"'
                        ',"6-CZ49","6-I162","6-KPAB","617I-I","62O-UE","6E-MOW","6EK-BV","6F-H3W","6FS-CZ"'
                        ',"6L78-1","6O-XIO","6OYQ-Z","6QBH-S","6U-MFQ","6WW-28","7-8EOE","7-A6XV","7-K5EL"'
                        ',"77-KDQ","7BX-6F","7D-PAT","7LHB-Z","7Q-8Z2","7T-0QS","7X-02R","8-AA98","8-OZU1"'
                        ',"86L-9F","87-1PM","87XQ-0","88A-RA","89-JPE","8B-SAJ","8DL-CP","8F-TK3","8KE-YS"'
                        ',"8P9-BM","8R-RTB","9-02G0","9-266Q","9-8GBA","9-980U","9-ZA4Z","92K-H2","99-0GS"'
                        ',"9IPC-E","9MWZ-B","9N-0HF","9P-870","9PX2-F","9U-TTJ","9UY4-H","A-5M31","A-BO4V"'
                        ',"A-GPTM","A-HZYL","A1F-22","A1RR-M","A3-LOG","Abai","Abha","Abudban","AC-7LZ"'
                        ',"AC2E-3","Access","Adahum","Adallier","Adiere","Adrallezoen","Adrel","Aeter"'
                        ',"Afivad","Agha","Agtver","AH-B84","Aharalel","Ahkour","Ahrosseas","Ahtulaima"'
                        ',"Aikoro","Aivoli","Aivonen","Ajanen","AJCJ-1","Akhrad","Akkio","Akora","Aldilur"'
                        ',"Alenia","Algasienan","Algogille","Alles","Alsavoinon","Altbrard","Amattens"'
                        ',"Ameinaka","Ami","Amoen","Ana","Anckee","Andole","Andrub","Anka","Annad","Ansasos"'
                        ',"Antollare","APES-G","Arakor","Arant","Arayar","Arbaz","ARBX-9","Ardar","Ardhis"'
                        ',"Ardishapur Prime","Arifsdald","Arnon","Arnstur","Arraron","Arzad","Arzieh"'
                        ',"Asabona","Aset","Asgeir","Asghatil","Ashab","Ashmarir","Asrios","Athinard"'
                        ',"Atonder","Aubonnie","Augnais","Aulbres","Auner","Aunia","Aurejet","Avair"'
                        ',"AX-DOT","B-F1MI","B-G1LG","B-II34","B-VIP9","B-XJX4","B9EA-G","Balle","Bamiette"'
                        ',"Basgerin","Bayuka","Bazadod","BEG-RL","Bekirdod","Bersyrim","BM-VYZ","Bogelek"'
                        ',"Boranai","Bosboger","BOZ1-O","BR-6XP","BU-IU4","BVRQ-O","BW-WJ2","BWF-ZZ"'
                        ',"BY-S36","C-LP3N","C-PEWN","C-VGYO","C-WPWH","C0T-77","C1G-XC","C2X-M5","C3J0-O"'
                        ',"C6C-K9","C8VC-S","Cailanar","Central Point","CHA2-Q","Chamja","Chamume"'
                        ',"Channace","Chanoun","Charmerout","Cherore","Chibi","CHP-76","CIS-7X","CJF-1P"'
                        ',"CJNF-J","CL-J9W","Claulenne","CNHV-M","Colelie","CR-0E5","Crielere","Croleur"'
                        ',"CT7-5V","CT8K-0","Cumemare","CX-1XF","D-0UI0","D-6H64","D-6WS1","D-FVI7"'
                        ',"D-I9HJ","D-W7F0","DAI-SH","Dastryns","DDI-B7","DE71-9","Defsunun","DGDT-3"'
                        ',"Dihra","Dimoohan","DJK-67","DK0-N8","Dom-Aphis","Doussivitte","Dunraelare"'
                        ',"DUU1-K","DUV-5Y","DY-40Z","E-B957","E-BFLT","E-BYOS","E-DOF2","E-FIC0"'
                        ',"E-VKJV","E-WMT7","E3-SDZ","E51-JE","E7VE-V","Earwik","Ebidan","Ebtesham"'
                        ',"ED-L9T","Egbonbet","Eglennaert","Egmar","EIH-IU","EK2-ET","EKPB-3","Ekura"'
                        ',"Enaluri","EOY-BG","EPCD-D","Eram","Erindur","Erstet","Erstur","Erzoh","ES-UWY"'
                        ',"Esteban","Esubara","Eszur","ETO-OT","EU0I-T","EUU-4N","Evaulon","EX-0LQ","Eygfe"'
                        ',"Eygfe","Eystur","F-749O","F-9PXR","F-TQWO","F-UVBV","F-ZBO0","F2-NXA","F3-8X2"'
                        ',"F39H-1","F4R2-Q","F5-CGW","F5FO-U","F69O-M","F9E-KX","Fabin","Fanathor","Faspera"'
                        ',"Faswiba","FD-MLJ","FDZ4-A","FE-6YQ","Fihrneh","Fildar","Firbha","Fluekele","Fovihi")')
            
            #updating Jove Systems Part 2
            print("SMT: Adding Jove Systems Part 2")
            cur.execute('UPDATE mapSolarSystems SET hasJoveObservatory=1 WHERE solarSystemName IN ("Frarn"'
                        ',"FRTC-5","FS-RFL","FSW-3C","FV-SE8","FV-YEA","FV1-RQ","FYD-TO","G-4H4C","G-AOTH"'
                        ',"G-G78S","G-ME2K","G-UTHL","G-YZUX","G2-INZ","G8AD-C","G9L-LP","Galeh","Gallareue"'
                        ',"Gallusiene","GC-LTF","GDHN-K","GE-94X","Gidali","GK5Z-T","GL6S-2","GN-PDU","GN7-XY"'
                        ',"GPD5-0","GQ2S-8","GR-X26","GTB-O4","GU-9F4","Gulfonodi","Gyerzen","H-29TM","H-EBQG"'
                        ',"H-HWQR","H-NOU5","H-S80W","H4X-0I","H5N-V7","H8-ZTO","H90-C9","Habu","Hadji","Hadonoo"'
                        ',"Hahyil","Haine","Hakeri","Hakodan","Hakonen","Hakshma","Halenan","Halibai","Hasama"'
                        ',"Hasateem","HB-1NJ","HB-5L3","HBD-CC","HD-AJ7","HD-HOZ","Hedaleolfarber","Hegfunden"'
                        ',"Hesarid","Heydieles","HG-YEQ","HHE5-L","HIK-MC","Hikansog","Hilaban","Hilfhurmur"'
                        ',"Hiremir","Hishai","Hjoramold","HKYW-T","HL-VZX","HM-XR2","HMF-9D","HO4E-Q","Hodrold"'
                        ',"Hoona","Hoseen","HP-6Z6","HPBE-D","HPV-RJ","Hrokkur","Hulmate","Huna","Hutian"'
                        ',"Hykanima","Hysera","I-7JR4","I-8D0G","I-9GI1","I-CUVX","I-MGAB","I6-SYN","I9-ZQZ"'
                        ',"IAK-JW","IBOX-2","IG-4OF","IGE-RI","Ihal","Ikoskio","Illamur","Immuri","Innia"'
                        ',"IO-R2S","IP6V-X","IPX-H5","IRD-HU","Irjunen","IS-R7P","Isenan","Ishomilken","Isid"'
                        ',"Isseras","Isutaka","Ithar","Itsyamil","Ivih","IX8-JB","Iyen-Oursta","J-AYLV","J-OAH2"'
                        ',"J-RXYN","J055520","J110145","J164710","J174618","J200727","J52-BH","J7-BDX","J7A-UR"'
                        ',"J7X-VN","J9A-BH","JA-G0T","JA-O6J","Jakanerva","Jambu","JAUD-V","JC-YX8","Jennim"'
                        ',"JEQG-7","JGOW-Y","JI1-SY","JKJ-VJ","JLO-Z3","Jondik","Joppaya","JPEZ-R","JQU-KY"'
                        ',"JT2I-7","JU-UYK","Juddi","JWZ2-V","JXQJ-B","JZ-B5Y","JZ-UQC","JZV-F4","K-MGJ7"'
                        ',"K-X5AX","K-XJJT","K-YL9T","K1Y-5H","K3JR-J","K42-IE","K7-LDX","K76A-3","Kaunokka"'
                        ',"Kausaaja","KBAK-I","KCT-0A","KD-KPR","KED-2O","KEJY-U","Kerepa","KFR-ZE","KGCF-5"'
                        ',"KGT3-6","Khabara","Kirras","KMC-WI","KMH-J1","KMV-CQ","Knophtikoo","Komaa","Komo"'
                        ',"Konola","Korama","KPI-OW","KQK1-2","KR8-27","Krilmokenur","Kuharah","Kuhri","Kulelen"'
                        ',"Kurniainen","Kusomonmon","KW-OAM","L-1SW8","L-AS00","L-QQ6P","L-TOFR","L-Z9NB","L5-UWT"'
                        ',"L6B-0N","L7XS-5","L8-WNE","Laah","Lamadent","Lari","Larkugei","Lasleinur","LBC-AW"'
                        ',"LD-2VL","LE-67X","Leremblompes","Lermireve","LGK-VP","LGL-SD","Lirerim","LMM7-L"'
                        ',"LQ-OAI","LRWD-B","LS9B-9","LW-YEW","LX-ZOJ","M-CNUD","M-HU4V","M-NP5O","M-SRKS"'
                        ',"M2-2V1","M4-KX5","M9-FIB","Madomi","Mahtista","Maire","Malma","Mani","Marosier"'
                        ',"Masanuh","MC4C-H","Mendori","Mercomesier","Merolles","Mesybier","MGAM-4","MH9C-S"'
                        ',"Miah","MJ-5F9","MJYW-3","MJYW-3","MKD-O8","Moclinamaud","MOCW-2","Moh","Mora"'
                        ',"Mormoen","Moro","MQ-O27","MS1-KJ","MTO2-2","Murzi","MXX5-9","Mya","MZ1E-P","MZLW-9"'
                        ',"N-I024","N-O53U","N-Q5PW","N-RAEL","N-RMSH","N-TFXK","N-YLOE","N5Y-4N","N7-BIY"'
                        ',"Nadohman","Nahrneder","Nakis","Nakregde","Nakri","Nakugard","Nasreri","NB-ALM"'
                        ',"NBW-GD","NE-3GR","Nedegulf","NEH-CS","Nema","New Eden","NG-M8K","Nidebora","Nifshed"'
                        ',"Nimambal","Nisuwa","NIZJ-0","NJ4X-S","Nomaa","Nomash","Nouta","NS2L-4","NSBE-L")')

            #updating Jove Systems Part 3
            print("SMT: Adding Jove Systems Part 3")
            cur.execute('UPDATE mapSolarSystems SET hasJoveObservatory=1 WHERE solarSystemName IN ("NSI-MW"'
                        ',"Nuken","NZW-ZO","O-7LAI","O-CT8N","O-IVNH","O-JPKH","O-LR1H","O-MCZR","O-N589"'
                        ',"O-QKSM","O1Y-ED","O2O-2X","O3L-95","O7-7UX","Obanen","Oberen","Obrolber","Odin"'
                        ',"Odinesyn","Odinesyn","Ogaria","OGL8-Q","OGY-6D","Ohkunen","Oicx","Oishami"'
                        ',"OJ-CT4","OKEO-X","Onatoh","Onnamon","OP7-BP","Ordize","Orien","Osaa","Ossa"'
                        ',"Osvetur","Otelen","OTJ9-E","Otomainen","Otraren","OU-X3P","Ourapheh","Outuni"'
                        ',"OXC-UL","OXIY-V","P3EN-E","P5-EFH","P65-TA","P7MI-T","P7Z-R3","P8-BKO","P9F-ZG"'
                        ',"Pain","Parses","Pashanai","Paye","PE-H02","PE-SAM","PEK-8Z","Pera","Pertnineere"'
                        ',"Peyiri","PFV-ZH","Phoren","Pimsu","PNS7-J","PO-3QW","Poitot","POQP-K","PQRE-W"'
                        ',"Pserz","Pucherie","PWPY-4","PXF-RF","PZMA-E","Q-K2T7","Q-NA5H","Q-NJZ4","Q-R3GP"'
                        ',"Q-XEB3","Q1-R7K","Q1U-IU","QA1-BT","QBL-BV","QFRV-2","QHH-13","QK-CDG","QKTR-L"'
                        ',"QM-20X","QOK-SX","QQ3-YI","QR-K85","QSCO-D","QY6-RK","R-2R0G","R-ARKN","R-ESG0"'
                        ',"R-ORB7","R0-DMM","R1O-GN","R3W-XU","Raa","Raihbaka","Rakapas","Raneilles","Rannoze"'
                        ',"Rauntaka","Rayeret","RD-FWY","Remoriu","Reteka","RF-CN3","Rimbah","RJBC-I","RO-0PZ"'
                        ',"Rokofur","RORZ-H","Roushzar","RUF3-O","Rumida","Ruvas","RXA-W1","RY-2FX","RYQC-I"'
                        ',"RZ-PIY","RZC-16","S-1LIO","S-51XG","S-DN5M","S-MDYI","S-NJBB","S5W-1Z","S8-NSQ"'
                        ',"Safilbab","Saikamon","Sakulda","Salah","Salashayama","Saminer","Sankkasen","Santola"'
                        ',"Sassecho","Sasta","Sazre","Scolluzer","Scuelazyns","Seiradih","Sendaya","Serad"'
                        ',"Seshala","SH1-6P","SH6X-F","Shach","Shaha","Shala","Shamahi","Sharji","Sharuveil"'
                        ',"Shenela","Shihuken","Shuria","Sibe","Sigga","Simela","Sirekur","Sist","Situner"'
                        ',"SN9S-N","SNFV-I","Sobenah","Somouh","Sosan","Sotrentaira","Soza","SPLE-Y","SR-KBB"'
                        ',"Stegette","Stoure","SVB-RE","SY-OLX","SY-UWN","SZ6-TA","T-0JWP","T-AKQZ","T-K10W"'
                        ',"T-LIWS","T-Q2DD","T-Z6J2","TA9T-P","Tabbetzur","Tahli","TAL1-3","Talidal","Tama"'
                        ',"Tartoken","TCAG-3","TDE4-H","Teshkat","Teskanen","TET3-B","Tew","TFPT-U","Thakala"'
                        ',"Tierijev","TJM-JJ","TL-T9Z","Toustain","Tralasa","TU-O0T","Tunttaras","TV8-HS"'
                        ',"TXME-A","TYB-69","Tzashrah","U-BXU9","U-INPD","U-MFTL","U-QMOA","U-RELP","U-TJ7Y"'
                        ',"U104-3","U2-28D","U93O-A","U9SE-N","U9U-TQ","UAYL-F","UB5Z-3","UC3H-Y","Uchomida"'
                        ',"UD-VZW","UI-8ZE","Ukkalen","UKYS-5","Unel","UNJ-GX","Uotila","Uoyonen","Ustnia"'
                        ',"UT-UZB","Uusanen","UVHO-F","UYU-VV","V-F6DQ","V-QXXK","V0DF-2","V6-NY1","V7D-JD"'
                        ',"V89M-R","Valmu","Varigne","VBPT-T","Vecamia","VI2K-J","Vifrevaert","VQE-CN"'
                        ',"Vuorrassi","VVB-QH","VWES-Y","W-4FA9","W-UQA5","W6V-VM","WB-AYY","WEQT-K","Weraroix"'
                        ',"WFFE-4","WH-2EZ","WH-JCA","WHG2-7","WIO-OL","WPV-JN","WV-0R2","WV0D-1","WW-KGD"'
                        ',"Wysalan","X-0CKQ","X-41DA","X-CYNC","X-EHHD","X-M9ON","X-Z4JW","X36Y-G","X5O1-L"'
                        ',"X6-J6R","X9V-15","XA5-TY","XCBK-X","XD-TOV","XFBE-T","XKM-DE","XQP-9C","XSQ-TF"'
                        ',"XT-R36","XTVZ-E","XU7-CH","XUPK-Z","Y-770C","Y-C4AL","Y-EQ0C","Y-FZ5N","Y-K50G"'
                        ',"Y-ORBJ","Y-RAW3","Y-XZA7","Y1-UQ2","Y19P-1","Y4-GQV","Y6-HPG","Yashunen","Yeder"'
                        ',"Yeeramoun","YG-82V","Yoma","YQM-P1","YRNJ-8","YRV-MZ","Yuhelia","YUY-LM","Yuzier"'
                        ',"Yvelet","YZ9-F6","Z-2Y2Y","Z-7OK1","Z-8Q65","Z-K495","Z-M5A1","Z-N9IP","Z-PNIA"'
                        ',"Z-UZZN","Z-YN5Y","Z3V-1W","Z9PP-H","ZA0L-U","Zahefeus","Zaimeth","ZD1-Z2","ZID-LE"'
                        ',"Ziona","Ziriert","ZK-YQ3","ZM-DNR","ZN0-SR","ZO-4AR","ZO-P5K","ZOPZ-6","ZOYW-O"'
                        ',"ZQ-Z3Y","ZXB-VC","ZZK-VF","Uplingur","LTT-AP")')

            self.conn.commit()
        except:
            print("SMT: Error ... ")
            self.conn.rollback()
        cur.close()
        del cur

    def checkDatabase(self):
        """Function that verifies the database"""
        if self.isSqLite3():
            return True
        return False

    def vacumm(self):
        """Reduce the size of the database eliminating all the empty spare space left in the file"""
        cur = self.conn.cursor()
        cur.execute('VACUUM')
        cur.close()
        del cur
        pass

    def recreateData(self):
        """Function that recreates the basic data in the newly cretaed database"""
        pass

# databaseCreator

Utility to dump SDE data into a ralational database

Supported Databases:

  * SQLite

The tool can be customized to import just what do you need, and discard everything else

What data it is exported

  * Solar Systems (Planets, Moons, Stars)
  * Regions
  * Constellations
  * NPC stations
  * Gates

TODO:

  * support more databases engines
  * support more customizing settings

Dependencies:

  * Python >= 3.8.0
  * PyYAML >= 6.0
  * classutilities >= 0.2.1
  
How to use it:
 
 Linux/UNIX: Make databaseBuilder.py executable using ```chmod u+x databaseBuilder.py```
 
 Run directly from shell ```./databaseBuilder.py```
 
 or using python ```python3 ./databaseBuilder.py```

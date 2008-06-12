"""Backend providers for Geniusql."""

import re
from geniusql import xray


class Version(object):
    
    def __init__(self, atoms):
        if isinstance(atoms, (int, float)):
            atoms = str(atoms)
        if isinstance(atoms, basestring):
            self.atoms = re.split(r'\W', atoms)
        else:
            self.atoms = [str(x) for x in atoms]
    
    def __str__(self):
        return ".".join([str(x) for x in self.atoms])
    
    def __cmp__(self, other):
        cls = self.__class__
        if not isinstance(other, cls):
            # Try to coerce other to a Version instance.
            other = cls(other)
        
        index = 0
        while index < len(self.atoms) and index < len(other.atoms):
            mine, theirs = self.atoms[index], other.atoms[index]
            if mine.isdigit() and theirs.isdigit():
                mine, theirs = int(mine), int(theirs)
            if mine < theirs:
                return -1
            if mine > theirs:
                return 1
            index += 1
        if index < len(other.atoms):
            return -1
        if index < len(self.atoms):
            return 1
        return 0


class _Registry(dict):
    
    def open(self, key, **kwargs):
        opener = self[key]
        if isinstance(opener, basestring):
            opener = xray.attributes(opener)
        return opener(**kwargs)

registry = _Registry({
    "access": "geniusql.providers.msaccess.MSAccessDatabase",
    "msaccess": "geniusql.providers.msaccess.MSAccessDatabase",
    
    "firebird": "geniusql.providers.firebird.FirebirdDatabase",
    "mysql": "geniusql.providers.mysql.MySQLDatabase",
    
    "postgres": "geniusql.providers.pypgsql.PyPgDatabase",
    "postgresql": "geniusql.providers.pypgsql.PyPgDatabase",
    "pypgsql": "geniusql.providers.pypgsql.PyPgDatabase",
    
    "psycopg": "geniusql.providers.psycopg.PsycoPgDatabase",
    "psycopg2": "geniusql.providers.psycopg.PsycoPgDatabase",
    
    "sqlite": "geniusql.providers.sqlite.SQLiteDatabase",
    
    "sqlserver": "geniusql.providers.sqlserver.SQLServerDatabase",
    "mssql": "geniusql.providers.sqlserver.SQLServerDatabase",
    })

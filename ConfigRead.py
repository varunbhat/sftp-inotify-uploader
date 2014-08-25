import re


class ConfigRead():
    def __init__(self):
        self.pattern = r'^[ \t]*([A-Za-z_0-9]+)[ \t]*=[ \t]*(.*)(?:#|//|$)'

    def setDefaults(self):
        return 1

    def GetConfig(self, filename, defaults=None):
        f = open(filename, 'r')
        configFileData = f.read()
        f.close()
        res = re.findall(self.pattern, configFileData, re.M)
        resobj = type('resobj', (), dict(__getitem__=lambda self, _key: self.__dict__[_key], all=self.__dict__))()
        resobj.__dict__.update(dict(res))
        self.__dict__.update({"_".join(filename.split(".")[0:-1]): resobj})
        return resobj
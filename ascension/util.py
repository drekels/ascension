NO_VALUE = "NO_VALUE"
NO_DEFAULT = "NO_VALUE"


class IllegalActionException(Exception):
    pass


class Singleton(type):
    instance = None

    def reset(cls, *args, **kwargs):
        cls.instance = cls(*args, **kwargs)

    def __getattribute__(cls, attr):
        instance = super(Singleton, cls).__getattribute__("instance")
        if instance and hasattr(instance, attr):
            return getattr(instance, attr)
        class_attr = super(Singleton, cls).__getattribute__(attr)
        return class_attr


    def __getattr__(cls, attr):
        return getattr(cls.instance, attr)


class ParamDefinition(object):

    def __init__(self, param_definition):
        self.name = param_definition["name"]
        self.default = param_definition.get("default", NO_DEFAULT)
        self.parse = param_definition.get("parse", None)

    def getvalue(self, input_value):
        value = self.default
        if input_value != NO_VALUE:
            value = input_value
        if self.default == NO_DEFAULT:
            raise TypeError("The parameter '{}' requires a value".format(self.name))
        if self.parse:
            value = self.parse(value)
        return value


class SettingSet(object):

    def __init__(self, param_definitions):
        self.param_definitions = [ParamDefinition(x) for x in param_definitions]

    def processvalues(self, targetobj, input_values):
        for param in self.param_definitions:
            setattr(targetobj, param.name, param.getvalue(input_values.get(param.name, NO_VALUE)))


class SettingBased(object):

    def __init__(self, **kwargs):
        self.settingset.processvalues(self, kwargs)


def insert_sort(almost_sorted):
    for i in range(1, len(almost_sorted)):
        val = almost_sorted[i]
        j = i - 1
        while (j >= 0) and (almost_sorted[j] > val):
            almost_sorted[j+1] = almost_sorted[j]
            j = j - 1
        almost_sorted[j+1] = val

NO_VALUE = "NO_VALUE"
NO_DEFAULT = "NO_VALUE"


class Singleton(type):
    instance = None

    def reset(cls, *args, **kwargs):
        cls.instance = cls(*args, **kwargs)

    def __getattribute__(cls, attr, _fromclass=False):
        instance = super(Singleton, cls).__getattribute__("instance")
        if instance and hasattr(instance, attr):
            return getattr(instance, attr)
        return super(Singleton, cls).__getattribute__(attr)


    def __getattr__(cls, attr):
        return getattr(cls.instance, attr)


class ParamDefinition(object):

    def __init__(self, param_definition):
        self.name = param_definition["name"]
        self.default = param_definition.get("default", NO_DEFAULT)

    def getvalue(self, input_value):
        if input_value != NO_VALUE:
            return input_value
        if self.default == NO_DEFAULT:
            raise TypeError("The parameter '{}' requires a value".format(self.name))
        return self.default


class SettingSet(object):

    def __init__(self, param_definitions):
        self.param_definitions = [ParamDefinition(x) for x in param_definitions]

    def processvalues(self, targetobj, input_values):
        for param in self.param_definitions:
            setattr(targetobj, param.name, param.getvalue(input_values.get(param.name, NO_VALUE)))


class SettingBased(object):

    def __init__(self, **kwargs):
        self.settingset.processvalues(self, kwargs)

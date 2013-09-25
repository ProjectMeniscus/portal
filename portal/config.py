import os.path

from ConfigParser import ConfigParser


_CFG_DEFAULTS = {
    'core': {
        'processes': 1,
        'syslog_bind_host': 'localhost:5140',
        'zmq_bind_host': 'localhost:5000'
    },
    'logging': {
        'console': True,
        'logfile': '/var/log/meniscus-portal/portal.log',
        'verbosity': 'WARNING'
    }
}


def _host_tuple(host_str):
    if host_str:
        parts = host_str.split(':')
        if len(parts) == 1:
            return (parts[0], 80)
        elif len(parts) == 2:
            return (parts[0], int(parts[1]))
        else:
            raise Exception('Malformed host: {}'.format(host))
    return None


def load_config(location='/etc/meniscus-portal/portal.conf'):
    if not os.path.isfile(location):
        raise Exception(
            'Unable to locate configuration file: {}'.format(location))
    cfg = ConfigParser()
    cfg.read(location)
    return PortalConfiguration(cfg)


class PortalConfiguration(object):
    """
    A Portal configuration.
    """
    def __init__(self, cfg):
        self.core = CoreConfiguration(cfg)
        self.logging = LoggingConfiguration(cfg)


class ConfigurationObject(object):
    """
    A configuration object is an OO abstraction for a ConfigParser that allows
    for ease of documentation and usage of configuration options. All
    subclasses of ConfigurationObject must follow a naming convention. A
    configuration object subclass must start with the name of its section. This
    must then be followed by the word "Configuration." This convention results
    in subclasses with names similar to: CoreConfiguration and
    LoggingConfiguration.

    A configuration object subclass will have its section set to the lowercase
    name of the subclass sans the word such that a subclass with the name,
    "LoggingConfiguration" will reference the ConfigParser section "logging"
    when looking up options.
    """
    def __init__(self, cfg):
        self._cfg = cfg
        self._namespace = self._format_namespace()

    def __getattr__(self, name):
        return self._get(name)

    def _format_namespace(self):
        return type(self).__name__.replace('Configuration', '').lower()

    def _options(self):
        return self._cfg.options(self._namespace)

    def _has_option(self, option):
        return self._cfg.has_option(self._namespace, option)

    def _get_default(self, option):
        if option in _CFG_DEFAULTS[self._namespace]:
            return _CFG_DEFAULTS[self._namespace][option]
        return None

    def _get(self, option):
        if self._has_option(option):
            return self._cfg.get(self._namespace, option)
        else:
            return self._get_default(option)

    def _getboolean(self, option):
        if self._has_option(option):
            return self._cfg.getboolean(self._namespace, option)
        else:
            return self._get_default(option)

    def _getint(self, option):
        if self._has_option(option):
            return self._cfg.getint(self._namespace, option)
        else:
            return self._get_default(option)


class CoreConfiguration(ConfigurationObject):
    """
    Class mapping for the Portal configuration section 'core'
    """
    @property
    def processes(self):
        """
        Returns the number of processess Portal should spin up to handle
        messages. If unset, this defaults to 1.

        Example
        --------
        processes = 0
        """
        return self._getint('processes')

    @property
    def syslog_bind_host(self):
        """
        Returns a tuple of  host and port that portal is expected to bind
        to when accepting syslog client connections. This option defaults
        to localhost:5140 if left unset.

        Example
        --------
        bind_host = localhost:5140
        """
        return _host_tuple(self._get('syslog_bind_host'))

    @property
    def zmq_bind_host(self):
        """
        Returns a tuple of  host and port that portal is expected to bind
        to when accepting upstream worker connections. This option defaults
        to localhost:5140 if left unset.

        Example
        --------
        bind_host = localhost:5000
        """
        return _host_tuple(self._get('zmq_bind_host'))


class LoggingConfiguration(ConfigurationObject):
    """
    Class mapping for the Portal configuration section 'logging'
    """
    @property
    def console(self):
        """
        Returns a boolean representing whether or not Portal should write to
        stdout for logging purposes. This value may be either True of False. If
        unset this value defaults to False.
        """
        return self._get('console')

    @property
    def logfile(self):
        """
        Returns the log file the system should write logs to. When set, Portal
        will enable writing to the specified file for logging purposes If unset
        this value defaults to None.
        """
        return self._get('logfile')

    @property
    def verbosity(self):
        """
        Returns the type of log messages that should be logged. This value may
        be one of the following: DEBUG, INFO, WARNING, ERROR or CRITICAL. If
        unset this value defaults to WARNING.
        """
        return self._get('verbosity')

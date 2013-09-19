from libc.string cimport strlen
from libc.stdlib cimport malloc, free
from cpython cimport bool, PyBytes_FromStringAndSize, PyBytes_FromString

import os


class SyslogError(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class ParsingError(SyslogError):

    def __init__(self, msg, cause):
        super(ParsingError, self).__init__(msg)
        self.cause = cause

    def __str__(self):
        try:
            formatted = 'Error: {}'.format(self.msg)
            if self.cause:
                cause_msg = '  Caused by: {}'.format(
                    getattr(self.cause, 'msg', str(self.cause)))
                return '\n'.join((formatted, cause_msg))
            return formatted
        except Exception as ex:
            return str(ex)


class SyslogMessageHandler(object):

    def __init__(self):
        self.msg = ''
        self.msg_head = None

    def on_msg_head(self, message_head):
        pass

    def on_msg_part(self, message_part):
        pass

    def on_msg_complete(self, message_size):
        pass


class SyslogMessageHead(object):

    def __init__(self):
        self.reset()

    def reset(self):
        self.priority = ''
        self.version = ''
        self.timestamp = ''
        self.hostname = ''
        self.appname = ''
        self.processid = ''
        self.messageid = ''
        self.sd = dict()
        self.current_sde = None
        self.current_sd_field = None

    def get_sd(self, name):
        return self.sd.get(name)

    def create_sde(self, sd_name):
        self.current_sde = dict()
        self.sd[sd_name] = self.current_sde

    def set_sd_field(self, sd_field_name):
        self.current_sd_field = sd_field_name

    def set_sd_value(self, value):
        self.current_sde[self.current_sd_field] = value

    def as_dict(self):
        sd_copy = dict()
        dictionary = {
            'priority': str(self.priority),
            'version': str(self.version),
            'timestamp': str(self.timestamp),
            'hostname': str(self.hostname),
            'appname': str(self.appname),
            'processid': str(self.processid),
            'messageid': str(self.messageid),
            'sd': sd_copy
        }

        for sd_name in self.sd:
            sd_copy[sd_name] = dict()
            for sd_fieldname in self.sd[sd_name]:
                value = self.sd[sd_name][sd_fieldname]
                sd_copy[sd_name][sd_fieldname] = value.decode('utf-8')
        return dictionary


cdef int on_msg_begin(syslog_parser *parser):
    cdef object parser_data = <object> parser.app_data
    parser_data.msg_head.reset()

    return 0


cdef int on_sd_element(syslog_parser *parser, char *data, size_t size):
    cdef object parser_data = <object> parser.app_data
    cdef object pystr = PyBytes_FromStringAndSize(data, size)

    try:
        parser_data.msg_head.create_sde(pystr)
    except Exception:
        return -1
    return 0


cdef int on_sd_field(syslog_parser *parser, char *data, size_t size):
    cdef object parser_data = <object> parser.app_data
    cdef object pystr = PyBytes_FromStringAndSize(data, size)

    try:
        parser_data.msg_head.set_sd_field(pystr)
    except Exception:
        return -1
    return 0


cdef int on_sd_value(syslog_parser *parser, char *data, size_t size):
    cdef object parser_data = <object> parser.app_data
    cdef object pystr = PyBytes_FromStringAndSize(data, size)

    try:
        parser_data.msg_head.set_sd_value(pystr)
    except Exception:
        return -1
    return 0


cdef int on_msg_head_complete(syslog_parser *parser):
    cdef object parser_data = <object> parser.app_data

    parser_data.msg_head.priority = str(parser.msg_head.priority)
    parser_data.msg_head.version = str(parser.msg_head.version)

    parser_data.msg_head.timestamp = PyBytes_FromStringAndSize(
        parser.msg_head.timestamp.bytes,
        parser.msg_head.timestamp.size)

    parser_data.msg_head.hostname = PyBytes_FromStringAndSize(
        parser.msg_head.hostname.bytes,
        parser.msg_head.hostname.size)

    parser_data.msg_head.appname = PyBytes_FromStringAndSize(
        parser.msg_head.appname.bytes,
        parser.msg_head.appname.size)

    parser_data.msg_head.processid = PyBytes_FromStringAndSize(
        parser.msg_head.processid.bytes,
        parser.msg_head.processid.size)

    parser_data.msg_head.messageid = PyBytes_FromStringAndSize(
        parser.msg_head.messageid.bytes,
        parser.msg_head.messageid.size)

    try:
        parser_data.msg_handler.on_msg_head(parser_data.msg_head)
    except Exception:
        return -1
    return 0


cdef int on_msg_part(syslog_parser *parser, char *data, size_t size):
    cdef object parser_data = <object> parser.app_data
    cdef object pystr = PyBytes_FromStringAndSize(data, size)

    try:
        parser_data.msg_handler.on_msg_part(pystr)
    except Exception:
        return -1
    return 0


cdef int on_msg_complete(syslog_parser *parser):
    cdef object parser_data = <object> parser.app_data

    try:
        parser_data.msg_handler.on_msg_complete(parser.message_length)
    except Exception:
        return -1
    return 0


cdef class Parser(object):

    cdef syslog_parser_settings *_cparser_settings
    cdef syslog_parser *_cparser
    cdef object _data

    def __init__(self, msg_handler):
        self._data = ParserData(msg_handler)

        # Init the parser
        self._cparser = <syslog_parser *> malloc(sizeof(syslog_parser))
        uslg_parser_init(self._cparser, <void *> self._data)

        # Init our callbacks
        self._cparser_settings = <syslog_parser_settings *> malloc(
            sizeof(syslog_parser_settings))

        self._cparser_settings.on_msg_begin = <syslog_cb> on_msg_begin
        self._cparser_settings.on_sd_element = <syslog_data_cb> on_sd_element
        self._cparser_settings.on_sd_field = <syslog_data_cb> on_sd_field
        self._cparser_settings.on_sd_value = <syslog_data_cb> on_sd_value
        self._cparser_settings.on_msg_head_complete = <syslog_cb> on_msg_head_complete
        self._cparser_settings.on_msg_part = <syslog_data_cb> on_msg_part
        self._cparser_settings.on_msg_complete = <syslog_cb> on_msg_complete

    def __dealloc__(self):
        if self._cparser != NULL:
            uslg_free_parser(self._cparser)
            self._cparser = NULL

    def read(self, data):
        if isinstance(data, str):
            strval = data
        elif isinstance(data, bytearray):
            strval = str(data)
        elif isinstance(data, unicode):
            strval = data.encode('utf-8')

        result = uslg_parser_exec(
            self._cparser,
            self._cparser_settings,
            strval,
            len(strval))

        if result:
            error_pystr = PyBytes_FromString(uslg_error_string(result))

            raise ParsingError(
                msg=error_pystr,
                cause=self._data.exception)

    def reset(self):
        uslg_parser_reset(self._cparser)
        self._data.msg_handler.msg_head = None
        self._data.msg_head = SyslogMessageHead()


class ParserData(object):

    def __init__(self, msg_handler):
        self.msg_handler = msg_handler
        self.msg_head = SyslogMessageHead()
        self.exception = None

import os
from cffi import FFI

FFI = FFI()
FFI.cdef("""
// Type definitions
typedef struct pbuffer pbuffer;
typedef struct syslog_parser syslog_parser;
typedef struct syslog_msg_head syslog_msg_head;
typedef struct syslog_parser_settings syslog_parser_settings;

typedef int (*syslog_cb) (syslog_parser *parser);
typedef int (*syslog_data_cb) (syslog_parser *parser, const char *data, size_t len);

// Structs
struct pbuffer {
    char *bytes;
    size_t position;
    size_t size;
};

struct syslog_msg_head {
    // Numeric Fields
    unsigned short priority;
    unsigned short version;

    // String Fields
    char *timestamp;
    size_t timestamp_len;

    char *hostname;
    size_t hostname_len;

    char *appname;
    size_t appname_len;

    char *processid;
    size_t processid_len;

    char *messageid;
    size_t messageid_len;
};

struct syslog_parser_settings {
    syslog_cb         on_msg_begin;
    syslog_cb         on_msg_head;
    syslog_data_cb    on_sd_element;
    syslog_data_cb    on_sd_field;
    syslog_data_cb    on_sd_value;
    syslog_data_cb    on_msg_part;
    syslog_cb         on_msg_complete;
};

struct syslog_parser {
    // Parser fields
    unsigned char flags : 3;
    unsigned char token_state;
    unsigned char state;

    // Errors
    unsigned char error;

    // Message head
    struct syslog_msg_head *msg_head;

    // Byte tracking fields
    uint32_t message_length;
    uint32_t octets_remaining;
    uint32_t octets_read;

    // Buffer
    pbuffer *buffer;

    // Optionally settable application data pointer
    void *app_data;
};

// Functions
void uslg_parser_reset(syslog_parser *parser);
void uslg_free_parser(syslog_parser *parser);

int uslg_parser_init(syslog_parser *parser, void *app_data);
int uslg_parser_exec(syslog_parser *parser, const syslog_parser_settings *settings, const char *data, size_t length);

char * uslg_error_string(int error);
""")

USYSLOG_LIB = FFI.verify(
    """
    #include "usyslog.h"
    """,
    include_dirs=['./include'],
    sources=['./include/usyslog.c'])
#   Uncomment the line below for debug output
#    extra_compile_args=['-D DEBUG_OUTPUT'])

FFI.cdef("""
// C stdlib Functions
size_t strlen(const char *);
""")

C_LIB = FFI.dlopen(None)


class SyslogError(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class ParsingError(SyslogError):

    def __init__(self, msg, cause):
        super(ParsingError, self).__init__(msg)
        self.cause = cause


class SyslogMessageHandler(object):

    def __init__(self):
        self.msg = ''
        self.msg_head = None

    def on_msg_head(self, message_head):
        pass

    def on_msg_part(self, message_part):
        pass

    def on_msg_complete(self, message_part):
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
                sd_copy[sd_name][sd_fieldname] = self.sd[
                    sd_name][sd_fieldname].decode('utf-8')
        return dictionary


@FFI.callback("int (syslog_parser *parser)")
def on_msg_begin(parser):
    return 0

@FFI.callback("int (syslog_parser *parser, const char *data, size_t len)")
def on_sd_element(parser, data, size):
    parser_data = FFI.from_handle(parser.app_data)

    try:
        msg_head = parser_data.msg_head
        sd_element = FFI.string(data, size)
        msg_head.create_sde(sd_element)
    except Exception as ex:
        parser_data.exception = ex
        return 1
    return 0

@FFI.callback("int (syslog_parser *parser, const char *data, size_t len)")
def on_sd_field(parser, data, size):
    parser_data = FFI.from_handle(parser.app_data)

    try:
        msg_head = parser_data.msg_head
        sd_field = FFI.string(data, size)
        msg_head.set_sd_field(sd_field)
    except Exception as ex:
        parser_data.exception = ex
        return 1
    return 0

@FFI.callback("int (syslog_parser *parser, const char *data, size_t len)")
def on_sd_value(parser, data, size):
    parser_data = FFI.from_handle(parser.app_data)

    try:
        msg_head = parser_data.msg_head
        sd_value = FFI.string(data, size)
        msg_head.set_sd_value(sd_value)
    except Exception as ex:
        parser_data.exception = ex
        return 1
    return 0

@FFI.callback("int (syslog_parser *parser)")
def on_msg_head(parser):
    parser_data = FFI.from_handle(parser.app_data)

    try:
        msg_head = parser_data.msg_head
        msg_head.priority = str(parser.msg_head.priority)
        msg_head.version = str(parser.msg_head.version)
        msg_head.timestamp = FFI.string(
            parser.msg_head.timestamp,
            parser.msg_head.timestamp_len)
        msg_head.hostname = FFI.string(
            parser.msg_head.hostname,
            parser.msg_head.hostname_len)
        msg_head.appname = FFI.string(
            parser.msg_head.appname,
            parser.msg_head.appname_len)
        msg_head.processid = FFI.string(
            parser.msg_head.processid,
            parser.msg_head.processid_len)
        msg_head.messageid = FFI.string(
            parser.msg_head.messageid,
            parser.msg_head.messageid_len)

        parser_data.msg_handler.on_msg_head(msg_head)
    except Exception as ex:
        parser_data.exception = ex
        return 1
    return 0

@FFI.callback("int (syslog_parser *parser, const char *data, size_t len)")
def on_msg_part(parser, data, size):
    parser_data = FFI.from_handle(parser.app_data)

    try:
        part = FFI.string(data, size)
        parser_data.msg_handler.on_msg_part(part)
    except Exception as ex:
        parser_data.exception = ex
        return 1
    return 0

@FFI.callback("int (syslog_parser *parser)")
def on_msg_complete(parser):
    parser_data = FFI.from_handle(parser.app_data)

    try:
        parser_data.msg_handler.on_msg_complete()
    except Exception as ex:
        parser_data.exception = ex
        return 1
    return 0


class Parser(object):

    def __init__(self, msg_handler):
        self._data = ParserData(msg_handler)
        self._data_ctype = FFI.new_handle(self._data)

        # Init the parser
        self._cparser = FFI.new("syslog_parser *")
        USYSLOG_LIB.uslg_parser_init(self._cparser, self._data_ctype)

        # Init our callbacks
        self._cparser_settings = FFI.new("syslog_parser_settings *")
        self._cparser_settings.on_msg_begin = on_msg_begin
        self._cparser_settings.on_msg_head = on_msg_head
        self._cparser_settings.on_sd_element = on_sd_element
        self._cparser_settings.on_sd_field = on_sd_field
        self._cparser_settings.on_sd_value = on_sd_value
        self._cparser_settings.on_msg_part = on_msg_part
        self._cparser_settings.on_msg_complete = on_msg_complete

    def read(self, bytearray):
        result = USYSLOG_LIB.uslg_parser_exec(
            self._cparser,
            self._cparser_settings,
            bytearray,
            len(bytearray))

        if result:
            error_cstr = USYSLOG_LIB.uslg_error_string(result)
            error_pystr = FFI.string(
                USYSLOG_LIB.uslg_error_string(result),
                C_LIB.strlen(error_cstr))
            raise ParsingError(
                msg=error_pystr,
                cause=self._data.exception)

    def reset(self):
        USYSLOG_LIB.uslg_parser_reset(self._cparser)
        self._data.msg_handler.msg_head = None
        self._data.msg_head = SyslogMessageHead()


class ParserData(object):

    def __init__(self, msg_handler):
        self.msg_handler = msg_handler
        self.msg_head = SyslogMessageHead()
        self.exception = None

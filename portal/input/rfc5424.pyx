from libc.stdlib cimport realloc, malloc, free, atoi
from cpython cimport bool


cdef extern from "Python.h":
    int PyByteArray_Check(object bytearray)
    char* PyByteArray_AsString(object bytearray) except NULL
    Py_ssize_t PyByteArray_Size(object bytearray)

    int PyBytes_Check(object bytes)
    char* PyBytes_AsString(object bytes) except NULL
    Py_ssize_t PyBytes_Size(object bytes)

    object PyUnicode_FromStringAndSize(char *string, Py_ssize_t length)
    object PyString_FromStringAndSize(char *string, Py_ssize_t length)
    object PyByteArray_FromStringAndSize(char *string, Py_ssize_t length)


# Lexer states
cdef enum lexer_state:
    OCTET
    PRIORITY_BEGIN
    PRIORITY
    VERSION
    TIMESTAMP
    HOSTNAME
    APPNAME
    PROCESSID
    MESSAGEID
    STRUCTURED_DATA_BEGIN
    SD_ELEMENT_NAME
    SD_FIELD_NAME
    SD_VALUE_BEGIN
    SD_VALUE_CONTENT
    SD_VALUE_END
    STRUCTURED_DATA_END
    MESSAGE


# Token constants
cdef int NO_TOKENS = 0
cdef int PRIORITY_TOKEN = 1
cdef int VERSION_TOKEN = 2
cdef int TIMESTAMP_TOKEN = 3
cdef int HOSTNAME_TOKEN = 4
cdef int APPNAME_TOKEN = 5
cdef int PROCESSID_TOKEN = 6
cdef int MESSAGEID_TOKEN = 7
cdef int SDE_NAME_TOKEN = 8
cdef int SDE_FIELD_NAME_TOKEN = 9
cdef int SDE_FIELD_VALUE_TOKEN = 10
cdef int MESSAGE_PART_TOKEN = 11
cdef int LAST_MESSAGE_PART_TOKEN = 12


# Delimeter constants
cdef char SPACE = ' '
cdef char DASH = '-'
cdef char QUOTE = '"'
cdef char EQUALS = '='
cdef char OPEN_ANGLE_BRACKET = '<'
cdef char CLOSE_ANGLE_BRACKET = '>'
cdef char OPEN_BRACKET = '['
cdef char CLOSE_BRACKET = ']'

# Size constants
cdef int RFC3164_MAX_BYTES = 1024
cdef int RFC5424_MAX_BYTES = 2048

cdef int MAX_BYTES = 536870912


class SyslogMessageHandler(object):

    def message_head(self, message_head):
        pass

    def message_part(self, message_part):
        pass

    def message_complete(self, message_part):
        pass

class SyslogMessageHead(object):

    def __init__(self):
        self.priority = ''
        self.version = ''
        self.timestamp = ''
        self.hostname = ''
        self.appname = ''
        self.processid = ''
        self.messageid = ''
        self.sd = dict()

    def get_sd(self, name):
        return self.sd.get(name)

    def create_sd(self, sd_name):
        self.sd[sd_name] = dict()

    def add_sd_field(self, sd_name, sd_fieldname, sd_value):
        self.sd[sd_name][sd_fieldname] = sd_value

    def as_json(self):
        pass

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
                sd_copy[sd_name][sd_fieldname] = self.sd[sd_name][sd_fieldname].decode('utf-8')
        return dictionary


class SyslogParser(object):

    def __init__(self, message_handler=SyslogMessageHandler()):
        self.message = SyslogMessageHead()
        self.sd_name = None
        self.sd_fieldname = None
        self.message_handler = message_handler
        self.message_head_passed = False
        self.cparser = CSyslogParser(self)

    def read(self, bytearray):
        self.cparser.read(bytearray)

    def reset(self):
        self.cparser.reset()
        self.message = SyslogMessageHead()
        self.message_head_passed = False


def set_priority(parser, priority):
    parser.message.priority = priority

def set_version(parser, version):
    parser.message.version = version

def set_timestamp(parser, timestamp):
    parser.message.timestamp = timestamp

def set_hostname(parser, hostname):
    parser.message.hostname = hostname

def set_appname(parser, appname):
    parser.message.appname = appname

def set_processid(parser, processid):
    parser.message.processid = processid

def set_messageid(parser, messageid):
    parser.message.messageid = messageid

def create_sd_element(parser, name):
    parser.message.create_sd(name)

def add_sd_field(parser, name, field_name, value):
    parser.message.add_sd_field(name, field_name, value)

def hand_off_message_head(parser):
    try:
        parser.message_handler.message_head(parser.message)
    except Exception as ex:
        print('Failure: {}'.format(ex))

def message_part(parser, message_part):
    try:
        parser.message_handler.message_part(message_part)
    except Exception as ex:
        print('Failure: {}'.format(ex))

def message_complete(parser, last_message_part):
    try:
        parser.message_handler.message_complete(last_message_part)
    except Exception as ex:
        print('Failure: {}'.format(ex))


cdef class CSyslogParser(object):

    cdef SyslogLexer lexer
    cdef object python_wrapper, sde_name, sde_field_name
    cdef bool message_head_passed

    def __cinit__(self):
        self.lexer = SyslogLexer()
        self.message_head_passed = False

    def __init__(self, object python_wrapper):
        self.python_wrapper = python_wrapper

    def _lexer(self):
        return self.lexer

    def read(self, object bytearray):
        self._read(bytearray)

    cdef void _read(self, object data):
        cdef int bytes_left = 0
        if PyByteArray_Check(data):
            bytes_left = PyByteArray_Size(data)
            self.lexer.set_data(PyByteArray_AsString(data))
        elif PyBytes_Check(data):
            bytes_left = PyBytes_Size(data)
            self.lexer.set_data(PyBytes_AsString(data))
        else:
            raise Exception('Unable to extract bytes from unknown object type: {}'.format(data))

        while bytes_left > 0:
            self.lexer.next()
            if self.lexer.has_token():
                self.handle_token()
            bytes_left -= 1

    cdef void handle_token(self):
        cdef int token_type = self.lexer.token_type()

        if token_type == PRIORITY_TOKEN:
            set_priority(self.python_wrapper, self.lexer.get_token_as_string())
        elif token_type == VERSION_TOKEN:
            set_version(self.python_wrapper, self.lexer.get_token_as_string())
        elif token_type == TIMESTAMP_TOKEN:
            set_timestamp(self.python_wrapper, self.lexer.get_token_as_string())
        elif token_type == HOSTNAME_TOKEN:
            set_hostname(self.python_wrapper, self.lexer.get_token_as_string())
        elif token_type == APPNAME_TOKEN:
            set_appname(self.python_wrapper, self.lexer.get_token_as_string())
        elif token_type == PROCESSID_TOKEN:
            set_processid(self.python_wrapper, self.lexer.get_token_as_string())
        elif token_type == MESSAGEID_TOKEN:
            set_messageid(self.python_wrapper, self.lexer.get_token_as_string())
        elif token_type == SDE_NAME_TOKEN:
            self.sde_name = self.lexer.get_token_as_string()
            create_sd_element(self.python_wrapper, self.sde_name)
        elif token_type == SDE_FIELD_NAME_TOKEN:
            self.sde_field_name = self.lexer.get_token_as_string()
        elif token_type == SDE_FIELD_VALUE_TOKEN:
            add_sd_field(self.python_wrapper, self.sde_name, self.sde_field_name, self.lexer.get_token())
        elif token_type == MESSAGE_PART_TOKEN:
            if not self.message_head_passed:
                hand_off_message_head(self.python_wrapper)
                self.message_head_passed = True
            message_part(self.python_wrapper, self.lexer.get_token())
        elif token_type == LAST_MESSAGE_PART_TOKEN:
            if not self.message_head_passed:
                hand_off_message_head(self.python_wrapper)
            message_complete(self.python_wrapper, self.lexer.get_token())
            self.message_head_passed = False


cdef class SyslogLexer(object):

    cdef Py_ssize_t token_length, buffer_size
    cdef int buffered_octets, octets_left, token, data_index
    cdef char *token_buffer, *data_buffer
    cdef lexer_state current_state

    def __cinit__(self, int size_hint=RFC5424_MAX_BYTES):
        self.buffer_size = size_hint
        self.token_buffer = <char*> malloc(sizeof(char) * size_hint)
        self.reset()

    def __dealloc__(self):
        if self.token_buffer is not NULL:
            free(self.token_buffer)

    def reset(self):
        self._reset()

    def get_token_as_string(self):
        cdef object next_token
        # Export the token info
        next_token = PyUnicode_FromStringAndSize(self.token_buffer, self.token_length)
        # Reset the token info
        self.token_length = 0
        self.buffered_octets = 0
        # Return the token
        return next_token

    def get_token(self):
        cdef object next_token
        # Export the token info
        next_token = PyByteArray_FromStringAndSize(self.token_buffer, self.token_length)
        # Reset the token info
        self.token_length = 0
        self.buffered_octets = 0
        # Return the token
        return next_token

    cpdef set_data(self, char *data_buffer):
        self.data_buffer = data_buffer
        self.data_index = 0

    cpdef next(self):
        cdef char next_byte = self.data_buffer[self.data_index]
        if self.current_state == OCTET:
            self.read_octet(next_byte)
        else:
            self.next_msg_part(next_byte)
        self.data_index += 1

    cpdef int remaining(self):
        return self.octets_left

    cpdef int token_type(self):
        return self.token

    cpdef bool has_token(self):
        return self.token_length > 0

    cdef void _reset(self):
        self.current_state = OCTET
        self.buffered_octets = 0
        self.token_length = 0

    cdef void collect(self, char byte):
        self.token_buffer[self.buffered_octets] = byte
        self.buffered_octets += 1

    cdef void copy_into(self, char *dest):
        cdef int index = 0
        while index < self.buffered_octets:
            dest[index] = self.token_buffer[index]
            index += 1
        self.buffered_octets = 0

    cdef void buffer_token(self, int token_type):
        self.token = token_type
        self.token_length = self.buffered_octets

    cdef void next_msg_part(self, char next_byte):
        if self.current_state == PRIORITY_BEGIN:
            self.read_priority_start(next_byte)
        elif self.current_state == PRIORITY:
            self.read_token(next_byte,
                CLOSE_ANGLE_BRACKET, VERSION, PRIORITY_TOKEN)
        elif self.current_state == VERSION:
            self.read_token(next_byte,
                SPACE, TIMESTAMP, VERSION_TOKEN)
        elif self.current_state == TIMESTAMP:
            self.read_token(next_byte,
                SPACE, HOSTNAME, TIMESTAMP_TOKEN)
        elif self.current_state == HOSTNAME:
            self.read_token(next_byte,
                SPACE, APPNAME, HOSTNAME_TOKEN)
        elif self.current_state == APPNAME:
            self.read_token(next_byte,
                SPACE, PROCESSID, APPNAME_TOKEN)
        elif self.current_state == PROCESSID:
            self.read_token(next_byte,
                SPACE, MESSAGEID, PROCESSID_TOKEN)
        elif self.current_state == MESSAGEID:
            self.read_token(next_byte,
                SPACE, STRUCTURED_DATA_BEGIN, MESSAGEID_TOKEN)
        elif self.current_state == STRUCTURED_DATA_BEGIN:
            self.read_structured_data(next_byte)
        elif self.current_state == SD_ELEMENT_NAME:
            self.read_token(next_byte,
                SPACE, SD_FIELD_NAME, SDE_NAME_TOKEN)
        elif self.current_state == SD_FIELD_NAME:
            self.read_token(next_byte,
                EQUALS, SD_VALUE_BEGIN, SDE_FIELD_NAME_TOKEN)
        elif self.current_state == SD_VALUE_BEGIN:
            self.read_sd_value_start(next_byte)
        elif self.current_state == SD_VALUE_CONTENT:
            self.read_token(next_byte,
            QUOTE, SD_VALUE_END, SDE_FIELD_VALUE_TOKEN)
        elif self.current_state == SD_VALUE_END:
            self.read_sd_value_end(next_byte)
        elif self.current_state == STRUCTURED_DATA_END:
            self.read_sd_end(next_byte)
        elif self.current_state == MESSAGE:
            self.read_message(next_byte)
        self.octets_left -= 1

    cdef void read_octet(self, char next_byte):
        if next_byte == SPACE:
            self.parse_octet()
            self.current_state = PRIORITY_BEGIN
        else:
            self.collect(next_byte)

    cdef void parse_octet(self):
        cdef char *octet_buffer = <char*> malloc(
            sizeof(char) * self.buffered_octets)
        cdef int octets_read = self.buffered_octets + 1

        try:
            self.copy_into(octet_buffer)
            self.octets_left = atoi(octet_buffer)
        finally:
            free(octet_buffer)

    cdef void read_priority_start(self, char next_byte):
        if next_byte != OPEN_ANGLE_BRACKET:
            raise Exception('Expected <')
        self.current_state = PRIORITY

    cdef void read_token(self, char next_byte, char terminator,
            lexer_state next_state, int token_type):
        if next_byte == terminator:
            self.buffer_token(token_type)
            self.current_state = next_state
        else:
            self.collect(next_byte)

    cdef void read_structured_data(self, char next_byte):
        if next_byte == OPEN_BRACKET:
            self.current_state = SD_ELEMENT_NAME
        elif next_byte == DASH:
            self.current_state = STRUCTURED_DATA_END

    cdef void read_sd_value_start(self, char next_byte):
        if next_byte == QUOTE:
            self.current_state = SD_VALUE_CONTENT

    cdef void read_sd_value_end(self, char next_byte):
        if next_byte != SPACE:
            if next_byte == CLOSE_BRACKET:
                self.current_state = STRUCTURED_DATA_END
            else:
                self.collect(next_byte)
                self.current_state = SD_FIELD_NAME

    cdef void read_sd_end(self, char next_byte):
        if next_byte != SPACE:
            if next_byte == OPEN_BRACKET:
                self.current_state = SD_ELEMENT_NAME
            else:
                self.current_state = MESSAGE
                self.read_message(next_byte)

    cdef void read_message(self, char next_byte):
        cdef bool done_reading_message = (self.octets_left - 1 == 0)
        cdef bool buffer_full = (
            self.buffered_octets + 1 == self.buffer_size)
        self.collect(next_byte)
        if done_reading_message or buffer_full:
            if not done_reading_message:
                self.buffer_token(MESSAGE_PART_TOKEN)
            else:
                self.buffer_token(LAST_MESSAGE_PART_TOKEN)
                self.current_state = OCTET


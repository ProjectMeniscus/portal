from libc.stdlib cimport realloc, malloc, free, atoi
from libc.string cimport memset
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
    ls_begin
    ls_octet_count
    ls_priority_begin
    ls_priority
    ls_version
    ls_timestamp
    ls_hostname
    ls_appname
    ls_processid
    ls_messageid
    ls_sd_begin
    ls_sd_element_name
    ls_sd_field_name
    ls_sd_value_begin
    ls_sd_value_content
    ls_sd_value_end
    ls_sd_end
    ls_message


# Token constants
cdef int tc_none = 0
cdef int tc_priority = 1
cdef int tc_version = 2
cdef int tc_timestamp = 3
cdef int tc_hostname = 4
cdef int tc_appname = 5
cdef int tc_processid = 6
cdef int tc_messageid = 7
cdef int tc_sd_name = 8
cdef int tc_sd_field_name = 9
cdef int tc_sd_field_value = 10
cdef int tc_message_part = 11
cdef int tc_last_message_part = 12
cdef int tc_new_msg = 13


# Error constants
cdef int ec_none = 0
cdef int ec_out_of_octets = 1
cdef int ec_integer_overflow = 2
cdef int ec_octet_part_nan = 3


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


# Helper functions
cdef inline bool is_number(char b):
    return b > 47 and b < 58


cdef inline int base10_add(int original, char b):
    cdef int c = original
    c *= 10
    c += b - 48

    if c < original:
        return -1
    else:
        return c


def hand_off_message_head(delegate, message_head):
    try:
        delegate.message_head(message_head)
    except Exception as ex:
        raise MessageHandlerError('Error during message head handoff.', ex)


def hand_off_message_part(delegate, message_part):
    try:
        delegate.message_part(message_part)
    except Exception as ex:
        raise MessageHandlerError('Error during message part handoff.', ex)


def hand_off_message_end(delegate, message_part):
    try:
        delegate.message_complete(message_part)
    except Exception as ex:
        raise MessageHandlerError('Error during message completion.', ex)


def raise_exception(int error_type):
    if error_type == ec_out_of_octets:
        raise ParsingError(
            'Message out of octets to read but lexer '
            'is in an invalid state for ending a message.')
    elif error_type == ec_integer_overflow:
        raise ParsingError('Octet count too large.')
    elif error_type == ec_octet_part_nan:
        raise ParsingError('Octet count character not a number.')


class SyslogError(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class UnknownTypeError(SyslogError):

    def __init__(self, msg):
        super(UnknownTypeError, self).__init__(msg)


class ParsingError(SyslogError):

    def __init__(self, msg):
        super(ParsingError, self).__init__(msg)


class MessageHandlerError(SyslogError):

    def __init__(self, msg, cause):
        super(MessageHandlerError, self).__init__(msg)
        self.cause = cause

    def __str__(self):
        return 'MessageHandler exception: {} - {}'.format(
            self.msg, self.cause)


class SyslogMessageHandler(object):

    def message_head(self, message_head):
        pass

    def message_part(self, message_part):
        pass

    def message_complete(self, message_part):
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

    def set_sd_field(self, sd_fieldname):
        self.current_sd_field = sd_fieldname

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


class Parser(object):

    def __init__(self, msg_delegate):
        self.cparser = SyslogParser(msg_delegate)

    def read(self, bytearray):
        self.cparser.read(bytearray)

    def reset(self):
        self.cparser.reset()


cdef class SyslogParser(object):

    cdef object syslog_msg, msg_delegate
    cdef bool head_handed_off
    cdef SyslogLexer lexer

    def __cinit__(self):
        self.lexer = SyslogLexer(RFC5424_MAX_BYTES)

    def __init__(self, object msg_delegate):
        self.msg_delegate = msg_delegate
        self.syslog_msg = SyslogMessageHead()

    def _lexer(self):
        return self.lexer

    def reset(self):
        self.lexer.reset()
        self.syslog_msg.reset()

    cpdef read(self, object data):
        cdef int datalen, index = 0
        cdef char* cdata

        if PyByteArray_Check(data):
            datalen = PyByteArray_Size(data)
            cdata = PyByteArray_AsString(data)
        elif PyBytes_Check(data):
            datalen = PyBytes_Size(data)
            cdata = PyBytes_AsString(data)
        else:
            raise UnknownTypeError(
                'Unable to extract bytes from type: {}'.format(type(data)))

        while index < datalen:
            self.lexer.next(cdata[index])
            if self.lexer.has_error():
                try:
                    raise_exception(self.lexer.error_type())
                finally:
                    self.lexer.reset()
            if self.lexer.has_token():
                self.handle_token()
            index += 1

    cdef void handle_token(self):
        cdef int token_type = self.lexer.token_type()

        if token_type == tc_new_msg:
            self.head_handed_off = False
        if token_type == tc_priority:
            self.syslog_msg.priority = self.lexer.get_token_as_string()
        elif token_type == tc_version:
            self.syslog_msg.version = self.lexer.get_token_as_string()
        elif token_type == tc_timestamp:
            self.syslog_msg.timestamp = self.lexer.get_token_as_string()
        elif token_type == tc_hostname:
            self.syslog_msg.hostname = self.lexer.get_token_as_string()
        elif token_type == tc_appname:
            self.syslog_msg.appname = self.lexer.get_token_as_string()
        elif token_type == tc_processid:
            self.syslog_msg.processid = self.lexer.get_token_as_string()
        elif token_type == tc_messageid:
            self.syslog_msg.messageid = self.lexer.get_token_as_string()
        elif token_type == tc_sd_name:
            self.syslog_msg.create_sde(self.lexer.get_token_as_string())
        elif token_type == tc_sd_field_name:
            self.syslog_msg.set_sd_field(self.lexer.get_token_as_string())
        elif token_type == tc_sd_field_value:
            self.syslog_msg.set_sd_value(self.lexer.get_token())
        elif token_type == tc_message_part:
            self.handoff_head()
            hand_off_message_part(self.msg_delegate, self.lexer.get_token())
        elif token_type == tc_last_message_part:
            self.handoff_head()
            hand_off_message_end(self.msg_delegate, self.lexer.get_token())

    cdef void handoff_head(self):
        if not self.head_handed_off:
            hand_off_message_head(self.msg_delegate, self.syslog_msg)
            self.head_handed_off = True


cdef class SyslogLexer(object):

    cdef Py_ssize_t buffer_size, octets_buffered, octets_remaining
    cdef lexer_state state
    cdef char *char_buff
    cdef int token, error

    def __cinit__(self, int size_hint):
        self.buffer_size = size_hint
        self.char_buff = <char*> malloc(sizeof(char) * size_hint)
        self.reset()

    def __dealloc__(self):
        if self.char_buff is not NULL:
            free(self.char_buff)

    cpdef int remaining(self):
        return self.octets_remaining

    cdef get_token_as_string(self):
        cdef object next_token  = PyUnicode_FromStringAndSize(
            self.char_buff, self.octets_buffered)
        self.token = tc_none
        self.octets_buffered = 0
        # Return the token
        return next_token

    cdef get_token(self):
        cdef object next_token = PyByteArray_FromStringAndSize(
            self.char_buff, self.octets_buffered)
        self.token = tc_none
        self.octets_buffered = 0
        # Return the token
        return next_token

    cdef int get_error(self):
        return self.error

    cdef bool has_error(self):
        return self.error != ec_none

    cdef int token_type(self):
        return self.token

    cdef bool has_token(self):
        return self.token != tc_none

    cdef void reset(self):
        self.state = ls_begin
        self.octets_remaining = 0
        self.error = ec_none
        self.token = tc_none
        self.octets_buffered = 0

    cdef void collect(self, char b):
        self.char_buff[self.octets_buffered] = b
        self.octets_buffered += 1

    cdef void next(self, char b):
        if self.state != ls_begin and self.state != ls_octet_count:
            self.octets_remaining -= 1
            if self.octets_remaining < 0:
                self.error = ec_out_of_octets
                return
        self._next(b)

    cdef void _next(self, char b):
        if self.state == ls_begin:
            self.begin(b)
        elif self.state == ls_octet_count:
            self.read_octet_count(b)
        elif self.state == ls_priority_begin:
            self.read_priority_begin(b)
        elif self.state == ls_priority:
            self.read_until(b, CLOSE_ANGLE_BRACKET, ls_version, tc_priority)
        elif self.state == ls_version:
            self.read_until(b, SPACE, ls_timestamp, tc_version)
        elif self.state == ls_timestamp:
            self.read_until(b, SPACE, ls_hostname, tc_timestamp)
        elif self.state == ls_hostname:
            self.read_until(b, SPACE, ls_appname, tc_hostname)
        elif self.state == ls_appname:
            self.read_until(b, SPACE, ls_processid, tc_appname)
        elif self.state == ls_processid:
            self.read_until(b, SPACE, ls_messageid, tc_processid)
        elif self.state == ls_messageid:
            self.read_until(b, SPACE, ls_sd_begin, tc_messageid)
        elif self.state == ls_sd_begin:
            self.read_structured_data(b)
        elif self.state == ls_sd_element_name:
            self.read_until(b, SPACE, ls_sd_field_name, tc_sd_name)
        elif self.state == ls_sd_field_name:
            self.read_until(b, EQUALS, ls_sd_value_begin, tc_sd_field_name)
        elif self.state == ls_sd_value_begin:
            self.read_sd_value_begin(b)
        elif self.state == ls_sd_value_content:
            self.read_until(b, QUOTE, ls_sd_value_end, tc_sd_field_value)
        elif self.state == ls_sd_value_end:
            self.read_sd_value_end(b)
        elif self.state == ls_sd_end:
            self.read_sd_end(b)
        elif self.state == ls_message:
            self.read_message(b)

    cdef void read_until(self, char b, char terminator,
            lexer_state next_state, int token_type):
        if b != terminator:
            self.collect(b)
        else:
            self.state = next_state
            self.token = token_type

    cdef void begin(self, char b):
        self.token = tc_new_msg

        if is_number(b):
            self.state = ls_octet_count
            self.read_octet_count(b)
        else:
            self.state = ls_priority_begin
            self.read_priority_begin(b)

    cdef void parse_into_octet_count(self, char b):
        cdef int next_count = base10_add(self.octets_remaining, b)

        if next_count < self.octets_remaining:
            self.error = ec_integer_overflow
        else:
            self.octets_remaining = next_count

    cdef void read_octet_count(self, char b):
        if b != SPACE:
            if is_number(b):
                self.parse_into_octet_count(b)
            else:
                self.error = ec_octet_part_nan
        else:
            self.state = ls_priority_begin

    cdef void read_priority_begin(self, char b):
        if b == OPEN_ANGLE_BRACKET:
            self.state = ls_priority

    cdef void read_structured_data(self, char b):
        if b == OPEN_BRACKET:
            self.state = ls_sd_element_name
        elif b == DASH:
            self.state = ls_message

    cdef void read_sd_value_begin(self, char b):
        if b == QUOTE:
            self.state = ls_sd_value_content

    cdef void read_sd_value_end(self, char b):
        if b == CLOSE_BRACKET:
            self.state = ls_sd_end
        else:
            self.collect(b)
            self.state = ls_sd_field_name

    cdef void read_sd_end(self, char b):
        if b == OPEN_BRACKET:
            self.state = ls_sd_element_name
        else:
            self.state = ls_message
            self.read_message(b)

    cdef void read_message(self, char b):
        self.collect(b)
        if self.octets_remaining == 0:
            # Done reading message
            self.token = tc_last_message_part
            self.state = ls_begin
        elif self.octets_buffered + 1 == self.buffer_size:
            # Buffer full, transmit chunk
            self.token = tc_message_part


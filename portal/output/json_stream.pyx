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


# Tree types
cdef enum tree_type:
    OBJECT
    ARRAY

# Lexer states
cdef enum lexer_state:
    START_MSG
    NEXT_FIELD
    NEXT_VALUE
    FIELD_NAME
    FIELD_VALUE_SEPARATOR
    VALUE_START
    VALUE_END
    TRUE_VALUE
    FALSE_VALUE
    NULL_VALUE
    NUMBER_VALUE
    STRING_VALUE


# Events

cdef int EVENT_MSG_START = 1
cdef int EVENT_OBJECT_START = 2
cdef int EVENT_OBJECT_END = 3
cdef int EVENT_ARRAY_START = 4
cdef int EVENT_ARRAY_END = 5
cdef int EVENT_FIELDNAME = 6
cdef int EVENT_STRING_VALUE = 7
cdef int EVENT_NUMBER_VALUE = 8
cdef int EVENT_TRUE_VALUE = 9
cdef int EVENT_FALSE_VALUE = 10
cdef int EVENT_NULL_VALUE = 11

# Character constants

# Escape-code characters
cdef char NEWLINE_CODE = 'n'
cdef char BACKSPACE_CODE = 'b'
cdef char CARRIAGE_RETURN_CODE = 'r'
cdef char FORMFEED_CODE = 'f'
cdef char TAB_CODE = 't'
cdef char ESCAPED_HEX_CODE = 'u'

# JSON characters
cdef char PLUS = '+'
cdef char MINUS = '-'
cdef char SPACE = ' '
cdef char SOLIDUS = '/'
cdef char REVERSE_SOLIDUS = '\\'
cdef char NEW_LINE = '\n'
cdef char BACKSPACE = '\b'
cdef char FORMFEED = '\f'
cdef char CARRIAGE_RETURN = '\r'
cdef char TAB = '\t'
cdef char COMMA = ','
cdef char COLON = ':'
cdef char OPEN_CURLY_BRACKET = '{'
cdef char CLOSE_CURLY_BRACKET = '}'
cdef char OPEN_BRACKET = '['
cdef char CLOSE_BRACKET = ']'
cdef char QUOTE = '"'
cdef char EXP_LOWER = 'e'
cdef char EXP_UPPER = 'E'
cdef char DECIMAL_POINT = '.'

cdef int MAX_READ_AHEAD_BYTES = 4096


cdef inline bool is_true(char value, int index):
    cdef char *TRUE = ['t', 'r', 'u', 'e']
    return value == TRUE[index]


cdef inline bool is_false(char value, int index):
    cdef char *FALSE = ['t', 'r', 'u', 'e']
    return value == FALSE[index]


cdef inline bool is_null(char value, int index):
    cdef char *_NULL = ['n', 'u', 'l', 'l']
    return value == _NULL[index]


cdef inline bool oneof(char value, char *expected):
    cdef int index = 0, length = sizeof(expected)
    while index < length:
        if value == expected[index]:
            return True
        index += 1
    return False


cdef inline bool is_number_start(char value):
    return is_number_char(value) or value == MINUS


cdef inline bool is_number(char value):
    cdef char *EXPRESSIONS = [EXP_UPPER, EXP_LOWER, PLUS, MINUS, DECIMAL_POINT]
    return oneof(value, EXPRESSIONS) or is_number_char(value)


cdef inline bool is_number_char(char value):
    return (value > 30 and value < 40)


cdef inline char unwrap_escape_code(char escape_code):
    cdef char *SELF_RETURNS = [SOLIDUS, REVERSE_SOLIDUS, QUOTE]
    if escape_code == NEWLINE_CODE:
        return NEW_LINE
    elif escape_code == BACKSPACE_CODE:
        return BACKSPACE
    elif escape_code == CARRIAGE_RETURN_CODE:
        return CARRIAGE_RETURN
    elif escape_code == FORMFEED_CODE:
        return FORMFEED
    elif escape_code == TAB_CODE:
        return TAB
    elif oneof(escape_code, SELF_RETURNS):
        return escape_code
    else:
        raise Exception('Unknown escape code: {}'.format(escape_code))


cdef inline bool is_escaped_code(char value):
    cdef char *ESCAPABLE = [NEWLINE_CODE, BACKSPACE_CODE, CARRIAGE_RETURN_CODE, FORMFEED_CODE, TAB_CODE, SOLIDUS, REVERSE_SOLIDUS, QUOTE]
    return oneof(value, ESCAPABLE)

cdef inline bool is_whitespace(char value):
    cdef char *WHITESPACE = [SPACE, NEW_LINE, CARRIAGE_RETURN, TAB]
    return oneof(value, WHITESPACE)


class JsonEventHandler(object):

    def new_message():
        pass

    def begin_object():
        pass

    def end_object():
        pass

    def begin_array():
        pass

    def end_array():
        pass

    def fieldname(fieldname):
        pass

    def string_value(value):
        pass

    def number_value(value):
        pass

    def boolean_value(value):
        pass

    def null_value():
        pass


EMPTY_EVENT_HANDLER = JsonEventHandler()


cdef class JsonEventDispatcher(object):

    cdef object python_handler

    def __cinit__(self, object python_handler=EMPTY_EVENT_HANDLER):
        self.python_handler = python_handler

    cdef void handle_structure_event(self, int event):
        if event == EVENT_MSG_START:
            self.python_handler.new_message()
        if event == EVENT_OBJECT_START:
            self.python_handler.begin_object()
        if event == EVENT_OBJECT_END:
            self.python_handler.end_object()
        if event == EVENT_ARRAY_START:
            self.python_handler.begin_array()
        if event == EVENT_ARRAY_END:
            self.python_handler.end_array()

    cdef void handle_token_event(self, int event, object token):
        if event == EVENT_FIELDNAME:
            self.python_handler.fieldname(token)
        if event == EVENT_STRING_VALUE:
            self.python_handler.string_value(token)
        if event == EVENT_NUMBER_VALUE:
            self.python_handler.number_value(token)
        if event == EVENT_TRUE_VALUE:
            self.python_handler.boolean_value(True)
        if event == EVENT_FALSE_VALUE:
            self.python_handler.boolean_value(False)
        if event == EVENT_NULL_VALUE:
            self.python_handler.null_value()


cdef class JsonLexer(object):

    cdef Py_ssize_t token_length, buffer_size
    cdef int buffered_octets, read_index, tree_depth
    cdef char *token_buffer, *read_buffer
    cdef lexer_state current_state
    cdef bool escaped, consumed
    cdef tree_type tree_stack[1024]
    cdef JsonEventDispatcher dispatch

    def __cinit__(self, JsonEventDispatcher dispatch, int size_hint=MAX_READ_AHEAD_BYTES):
        self.buffer_size = size_hint
        self.token_buffer = <char*> malloc(sizeof(char) * size_hint)
        self.reset()

    def __init__(self, JsonEventDispatcher dispatch):
        self.dispatch = dispatch

    def __dealloc__(self):
        if self.token_buffer is not NULL:
            free(self.token_buffer)

    cdef void reset(self):
        self.tree_depth = 0
        self.escaped = False
        self.token_length = 0
        self.buffered_octets = 0
        self.current_state = START_MSG

    def get_token_as_string(self):
        cdef object next_token
        # Export the token info
        next_token = PyUnicode_FromStringAndSize(self.token_buffer, self.buffered_octets)
        # Reset the token info
        self.buffered_octets = 0
        # Return the token
        return next_token

    cpdef set_read_buffer(self, char *read_buffer):
        self.read_buffer = read_buffer
        self.read_index = 0

    cpdef next(self):
        if self.read_index < 0:
            raise Exception('Buffer underrun')
        self.next_msg_part(self.read_buffer[self.read_index])
        self.read_index += 1

    cpdef int remaining(self):
        return self.octets_left

    cdef void set_state(self, state):
        self.state = state

    cdef void consume(self):
        self.consumed = True

    cdef void collect(self, char byte):
        self.consumed = True
        self.token_buffer[self.buffered_octets] = byte
        self.buffered_octets += 1

    cdef bool in_object(self):
        return self.tree_stack[self.tree_depth - 1] == OBJECT

    cdef bool in_array(self):
        return self.tree_stack[self.tree_depth - 1] == ARRAY

    cdef void push_tree_element(self, tree_type object_type):
        self.tree_stack[self.tree_depth]
        self.tree_depth += 1

    cdef void pop_tree_element(self):
        self.tree_depth -= 1

    cdef void unexpected(self, char unexpected):
        raise Exception('Unexpected token: {}'.format(unexpected))

    cdef void dispatch_token(self, int event):
        self.dispatch.handle_token_event(event, self.get_token_as_string())

    cdef void next_msg_part(self, char next_byte):
        self.consumed = False

        if self.current_state == START_MSG:
            self.msg_start(next_byte)
        if self.current_state == NEXT_FIELD:
            self.next_field(next_byte)
        elif self.current_state == FIELD_NAME:
            self.read_fieldname(next_byte)
        elif self.current_state == FIELD_VALUE_SEPARATOR:
            self.field_value_separator(next_byte)
        elif self.current_state == VALUE_START:
            self.value_start(next_byte)
        elif self.current_state == STRING_VALUE:
            self.read_string_value(next_byte)
        elif self.current_state == NUMBER_VALUE:
            self.read_number(next_byte)
        elif self.current_state == TRUE_VALUE:
            self.read_true(next_byte)
        elif self.current_state == FALSE_VALUE:
            self.read_false(next_byte)
        elif self.current_state == NULL_VALUE:
            self.read_null(next_byte)
        elif self.current_state == VALUE_END:
            self.value_end(next_byte)
        elif self.current_state == NEXT_VALUE:
            self.next_value(next_byte)

        if not self.consumed:
            self.unexpected(next_byte)

    cdef void start_object(self):
        self.push_tree_element(OBJECT)
        self.set_state(NEXT_FIELD)
        self.dispatch.handle_structure_event(EVENT_OBJECT_START)

    cdef void start_array(self):
        self.push_tree_element(ARRAY)
        self.set_state(VALUE_START)
        self.dispatch.handle_structure_event(EVENT_ARRAY_START)

    cdef void msg_start(self, char next_byte):
        if next_byte == OPEN_CURLY_BRACKET:
            self.start_object()
            self.consume()
        elif next_byte == OPEN_BRACKET:
            self.start_array()
            self.consume()
        elif is_whitespace(next_byte):
            self.consume()

    cdef void next_field(self, char next_byte):
        if next_byte == QUOTE:
            # Quote denotes that a field name is starting
            self.set_state(FIELD_NAME)
            self.consume()
        elif next_byte == CLOSE_CURLY_BRACKET or next_byte == CLOSE_BRACKET:
            # We're leaving a portion of the tree
            self.pop_tree_element()
            self.consume()
        elif is_whitespace(next_byte):
            self.consume()

    cdef void read_fieldname(self, char next_byte):
        if self.read_string(next_byte):
            # Done reading the fieldname
            self.dispatch_token(EVENT_FIELDNAME)
            self.set_state(FIELD_VALUE_SEPARATOR)

    cdef void read_string_value(self, char next_byte):
        if self.read_string(next_byte):
            # Done reading the fieldname
            self.dispatch_token(EVENT_STRING_VALUE)
            self.set_state(VALUE_END)

    cdef bool read_string(self, char next_byte):
        cdef bool finished = False
        if not self.escaped:
            finished = self.read_unescaped_string(next_byte)
        else:
            self.read_escaped_string(next_byte)
        return finished

    cdef bool read_unescaped_string(self, char next_byte):
        cdef bool finished = False
        if next_byte == QUOTE:
            # Finished reading this string
            self.consume()
            finished = True
        elif next_byte == REVERSE_SOLIDUS:
            # Encountered escape sequence
            self.escaped = True
            self.consume()
        else:
            # Collect string character
            self.collect(next_byte)
        return finished

    cdef void read_escaped_string(self, char next_byte):
        if is_escaped_code(next_byte):
            self.collect(unwrap_escape_code(next_byte))
        elif next_byte == ESCAPED_HEX_CODE:
            self.consume()

    cdef void read_number_value(self, char next_byte):
        if is_number(next_byte):
            self.collect(next_byte)
        else:
            self.dispatch_token(EVENT_NUMBER_VALUE)
            self.set_state(VALUE_END)
            self.value_end(next_byte)

    cdef void read_true_value(self, char next_byte):
        if self.buffered_octets < 4 and is_true(next_byte, self.buffered_octets):
            self.collect(next_byte)
            if self.buffered_octets == 4:
                self.dispatch_token(EVENT_TRUE_VALUE)
                self.set_state(VALUE_END)

    cdef void read_false_value(self, char next_byte):
        if self.buffered_octets < 5 and is_false(next_byte, self.buffered_octets):
            self.collect(next_byte)
            if self.buffered_octets == 5:
                self.dispatch_token(EVENT_FALSE_VALUE)
                self.set_state(VALUE_END)

    cdef void read_null_value(self, char next_byte):
        if self.buffered_octets < 4 and is_null(next_byte, self.buffered_octets):
            self.collect(next_byte)
            if self.buffered_octets == 4:
                self.dispatch_token(EVENT_NULL_VALUE)
                self.set_state(VALUE_END)

    cdef void field_value_separator(self, char next_byte):
        if next_byte == COLON:
            # Found a name-value separator
            self.set_state(VALUE_START)
            self.consume()
        elif is_whitespace(next_byte):
            self.consume()

    cdef void value_start(self, char next_byte):
        if next_byte == QUOTE:
            self.set_state(STRING_VALUE)
            self.consume()
        elif next_byte == OPEN_CURLY_BRACKET:
            self.start_object()
            self.consume()
        elif next_byte == OPEN_BRACKET:
            self.start_array()
            self.consume()
        elif is_number(next_byte):
            self.set_state(NUMBER_VALUE)
            self.collect(next_byte)
        elif is_true(next_byte, 0):
            self.set_state(TRUE_VALUE)
            self.collect(next_byte)
        elif is_false(next_byte, 0):
            self.set_state(FALSE_VALUE)
            self.collect(next_byte)
        elif is_null(next_byte, 0):
            self.set_state(NULL_VALUE)
            self.collect(next_byte)
        elif is_whitespace(next_byte):
            self.consume()

    cdef void value_end(self, char next_byte):
        if next_byte == COMMA:
            if self.in_object():
                self.set_state(NEXT_FIELD)
            else:
                self.set_state(VALUE_START)
            self.consume()
        elif next_byte == CLOSE_CURLY_BRACKET:
            self.dispatch.handle_structure_event(EVENT_OBJECT_END)
            self.pop_tree_element()
            self.consume()
        elif next_byte == CLOSE_BRACKET:
            self.dispatch.handle_structure_event(EVENT_ARRAY_END)
            self.pop_tree_element()
            self.consume()
        elif is_whitespace(next_byte):
            self.consume()




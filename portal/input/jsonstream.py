
from  portal.input.jsonep import JsonEventHandler, JsonEventParser


class JsonMessageHandler(object):

    def header(self, key, value):
        pass

    def body(self, body):
        pass


MESSAGE_ROOT = 1


class JsonMessageAssembler(JsonEventHandler):

    def __init__(self, message_handler):
        self.message_handler = message_handler
        self.tree_depth = 0
        self.object_stack = list()
        self.component_name = None
        self.reading_headers = True
        self.current_field = None
        self.current_object = None
        self.string_buffer = ''

    def _pop_tree(self):
        finished = self.object_stack.pop()
        if self.object_stack:
            self.current_object = self.object_stack[-1]
        if self._in_message_root():
            self._hand_off(finished)

    def _assign(self, tree_object):
        if self.current_field is not None:
            self.current_object[self.current_field] = tree_object
            self.current_field = None
        else:
            self.current_object.append(tree_object)

    def _in_message_root(self):
        return len(self.object_stack) == MESSAGE_ROOT

    def _hand_off(self, message):
        if self.reading_headers:
            self.message_handler.header(self.component_name, message)
        else:
            self.message_handler.body(message)

    def begin_object(self):
        tree_object = dict()
        if self.object_stack:
            self._assign(tree_object)
        else:
            self.reading_headers = True
        self.object_stack.append(tree_object)
        self.current_object = tree_object

    def end_object(self):
        self._pop_tree()

    def begin_array(self):
        tree_object = list()
        if self.object_stack:
            self._assign(tree_object)
        else:
            raise Exception('A JSON stream message may not begin with an array.')
        self.object_stack.append(tree_object)
        self.current_object = tree_object

    def end_array(self):
        self._pop_tree()

    def fieldname(self, name):
        if self._in_message_root():
            if name == 'body':
                self.reading_headers = False
            self.component_name = name
        self.current_field = name

    def string_value_part(self, string):
        self.string_buffer += string

    def string_value_end(self, string):
        self.string_value_part(string)
        self._assign(self.string_buffer)
        self.string_buffer = ''

    def number_value(self, value):
        self._assign(value)

    def boolean_value(self, value):
        self._assign(value)

    def null_value(self):
        self._assign(None)


import simplejson as json


class ObjectJsonWriter(object):

    def __init__(self):
        pass

    def _build_msg(self, headers, body):
        msg = '{'
        for key in headers:
            msg += '"{}": {},'.format(key, json.dumps(headers[key]))
        msg += '"body": {}'.format(json.dumps(body)) + '}'
        return msg

    def write(self, headers, body, socket):
        msg = self._build_msg(headers, body)
        length = len(msg)
        sent = 0
        while sent < length:
            sent += socket.send(msg[sent:])

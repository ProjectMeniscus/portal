from libc.stdint cimport *

cdef extern from "cstr.h":

    ctypedef struct cstr:
        char *bytes
        size_t size

    ctypedef struct cstr_buff:
        cstr *data
        size_t position


cdef extern from "syslog.h":

    cdef struct syslog_msg_head:
        uint16_t priority
        uint16_t version

        cstr *timestamp
        cstr *hostname
        cstr *appname
        cstr *processid
        cstr *messageid

    cdef struct syslog_parser:
        syslog_msg_head *msg_head
        size_t message_length
        void *app_data

    ctypedef int (*syslog_cb) (syslog_parser *parser)
    ctypedef int (*syslog_data_cb) (syslog_parser *parser, char *data, size_t len)

    struct syslog_parser_settings:
        syslog_cb         on_msg_begin
        syslog_data_cb    on_sd_element
        syslog_data_cb    on_sd_field
        syslog_data_cb    on_sd_value
        syslog_cb         on_msg_head_complete
        syslog_data_cb    on_msg_part
        syslog_cb         on_msg_complete

    void uslg_parser_reset(syslog_parser *parser)
    void uslg_free_parser(syslog_parser *parser)

    int uslg_parser_init(syslog_parser *parser, void *app_data)
    int uslg_parser_exec(syslog_parser *parser, syslog_parser_settings *settings, char *data, size_t length)

    char * uslg_error_string(int error)

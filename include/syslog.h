#ifndef syslog_h
#define syslog_h

#ifdef __cplusplus
extern "C" {
#endif

#include "cstr.h"
#include <stdint.h>
#include <sys/types.h>


// Typedefs
typedef struct syslog_parser syslog_parser;
typedef struct syslog_msg_head syslog_msg_head;
typedef struct syslog_parser_settings syslog_parser_settings;

typedef int (*syslog_cb) (syslog_parser *parser);
typedef int (*syslog_data_cb) (syslog_parser *parser, const char *data, size_t len);


// Enumerations
enum flags {
    F_RFC_3164       = 1 << 0,
    F_RFC_5424       = 1 << 1,
    F_ESCAPED        = 1 << 2,
    F_COUNT_OCTETS   = 1 << 3
};


enum USYSLOG_ERROR {
    SLERR_UNCAUGHT = 1,
    SLERR_BAD_OCTET_COUNT = 2,
    SLERR_BAD_PRIORITY_START = 3,
    SLERR_BAD_PRIORITY = 4,
    SLERR_BAD_VERSION = 5,
    SLERR_BAD_SD_START = 6,
    SLERR_BAD_SD_FIELD = 7,
    SLERR_BAD_SD_VALUE = 8,
    SLERR_PREMATURE_MSG_END = 9,

    SLERR_BAD_STATE = 100,
    SLERR_USER_ERROR = 101,

    SLERR_BUFFER_OVERFLOW = CSTR_BUFFER_OVERFLOW,
    SLERR_UNABLE_TO_ALLOCATE = 201
};


// Structs
struct syslog_msg_head {
    // Numeric Fields
    uint16_t priority;
    uint16_t version;

    cstr *timestamp;
    cstr *hostname;
    cstr *appname;
    cstr *processid;
    cstr *messageid;
};

struct syslog_parser_settings {
    syslog_cb         on_msg_begin;
    syslog_data_cb    on_sd_element;
    syslog_data_cb    on_sd_field;
    syslog_data_cb    on_sd_value;
    syslog_cb         on_msg_head_complete;
    syslog_data_cb    on_msg_part;
    syslog_cb         on_msg_complete;
};

struct syslog_parser {
    // Parser fields
    unsigned char flags : 4;
    unsigned char token_state;
    unsigned char state;

    // Errors
    unsigned char error;

    // Message head
    struct syslog_msg_head *msg_head;

    // Byte tracking fields
    size_t message_length;
    size_t octets_remaining;
    size_t octets_read;

    // Buffer
    cstr_buff *buffer;

    // Optionally settable application data pointer
    void *app_data;
};

// Functions
void uslg_parser_reset(syslog_parser *parser);
void uslg_free_parser(syslog_parser *parser);

int uslg_parser_init(syslog_parser *parser, void *app_data);
int uslg_parser_exec(syslog_parser *parser, const syslog_parser_settings *settings, const char *data, size_t length);

char * uslg_error_string(int error);

#ifdef __cplusplus
}
#endif
#endif
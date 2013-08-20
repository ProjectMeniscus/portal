#include "usyslog.h"
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <limits.h>

// Macros
#define RFC3164_MAX_BYTES       1024
#define RFC5424_MAX_BYTES       2048
#define MAX_BUFFER_SIZE         (RFC5424_MAX_BYTES * 32)

#ifndef ULLONG_MAX
#   define ULLONG_MAX ((uint64_t) -1)   // 2^64-1
#endif

#define IS_WS(c)            (c ==' ' || c == '\t' || c == '\r' || c == '\n')

#define LOWER(c)            (unsigned char)(c | 0x20)
#define IS_ALPHA(c)         (LOWER(c) >= 'a' && LOWER(c) <= 'z')
#define IS_NUM(c)           ((c) >= '0' && (c) <= '9')
#define IS_ALPHANUM(c)      (IS_ALPHA(c) || IS_NUM(c))

#define IS_HOST_CHAR(c) (IS_ALPHANUM(c) || (c) == '.' || (c) == '-' || (c) == '_')


enum token_state {
    ts_before,
    ts_read
};

// States
enum syslog_state {

    // Message Head
    s_msg_start,
    s_octet_count,
    s_priority_start,
    s_priority,
    s_version,
    s_timestamp,
    s_hostname,
    s_appname,
    s_procid,
    s_msgid,

    // RFC5424 - SDATA
    s_sd_start,
    s_sd_element,
    s_sd_field,
    s_sd_value_begin,
    s_sd_value,
    s_sd_value_end,
    s_sd_end,

    // Message Content
    s_message,
    s_msg_complete
};

enum syslog_retval {
    rv_advance,
    rv_rehash,
    rv_error
};

typedef enum syslog_state syslog_state;
typedef enum syslog_retval syslog_retval;

// Supporting functions

pbuffer * init_pbuffer(size_t size) {
    pbuffer *buffer = (pbuffer *) malloc(sizeof(pbuffer));
    buffer->bytes = (char *) malloc(sizeof(char) * size);
    buffer->position = 0;
    buffer->size = size;

    return buffer;
}

void reset_pbuffer(pbuffer *buffer) {
    buffer->position = 0;
}

void free_pbuffer(pbuffer *buffer) {
    if (buffer->bytes != NULL) {
        free(buffer->bytes);
        buffer->bytes = NULL;
    }

    free(buffer);
}

int store_byte_in_pbuffer(char byte, pbuffer *dest) {
    int retval = 0;

    if (dest-> position + 1 < dest->size) {
        dest->bytes[dest->position] = byte;
        dest->position += 1;
    } else {
        retval = SLERR_BUFFER_OVERFLOW;
    }

    return retval;
}

int copy_into_pbuffer(const char *source, pbuffer *dest, size_t length) {
    int retval = 0;

    if (dest->position + length < dest->size) {
        memcpy(dest->bytes, source, length);
        dest->position += length;
    } else {
        retval = SLERR_BUFFER_OVERFLOW;
    }

    return retval;
}

char * copy_pbuffer(pbuffer *src) {
    char *new = (char *) malloc(src->position * sizeof(char));
    memcpy(new, src->bytes, src->position);

    return new;
}

char * copy_buffer(syslog_parser *parser) {
    return copy_pbuffer(parser->buffer);
}

void reset_buffer(syslog_parser *parser) {
    reset_pbuffer(parser->buffer);
}

int store_byte(char byte, syslog_parser *parser) {
    return store_byte_in_pbuffer(byte, parser->buffer);
}

int on_cb(syslog_parser *parser, syslog_cb cb) {
    return cb(parser);
}

int on_data_cb(syslog_parser *parser, syslog_data_cb cb) {
    return cb(parser, parser->buffer->bytes, parser->buffer->position);
}

void set_token_state(syslog_parser *parser, enum token_state next_state) {
    #if DEBUG_OUTPUT
    // Print the state switch if we're compiled in DEBUG mode
    printf("Setting token state to: %i", next_state);
    #endif

    parser->token_state = next_state;
}

void set_state(syslog_parser *parser, syslog_state next_state) {
    #if DEBUG_OUTPUT
    // Print the state switch if we're compiled in DEBUG mode
    printf("Setting state to: %i", next_state);
    #endif

    parser->state = next_state;
    set_token_state(parser, ts_before);
}

int set_error(syslog_parser *parser, int error) {
    parser->error = error;
    return rv_error;
}

int msgid(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    if (!IS_WS(nb)) {
        store_byte(nb, parser);
    } else {
        parser->msg_head->msg_id= copy_buffer(parser);
        reset_buffer(parser);

        set_state(parser, s_sd_element);
    }
}

int proc_id(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    if (!IS_WS(nb)) {
        store_byte(nb, parser);
    } else {
        parser->msg_head->proc_id = copy_buffer(parser);
        reset_buffer(parser);

        set_state(parser, s_msgid);
    }
}

int appname(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    if (!IS_WS(nb)) {
        store_byte(nb, parser);
    } else {
        parser->msg_head->appname= copy_buffer(parser);
        reset_buffer(parser);

        set_state(parser, s_procid);
    }
}

int hostname(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    if (!IS_WS(nb)) {
        store_byte(nb, parser);
    } else {
        parser->msg_head->hostname = copy_buffer(parser);
        reset_buffer(parser);

        set_state(parser, s_appname);
    }
}

int timestamp(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    if (!IS_WS(nb)) {
        store_byte(nb, parser);
    } else {
        parser->msg_head->timestamp = copy_buffer(parser);
        reset_buffer(parser);

        set_state(parser, s_hostname);
    }
}

int version(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    int retval = rv_advance;

    if (IS_NUM(nb)) {
        uint8_t nversion = parser->message_length;
        nversion*= 10;
        nversion += nb - '0';

        if (nversion < parser->msg_head->version|| nversion > 999) {
            retval = set_error(parser, SLERR_BAD_PRIORITY);
        } else {
            parser->msg_head->version = nversion;
        }
    } else {
        set_state(parser, s_timestamp);
    }
}

int priority(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    int retval = rv_advance;

    if (IS_NUM(nb)) {
        uint8_t npri = parser->message_length;
        npri *= 10;
        npri += nb - '0';

        if (npri < parser->msg_head->pri || npri > 999) {
            retval = set_error(parser, SLERR_BAD_PRIORITY);
        } else {
            parser->msg_head->pri = npri;
        }
    } else {
        switch (nb) {
            case '>':
                set_state(parser, s_version);
                break;

            default:
                retval = set_error(parser, SLERR_BAD_PRIORITY);
        }
    }
}

int priority_start(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    int retval = rv_advance;

    switch(nb) {
        case '<':
            set_state(parser, s_priority);
            break;

        default:
            retval = set_error(parser, SLERR_BAD_PRIORITY_START);
    }

    return retval;
}

int octet_count(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    int retval = rv_advance;

    if (IS_NUM(nb)) {
        uint64_t mlength = parser->message_length;
        mlength *= 10;
        mlength += nb - '0';

        if (mlength < parser->message_length || mlength == ULONG_MAX) {
            retval = set_error(parser, SLERR_BAD_OCTET_COUNT);
        } else {
            parser->message_length = mlength;
        }
    } else {
        set_state(parser, s_priority_start);
    }

    return retval;
}

int msg_start(syslog_parser *parser, const syslog_parser_settings *settings, const char next) {
    set_state(parser, s_octet_count);
    return rv_rehash;
}

// Big state switch
int uslg_parser_exec(syslog_parser *parser, const syslog_parser_settings *settings, const char *data, size_t length) {
    int retval = 0, d_index;

    for (d_index = 0; d_index < length; d_index++) {
        char next_byte = data[d_index];

        #if DEBUG_OUTPUT
        // Get the next character being processed during debug
        printf("Next byte: %c\n", next_byte);
        #endif

        if (parser->token_state == ts_before) {
            switch (next_byte) {
                case ' ':
                case '\t':
                    continue;

                default:
                    set_token_state(parser, ts_read);
            }
        }

        switch (parser->state) {
            case s_msg_start:
                break;
            case s_octet_count:
                break;
            case s_priority:
                break;
            case s_version:
                break;
            case s_timestamp:
                break;
            case s_hostname:
                break;
            case s_appname:
                break;
            case s_procid:
                break;
            case s_msgid:
                break;

            case s_sd_start:
                break;
            case s_sd_element:
                break;
            case s_sd_field:
                break;
            case s_sd_value_begin:
                break;
            case s_sd_value:
                break;
            case s_sd_value_end:
                break;
            case s_sd_end:
                break;

            case s_message:
                break;
            case s_msg_complete:
                break;

            default:
                retval = SLERR_BAD_STATE;
        }

        if (!retval && parser->state == s_msg_complete) {
            retval = on_cb(parser, settings->on_msg_complete);
            uslg_parser_reset(parser);
        }

        if (retval) {
            uslg_parser_reset(parser);
            break;
        }
    }

    return retval;
}


void uslg_parser_reset(syslog_parser *parser) {
}

void uslg_parser_init(syslog_parser *parser) {
    // Preserve app_data ref
    void *app_data = parser->app_data;

    // Clear the parser memory space
    memset(parser, 0, sizeof(*parser));

    // Set up the struct elements
    parser->app_data = app_data;
    parser->msg_head = (syslog_msg_head *) malloc(sizeof(syslog_msg_head));
    parser->buffer = init_pbuffer(MAX_BUFFER_SIZE);
    uslg_parser_reset(parser);
}

void uslg_free_parser(syslog_parser *parser) {
    free_pbuffer(parser->buffer);
    free(parser);
}
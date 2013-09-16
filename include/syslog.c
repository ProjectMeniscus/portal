#include "syslog.h"
#include "cstr.h"

#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <stdbool.h>
#include <errno.h>

// Macros
#define RFC3164_MAX_BYTES       1024
#define RFC5424_MAX_BYTES       2048
#define MAX_BUFFER_SIZE         (RFC5424_MAX_BYTES * 32)

#define IS_WS(c)            (c ==' ' || c == '\t' || c == '\r' || c == '\n')
#define LOWER(c)            (unsigned char)(c | 0x20)
#define IS_ALPHA(c)         (LOWER(c) >= 'a' && LOWER(c) <= 'z')
#define IS_NUM(c)           ((c) >= '0' && (c) <= '9')
#define IS_ALPHANUM(c)      (IS_ALPHA(c) || IS_NUM(c))


// Typedefs
typedef enum {
    ts_before,
    ts_read
} token_state;

typedef enum {
    // Message Head
    s_msg_start,
    s_octet_count,
    s_priority_start,
    s_priority,
    s_version,
    s_timestamp,
    s_hostname,
    s_appname,
    s_processid,
    s_messageid,

    // RFC5424 - SDATA
    s_sd_start,
    s_sd_element,
    s_sd_field_start,
    s_sd_field,
    s_sd_value_start,
    s_sd_value,
    s_sd_value_end,
    s_sd_end,

    // Message Content
    s_message
} syslog_state;

typedef enum {
    pa_advance,
    pa_rehash,
    pa_none
} parser_action;


// Supporting functions
void free_msg_head_fields(syslog_msg_head *head) {
    if (head->timestamp != NULL) {
        cstr_free(head->timestamp);
        head->timestamp = NULL;
    }

    if (head->hostname != NULL) {
        cstr_free(head->hostname);
        head->hostname = NULL;
    }

    if (head->appname != NULL) {
        cstr_free(head->appname);
        head->appname = NULL;
    }

    if (head->processid != NULL) {
        cstr_free(head->processid);
        head->processid = NULL;
    }

    if (head->messageid != NULL) {
        cstr_free(head->messageid);
        head->messageid = NULL;
    }
}

void reset_msg_head(syslog_msg_head *head) {
    free_msg_head_fields(head);

    head->priority = 0;
    head->version = 0;
}

void on_cb(syslog_parser *parser, syslog_cb cb) {
    const int error = cb(parser);

    if (error) {
        parser->error = SLERR_USER_ERROR;
    }
}

void on_data_cb(syslog_parser *parser, syslog_data_cb cb) {
    const int error = cb(parser, parser->buffer->data->bytes, parser->buffer->position);

    if (error) {
        parser->error = SLERR_USER_ERROR;
    }

    cstr_buff_reset(parser->buffer);
}

#if DEBUG_OUTPUT
char * get_state_name(syslog_state state) {
    switch (state) {
        case s_msg_start:
            return "msg_start";
        case s_octet_count:
            return "octet_count";
        case s_priority_start:
            return "priority_start";
        case s_priority:
            return "priority";
        case s_version:
            return "version";
        case s_timestamp:
            return "timestamp";
        case s_hostname:
            return "hostname";
        case s_appname:
            return "appname";
        case s_processid:
            return "processid";
        case s_messageid:
            return "messageid";
        case s_sd_start:
            return "sd_start";
        case s_sd_element:
            return "sd_element";
        case s_sd_field_start:
            return "sd_field_start";
        case s_sd_field:
            return "sd_field";
        case s_sd_value_start:
            return "sd_value_start";
        case s_sd_value:
            return "sd_value";
        case s_sd_end:
            return "sd_end";
        case s_message:
            return "message";

        default:
            return "NOT A STATE";
    }
}
#endif

void set_token_state(syslog_parser *parser, token_state next_state) {
// Print the state switch if we're compiled in DEBUG mode
#if DEBUG_OUTPUT
    printf("Setting token state to: %i\n", next_state);
#endif

    parser->token_state = next_state;
}

void set_state(syslog_parser *parser, syslog_state next_state) {
// Print the state switch if we're compiled in DEBUG mode
#if DEBUG_OUTPUT
    printf("Setting state to: %s\n", get_state_name(next_state));
#endif

    parser->state = next_state;
    set_token_state(parser, ts_before);
}

void set_str_field(syslog_parser *parser) {
    const cstr_buff *buffer = parser->buffer;

    cstr *value = cstr_copy_from_cstr(buffer->data, buffer->position);

    if (value == NULL) {
        parser->error = SLERR_UNABLE_TO_ALLOCATE;
    } else {
        switch (parser->state) {
            case s_timestamp:
                parser->msg_head->timestamp = value;
                break;

            case s_hostname:
                parser->msg_head->hostname = value;
                break;

            case s_appname:
                parser->msg_head->appname = value;
                break;

            case s_processid:
                parser->msg_head->processid = value;
                break;

            case s_messageid:
                parser->msg_head->messageid = value;
                break;

            default:
                cstr_free(value);
        }

        cstr_buff_reset(parser->buffer);
    }
}

/**
* Reads the message portion of a syslog message. This function returns an int
* value representing the number of bytes read from the buffer.
*/
int read_message(syslog_parser *parser, const syslog_parser_settings *settings, const char *data, size_t length) {
    bool msg_complete = false;
    int read;

    if (parser->flags & F_COUNT_OCTETS) {
        // If we're counting octets then the message ends when we run out of octsts
        read = parser->octets_remaining >= length ? length : parser->octets_remaining;
        parser->octets_remaining -= read;

        msg_complete = parser->octets_remaining == 0;
    } else {
        // If we're not counting octets then the \n character is EOF for the message
        for (read = 0; read < length; read++) {
            if (data[read] == '\n') {
                msg_complete = true;
                break;
            }
        }
    }

    if (read > 0) {
        // If we read something we need to pass it along
        const int error = settings->on_msg_part(parser, data, read);

        if (error) {
            parser->error = SLERR_USER_ERROR;
        }
    }

    if (!parser->error && msg_complete) {
        // If there was no error reported and the message is complete, pass it along
        on_cb(parser, settings->on_msg_complete);

        if (!parser->error) {
            // If there was no error, set the parser back to a blank slate
            uslg_parser_reset(parser);
        }
    }

    return read;
}

int sd_value(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    switch (nb) {
        case '\\':
            parser->flags |= F_ESCAPED;
            break;

        case '"':
            if (parser->flags & F_ESCAPED) {
                parser->flags |= F_ESCAPED;
            } else {
                on_data_cb(parser, settings->on_sd_value);
                set_state(parser, s_sd_field_start);
            }
            break;

        default:
            cstr_buff_put(parser->buffer, nb);
    }

    return pa_advance;
}

int sd_value_start(syslog_parser *parser, char nb) {
    switch (nb) {
        case '"':
            set_state(parser, s_sd_value);
            break;

        default:
            parser->error = SLERR_BAD_SD_VALUE;
    }

    return pa_advance;
}

int sd_field(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    switch (nb) {
        case '=':
            on_data_cb(parser, settings->on_sd_field);
            set_state(parser, s_sd_value_start);
            break;

        default:
            cstr_buff_put(parser->buffer, nb);
    }

    return pa_advance;
}

int sd_field_start(syslog_parser *parser, char nb) {
    if (IS_ALPHANUM(nb)) {
        cstr_buff_put(parser->buffer, nb);
        set_state(parser, s_sd_field);
    } else {
        switch (nb) {
            case ']':
                set_state(parser, s_sd_start);
                break;

            default:
                parser->error = SLERR_BAD_SD_FIELD;
        }
    }

    return pa_advance;
}

int sd_element(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    if (!IS_WS(nb)) {
        cstr_buff_put(parser->buffer, nb);
    } else {
        on_data_cb(parser, settings->on_sd_element);
        set_state(parser, s_sd_field_start);
    }

    return pa_advance;
}

int sd_start(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    int retval = pa_advance;

    switch (nb) {
        case '[':
            set_state(parser, s_sd_element);
            break;

        case '-':
            set_state(parser, s_message);
            on_cb(parser, settings->on_msg_head_complete);
            break;

        default:
            set_state(parser, s_message);
            on_cb(parser, settings->on_msg_head_complete);
            retval = pa_rehash;
    }

    return retval;
}

int parse_msg_head_part(syslog_parser *parser, syslog_state next_state, char nb) {
    if (!IS_WS(nb)) {
        cstr_buff_put(parser->buffer, nb);
    } else {
        set_str_field(parser);
        set_state(parser, next_state);
    }

    return pa_advance;
}

int version(syslog_parser *parser, char nb) {
    int retval = pa_advance;

    if (IS_NUM(nb)) {
        uint16_t nversion = parser->msg_head->version;
        nversion *= 10;
        nversion += nb - '0';

        if (nversion < parser->msg_head->version|| nversion > 999) {
            parser->error = SLERR_BAD_VERSION;
        } else {
            parser->msg_head->version = nversion;
        }
    } else {
        set_state(parser, s_timestamp);
    }

    return retval;
}

int priority(syslog_parser *parser, char nb) {
    if (IS_NUM(nb)) {
        uint16_t npriority = parser->msg_head->priority;
        npriority *= 10;
        npriority += nb - '0';

        if (npriority < parser->msg_head->priority || npriority > 999) {
            parser->error = SLERR_BAD_PRIORITY;
        } else {
            parser->msg_head->priority = npriority;
        }
    } else {
        switch (nb) {
            case '>':
                set_state(parser, s_version);
                break;

            default:
                parser->error = SLERR_BAD_PRIORITY;
        }
    }

    return pa_advance;
}

int priority_start(syslog_parser *parser, char nb) {
    switch(nb) {
        case '<':
            set_state(parser, s_priority);
            break;

        default:
            parser->error = SLERR_BAD_PRIORITY_START;
    }

    return pa_advance;
}

int octet_count(syslog_parser *parser, char nb) {
    int retval = pa_advance;

    if (IS_NUM(nb)) {
        size_t mlength = parser->message_length;

        mlength *= 10;
        mlength += nb - '0';

        if (mlength < parser->message_length || mlength == UINT_MAX) {
            parser->error = SLERR_BAD_OCTET_COUNT;
        } else {
            parser->message_length = mlength;
        }
    } else if (IS_WS(nb)) {
        parser->flags |= F_COUNT_OCTETS;
        parser->octets_remaining = parser->message_length + 1;
        set_state(parser, s_priority_start);
        retval = pa_rehash;
    } else {
        parser->error = SLERR_BAD_OCTET_COUNT;
    }

    return retval;
}

int msg_start(syslog_parser *parser, const syslog_parser_settings *settings, char nb) {
    on_cb(parser, settings->on_msg_begin);

    if (IS_NUM(nb)) {
        set_state(parser, s_octet_count);
    } else {
        set_state(parser, s_priority);
    }

    return pa_rehash;
}

// Big state switch
int uslg_parser_exec(syslog_parser *parser, const syslog_parser_settings *settings, const char *data, size_t length) {
    int d_index;
    int error = 0;
    char next_byte;

    for (d_index = 0; d_index < length; d_index++) {
        int action = pa_none;
        next_byte = data[d_index];

#if DEBUG_OUTPUT
        printf("Next byte: %c\n", next_byte);
#endif

        // Token state is managed first
        if (parser->token_state == ts_before) {
            switch (next_byte) {
                case ' ':
                case '\t':
                    action = pa_advance;
                    break;

                case '\r':
                case '\n':
                    if (!(parser->flags & F_COUNT_OCTETS)) {
                        parser->error = SLERR_PREMATURE_MSG_END;
                    }
                    break;

                default:
                    set_token_state(parser, ts_read);
                    action = pa_rehash;
            }
        } else {
            // Parser state
            switch (parser->state) {
                case s_msg_start:
                    action = msg_start(parser, settings, next_byte);
                    break;

                case s_octet_count:
                    action = octet_count(parser, next_byte);
                    break;

                case s_priority_start:
                    action = priority_start(parser, next_byte);
                    break;

                case s_priority:
                    action = priority(parser, next_byte);
                    break;

                case s_version:
                    action = version(parser, next_byte);
                    break;

                case s_timestamp:
                    action = parse_msg_head_part(parser, s_hostname, next_byte);
                    break;

                case s_hostname:
                    action = parse_msg_head_part(parser, s_appname, next_byte);
                    break;

                case s_appname:
                    action = parse_msg_head_part(parser, s_processid, next_byte);
                    break;

                case s_processid:
                    action = parse_msg_head_part(parser, s_messageid, next_byte);
                    break;

                case s_messageid:
                    action = parse_msg_head_part(parser, s_sd_start, next_byte);
                    break;

                case s_sd_start:
                    action = sd_start(parser, settings, next_byte);
                    break;

                case s_sd_element:
                    action = sd_element(parser, settings, next_byte);
                    break;

                case s_sd_field_start:
                    action = sd_field_start(parser, next_byte);
                    break;

                case s_sd_field:
                    action = sd_field(parser, settings, next_byte);
                    break;

                case s_sd_value_start:
                    action = sd_value_start(parser, next_byte);
                    break;

                case s_sd_value:
                    action = sd_value(parser, settings, next_byte);
                    break;

                case s_message:
                    d_index += read_message(parser, settings, data + d_index, length - d_index);
                    break;

                default:
                    parser->error = SLERR_BAD_STATE;
            }
        }

        // Upon error, exit the read loop regardless of action
        if (parser->error) {
            error = parser->error;
            uslg_parser_reset(parser);
            break;
        }

        // What action should be taken for this byte
        switch (action) {
            case pa_advance:
                if (parser->flags & F_COUNT_OCTETS) {
                    parser->octets_remaining--;
                }

                break;

            case pa_rehash:
                d_index--;
                break;
        }
    }

    return error;
}


// Exported Functions

void uslg_parser_reset(syslog_parser *parser) {
    parser->octets_read = 0;
    parser->octets_remaining = 0;
    parser->message_length = 0;
    parser->error = 0;
    parser->flags = 0;

    reset_msg_head(parser->msg_head);
    cstr_buff_reset(parser->buffer);
    set_state(parser, s_msg_start);
    set_token_state(parser, ts_before);
}

int uslg_parser_init(syslog_parser *parser, void *app_data) {
    memset(parser, 0, sizeof(*parser));

    // Create the msg_head
    parser->msg_head = (syslog_msg_head *) malloc(sizeof(syslog_msg_head));

    if (parser->msg_head == NULL) {
        // Allocating the msg_head struct failed!
        return SLERR_UNABLE_TO_ALLOCATE;
    }

    memset(parser->msg_head, 0, sizeof(syslog_msg_head));

    parser->app_data = app_data;
    parser->buffer = cstr_buff_new(MAX_BUFFER_SIZE);

    if (parser->buffer == NULL) {
        // Allocating the buffer failed so let go
        // of the memory we just allocated for the
        // msg_head struct
        free_msg_head_fields(parser->msg_head);
        parser->msg_head = NULL;
        return SLERR_UNABLE_TO_ALLOCATE;
    }

    uslg_parser_reset(parser);
    return 0;
}

void uslg_free_parser(syslog_parser *parser) {
    free_msg_head_fields(parser->msg_head);
    cstr_buff_free(parser->buffer);
    free(parser->msg_head);
    free(parser);
}

char * uslg_error_string(int error) {
    switch (error) {
        case SLERR_UNCAUGHT:
            return "Uncaught or unknown error.";

        case SLERR_BAD_OCTET_COUNT:
            return "Octet count on syslog message was bad or malformed.";

        case SLERR_BAD_PRIORITY_START:
            return "The priority token was not correctly started.";

        case SLERR_BAD_PRIORITY:
            return "The priority token was bad or malformed.";

        case SLERR_BAD_VERSION:
            return "The version token was bad or malformed.";

        case SLERR_BAD_SD_START:
            return "The SDATA token was not started correctly.";

        case SLERR_BAD_SD_FIELD:
            return "The SDATA field was bad or malformed.";

        case SLERR_BAD_SD_VALUE:
            return "The SDATA value was bad or malformed.";

        case SLERR_PREMATURE_MSG_END:
            return "The syslog message was ended with an unescaped delimeter before the parser could reach the message token.";

        case SLERR_BAD_STATE:
            return "The parser was in a bad state. This should not happen.";

        case SLERR_USER_ERROR:
            return "The parser encountered an error while running the associated callback.";

        case SLERR_BUFFER_OVERFLOW:
            return "The parser buffer is not large enough for the data being passed.";

        case SLERR_UNABLE_TO_ALLOCATE:
            return "Unable to allocate memory.";

        default:
            return "Unknown error value.";
    }
}
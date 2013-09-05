#include "cstr.h"

#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>


cstr * cstr_new(size_t size) {
    cstr *new_cstr = malloc(sizeof(cstr));

    if (new_cstr != NULL) {
        new_cstr->bytes = malloc(sizeof(char) * size);
        new_cstr->size = size;
    }

    return new_cstr;
}

void cstr_free(cstr *cstr) {
    if (cstr != NULL) {
        if (cstr->bytes != NULL) {
            free(cstr->bytes);
        }

        free(cstr);
    }
}

cstr * cstr_copy_from_cstr(cstr *src, size_t size) {
    return cstr_copy_from_char(src->bytes, size);
}

cstr * cstr_copy_from_char(char *string, size_t size) {
    cstr *copy = cstr_new(size);

    if (copy != NULL) {
        memcpy(copy->bytes, string, size);
    }

    return copy;
}

cstr_buff * cstr_buff_new(size_t size) {
    // Allocate a new cstr_buff struct
    cstr_buff *buffer = (cstr_buff *) malloc(sizeof(cstr_buff));

    if (buffer != NULL) {
        buffer->data = cstr_new(size);

        if (buffer->data != NULL) {
            buffer->position = 0;
        } else {
            // Allocating the actual char buffer failed
            // so release the newly allocated struct
            free(buffer);
            buffer = NULL;
        }
    }

    return buffer;
}

void cstr_buff_free(cstr_buff *buffer) {
    if (buffer->data != NULL) {
        cstr_free(buffer->data);
    }

    free(buffer);
}

void cstr_buff_reset(cstr_buff *buffer) {
    buffer->position = 0;
}

int cstr_buff_put(cstr_buff *buffer, char src) {
    int retval = 0;
    int next_position = buffer->position + 1;

    if (next_position > 0 && next_position < buffer->data->size) {
        buffer->data->bytes[buffer->position] = src;
        buffer->position = next_position;
    } else {
        retval = CSTR_BUFFER_OVERFLOW;
    }

    return retval;
}


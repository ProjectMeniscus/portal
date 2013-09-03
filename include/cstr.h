#ifndef cstr_h
#define cstr_h

#ifdef __cplusplus
extern "C" {
#endif

#include <sys/types.h>

// Errors
typedef enum {
    CSTR_BUFFER_OVERFLOW = 0
} cstr_error;


// Structs
typedef struct {
    char *bytes;
    size_t size;
} cstr;

typedef struct {
    cstr *data;
    size_t position;
} cstr_buff;


// Functions

// String
cstr * cstr_new(size_t size);
void cstr_free(cstr *cstr);

cstr * cstr_copy_from_cstr(cstr *src, size_t size);
cstr * cstr_copy_from_char(char *src, size_t size);

// Buffer
cstr_buff * cstr_buff_new(size_t size);
void cstr_buff_free(cstr_buff *buffer);
void cstr_buff_reset(cstr_buff *buffer);

int cstr_buff_put(cstr_buff *buffer, char src);

#ifdef __cplusplus
}
#endif
#endif

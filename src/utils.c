/**
 * Copyright (c) 2020 Paul-Louis Ageneau
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

#include "juice/juice.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h> // for sleep

#define BUFFER_SIZE 4096

const int write_sdp(char path[], const char *sdp) {
    FILE *fp = fopen(path, "wb");
    if (fp != NULL) {
        fputs(sdp, fp);
        fclose(fp);
        return 0;
    }
    printf("Failed to open SDP path: %s\n", path);
    return -1;
}

const char * read_sdp(char path[]) {
    FILE *f = fopen(path, "rb");
    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);
    
    char *string = malloc(fsize + 1);
    fread(string, 1, fsize, f);
    fclose(f);
    string[fsize] = 0;
    return string;
}

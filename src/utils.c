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

int read_sdp(char path[], char *sdp) {
    FILE *fp = fopen(path, "r");
    char line[JUICE_MAX_SDP_STRING_LEN];
    if (fp != NULL) {

        int i = 0;
        while (fgets(line, JUICE_MAX_SDP_STRING_LEN, (FILE*)fp) != NULL) {
            printf("Line read: %s\n", line);
            strcat(sdp, line);
            i++;
        }
        fclose(fp);
        return 0;
    }
    printf("Remote SDP not found: %s\n", path);
    return -1;
}

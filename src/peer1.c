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

static juice_agent_t *agent1;

static void on_state_changed1(juice_agent_t *agent, juice_state_t state, void *user_ptr);

static void on_gathering_done1(juice_agent_t *agent, void *user_ptr);

static void on_recv1(juice_agent_t *agent, const char *data, size_t size, void *user_ptr);

const int write_sdp(char path[], const char *sdp);

const char * read_sdp(char path[]);

int test_connectivity() {
	juice_set_log_level(JUICE_LOG_LEVEL_DEBUG);

    printf("Max SDP string length: %d\n", JUICE_MAX_SDP_STRING_LEN);
    printf("Max SDP ADDRESS string length: %d\n", JUICE_MAX_ADDRESS_STRING_LEN);

	// Agent 1: Create agent
	juice_config_t config1;
	memset(&config1, 0, sizeof(config1));
	// config1.stun_server_host = "stun.l.google.com";
	// config1.stun_server_port = 19302;
	config1.cb_state_changed = on_state_changed1;
	config1.cb_gathering_done = on_gathering_done1;
	config1.cb_recv = on_recv1;
	config1.user_ptr = NULL;

	agent1 = juice_create(&config1);

    char* SDP1_PATH = "sdp1";
    char* SDP2_PATH = "sdp2";

    //+++++++++++DESCRIPTION EXCHANGE++++++++++++

	// Agent 1: Generate local description
	char sdp1[JUICE_MAX_SDP_STRING_LEN];
	juice_get_local_description(agent1, sdp1, JUICE_MAX_SDP_STRING_LEN);
	printf("Local description 1:\n###\n%s\n###\n", sdp1);
    write_sdp(SDP1_PATH, sdp1);

    // Wait until SDPs have been copied between hosts.
    char dummy[20];
    printf("Confirm file 'sdp2' is in working directory: ");
    fgets(dummy, 20, stdin);

	// Agent 1: Read local description of agent 2 from stdin.
	char sdp2[JUICE_MAX_ADDRESS_STRING_LEN];
    strcpy(sdp2, read_sdp(SDP1_PATH));
	printf("Local description 2:\n###\n%s\n###\n", sdp2);

	// Agent 1: Receive description from agent 2
	juice_set_remote_description(agent1, sdp2);

    //+++++++++++++++++++++++++++++++++++++++++++

	// Agent 1: Gather candidates (and send them to agent 2)
	juice_gather_candidates(agent1);

    printf("Confirm remote done gathering: ");
    fgets(dummy, 20, stdin);

    // Agent 1: Add sdp from agent 2.
	juice_add_remote_candidate(agent1, sdp2);

	sleep(2);

	// -- Connection should be finished --

	// Check states
	bool success = juice_get_state(agent1) == JUICE_STATE_COMPLETED;

	// Retrieve addresses
	char local[JUICE_MAX_ADDRESS_STRING_LEN];
	char remote[JUICE_MAX_ADDRESS_STRING_LEN];
	if (success &= (juice_get_selected_addresses(agent1, local, JUICE_MAX_ADDRESS_STRING_LEN,
	                                             remote, JUICE_MAX_ADDRESS_STRING_LEN) == 0)) {
		printf("Local address  1: %s\n", local);
		printf("Remote address 1: %s\n", remote);
	}

	// Agent 1: destroy
	juice_destroy(agent1);

	// Sleep so we can check destruction went well
	sleep(2);

	if (success) {
		printf("Success\n");
		return 0;
	} else {
		printf("Failure\n");
		return -1;
	}
}

// Agent 1: on state changed
static void on_state_changed1(juice_agent_t *agent, juice_state_t state, void *user_ptr) {
	printf("State 1: %s\n", juice_state_to_string(state));

	if (state == JUICE_STATE_CONNECTED) {
		// Agent 1: on connected, send a message
		const char *message = "Hello from 1";
		juice_send(agent, message, strlen(message));
	}
}

// Agent 1: on local candidates gathering done
static void on_gathering_done1(juice_agent_t *agent, void *user_ptr) {
	printf("Gathering done 1\n");
	// juice_set_remote_gathering_done(agent2); // optional
}

// Agent 1: on message received
static void on_recv1(juice_agent_t *agent, const char *data, size_t size, void *user_ptr) {
	char buffer[BUFFER_SIZE];
	if (size > BUFFER_SIZE - 1)
		size = BUFFER_SIZE - 1;
	memcpy(buffer, data, size);
	buffer[size] = '\0';
	printf("Received 1: %s\n", buffer);
}

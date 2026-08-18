#pragma once

// Starts the dry-run response-action client. No GPIO or relay is controlled.
void responseActionClientBegin();

// Non-blocking between scheduled HTTP operations; call from the network loop.
void responseActionClientPoll();

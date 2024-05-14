The RMR health check request ID is 100
The RMR health check response ID is 101

A handler for RMR messages must have the format of `handler(summary, sbuf)` to be called by the `RMRXapp` loop, passing `sbuf` as the pointer to the RMR message buffer and `summary` as a dictionary containing the RMR message data and metadata.
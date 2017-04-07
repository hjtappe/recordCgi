#!/bin/sh

# Save this file as config.cgi and update the configuration parameters

# Redirect anyone who calls this file.
echo "Location: list.cgi"
echo
exit 0

# Set configuration parameters.
cdDevice=/dev/sr0

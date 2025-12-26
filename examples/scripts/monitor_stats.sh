#!/bin/bash
#
# Display the updating histogram of the data on the sixel-compatible
# terminal (mlterm, xterm, iterm2).
# execute:
#
# ./monitor_stats.sh dfset_file_name temperature [refresh_time]
#

DFSET=${1}
T=${2}
DT=60

if [ "${3}." != "." ]; then
	DT=${3}
fi

while true ; do
	clear
	date
	plot_stats -s -n -w 6 -h 4 "${DFSET}" $T
	sleep $DT
done

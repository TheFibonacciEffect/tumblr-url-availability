#! /bin/bash

statuses=$(cat urls.txt | python ./tumblr_avail.py)
availabilities=$(echo "$statuses" | grep -F "AVAILABLE")

if [[ $availabilities ]]
then
	# url(s) are available
	echo "$availabilities"
	# no urls available
fi

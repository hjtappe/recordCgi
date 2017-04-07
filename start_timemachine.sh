#!/bin/bash
set -u
set -e
set -x

export JACK_START_SERVER=yes

THIS=$(readlink -f $0)
SPOOLDIR=$(dirname $THIS)/spool

if [ ! -d "$SPOOLDIR" ]; then
	mkdir "$SPOOLDIR"
	chmod 770 "$SPOOLDIR"
fi

# start jackd using traced parameters
if [ -z "$(pidof jackd)" ]; then
	if [ -r "$(dirname $0)/jackdrc" ]; then
		. $(dirname $0)/jackdrc &
	elif [ -r "${HOME}/.jackdrc" ]; then
		. ${HOME}/.jackdrc &
	else
		# let jackd find the configuration.
		jackd &
	fi
	sleep 10
fi
# set levels
# main volume 100%
amixer -c0 -- sset Master playback 100%
# set line to record
amixer -c0 sset Line 100% unmute cap
# PCM 70
amixer -c0 sset PCM 100%

# Start Button
(cd "$SPOOLDIR"; timemachine) &
sleep 5
# Connect timemachine to jack
jack_connect system:capture_1 TimeMachine:in_1
jack_connect system:capture_2 TimeMachine:in_2
# Connect inputs to outputs
### Do not enable if the soundcard is configured to provide the output on the input!
#jack_connect alsa_pcm:capture_1 alsa_pcm:playback_1
#jack_connect alsa_pcm:capture_2 alsa_pcm:playback_2

# Prevent screen from going blank.
(sleep 15; xset -dpms s off s noblank s 0 0 s noexpose) &


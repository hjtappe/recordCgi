#!/bin/bash

# Script that could be started by a minutely cronjob or manually.
# It will look for records to be transcoded and archived in $ARCHIV_DIR and
# create a related *.pid file to indicate that transcoding is in progress.
# Also, for each such file, the wav will be:
# - transcoded to mp3,
# - transformed into a Audio-CD track and
# - included into a CD image
# After these actions, the files will be moved to $ARCHIV_DIR and the PID file
# will be removed.
#
# A script copy-local.sh can be provided which will be called with the mp3 file
# as an argument, which can be used to copy the MP3 file or do other actions
# after a successful file transcoding

# exit on unknown variables
set -u

# preset some variables, just to be flexible.
THISDIR="$(dirname $0)"
ARCHIV_DIR="$THISDIR/Archiv"
WAV_DIR="$THISDIR/spool"
FILE_BASE="tm"
# Should be cleaned at each restart (so unfinished jobs can be re-scheduled)
LOCK_DIR="/var/lock"
LOGFILE="$WAV_DIR/moveTranscode.log"

COPY_LOCAL="$THISDIR/copy-local.sh"

# Options, default settings
opt_quiet=n;

# Sub-function to be verbose if not stated differently
vecho ()
{
	[ "$opt_quiet" == "y" ] || echo "$@"
}

# Sub-function to show a usage message
usage()
{
	this=$(basename $0);
	cat << EOT
Usage: $this [Options]
Options include:
(SHORT) (LONG)
       -q     --quiet      Only output things on error.
Help: Have a look into the source code documentation for explaination.
EOT
}

# Sub-function to transcode the files
# Expects the job ID as argument.
do_transcode()
{
	JOB_ID=${1:-}
	W64_FILE="${WAV_DIR}/${JOB_ID}.w64"
	WAV_FILE="${WAV_DIR}/${JOB_ID}.wav"
	MP3_FILE="${WAV_DIR}/${JOB_ID}.mp3"
	INFO_FILE="${WAV_DIR}/${JOB_ID}.txt"
	WAV_ENCODER="/usr/bin/sndfile-convert"
	WAV_ENCODER_OPTIONS="-pcm16"
	MP3_ENCODER="/usr/bin/lame"
	MP3_OPTIONS="-s 44.1 -n 16 --signed -a --replaygain-accurate --clipdetect -b 96 -c "
	MP3_REDIRECT=""
	#MP3_ID_CONVERT="/usr/bin/mid3iconv"
	NORMALIZER="/usr/bin/normalize-audio"
	NORMALIZE_OPTIONS="--no-progress"
	RESAMPLE="/usr/bin/resample"
	RESAMPLE_OPTIONS="-to 44100"
	# Check for validity
	if [ -z "${JOB_ID}" ]; then
		echo >&2 "Invalid parameters"
		exit 1
	fi
	if [ ! -r "${W64_FILE}" ]; then
		echo >&2 "Unable to read ${W64_FILE}"
		exit 1
	fi
	if [ ! -r "${INFO_FILE}" ]; then
		echo >&2 "Unable to read ${INFO_FILE}"
		exit 1
	fi
	if [ ! -x "${WAV_ENCODER}" ]; then
		echo >&2 "Unable to execute ${WAV_ENCODER}"
		exit 1
	fi
	if [ ! -x "${NORMALIZER}" ]; then
		echo >&2 "Unable to execute ${NORMALIZER}"
		exit 1
	fi
	if [ ! -x "${MP3_ENCODER}" ]; then
		echo >&2 "Unable to execute ${MP3_ENCODER}"
		exit 1
	fi
	#if [ ! -x "${MP3_ID_CONVERT}" ]; then
	#	echo >&2 "Unable to execute ${MP3_ID_CONVERT}"
	#	exit 1
	#fi
	if [ ! -x "${RESAMPLE}" ]; then
		echo >&2 "Unable to execute ${RESAMPLE}"
		exit 1
	fi
	vecho
	vecho "### Preparing wav for burning"
	vecho
	${WAV_ENCODER} ${WAV_ENCODER_OPTIONS} "${W64_FILE}" "${WAV_FILE}"
	if [ $? != 0 ]; then
		echo >&2 "Error creating ${WAV_FILE}"
		exit 1
	fi
	# Normalize record.
	vecho
	vecho "### Normalizing record."
	vecho
	${NORMALIZER} ${NORMALIZE_OPTIONS} "${WAV_FILE}"
	if [ $? != 0 ]; then
		echo >&2 "Error normalizing ${WAV_FILE}"
		exit 1
	fi
	# Soundcard is stuck at 48000 Hz. Needs resample for CD recording.
	vecho
	vecho "### Resample the sound file"
	vecho
	TMPDIR="$(mktemp -d /tmp/${JOB_ID}.XXXXX)"
	${RESAMPLE} ${RESAMPLE_OPTIONS} "${WAV_FILE}" "${TMPDIR}/${JOB_ID}.wav"  | grep -v '\.\.'
	if [ $? != 0 ]; then
		echo >&2 "Error resampling ${WAV_FILE}"
		exit 1
	fi
	mv -v "${TMPDIR}/${JOB_ID}.wav" "${WAV_FILE}"
	rmdir "${TMPDIR}/"
	# Create MP3.
	vecho
	vecho "### Transcoding to mp3"
	vecho
	if [ "$opt_quiet" == "y" ]; then
		MP3_REDIRECT=">/dev/null"
	fi

	COPYRIGHT=`echo "$JOB_ID" | sed 's/^([0-9]{4})-.*/$1/'`
	TITLE=`sed '1p;d' "$INFO_FILE"`
	ARTIST=`sed '2p;d' "$INFO_FILE"`
	COMMENT=`sed '3p;d' "$INFO_FILE"`

	nice ${MP3_ENCODER} ${MP3_OPTIONS} \
		-tt "$TITLE" -ta "$ARTIST" -ty "$YEAR" -tg "Speech" \
		"${WAV_FILE}" "${MP3_FILE}" ${MP3_REDIRECT} 2>&1

	if [ $? != 0 ]; then
		echo >&2 "Error creating ${MP3_FILE}"
		exit 1
	fi
	#vecho
	#vecho "### Setting encoding of info to the MP3"
	#vecho
	#"${MP3_ID_CONVERT}" -e "UTF8" "${MP3_FILE}"
	#if [ $? != 0 ]; then
	#	echo >&2 "Error setting MP3 ID encoding"
	#	exit 1
	#fi
	vecho
	vecho "### Archiving the files in the archiv directory"
	vecho
	mkdir -p "${ARCHIV_DIR}"

	# replace characters not allowed in Windows in the file names.
	WAV_NEW_FILE=$(echo "${WAV_FILE}" | sed 's,^.*/,,;s,[^a-zA-Z0-9\._-],_,g')
	MP3_NEW_FILE=$(echo "${MP3_FILE}" | sed 's,^.*/,,;s,[^a-zA-Z0-9\._-],_,g')
	INFO_NEW_FILE=$(echo "${INFO_FILE}" | sed 's,^.*/,,;s,[^a-zA-Z0-9\._-],_,g')
	# Archive the files.
	mv -v "${WAV_FILE}" "${ARCHIV_DIR}/${WAV_NEW_FILE}" && \
	mv -v "${MP3_FILE}" "${ARCHIV_DIR}/${MP3_NEW_FILE}"
	mv -v "${INFO_FILE}" "${ARCHIV_DIR}/${INFO_NEW_FILE}"
	if [ $? != 0 ]; then
		echo >&2 "Error moving files to ${ARCHIV_DIR}/"
		exit 1
	fi
	# Save disk space.
	rm -v "${W64_FILE}"
	echo "0"

	if [ -f "$COPY_LOCAL" -a -x "$COPY_LOCAL" ]; then
		"COPY_LOCAL" "${ARCHIV_DIR}/${MP3_NEW_FILE}" 2>&1
		RET=$?
		echo $RET
	fi
}

# Get the command line options
for ARG; do
	var=$(echo $ARG | sed 's,=.*,,')
	value=$(echo $ARG | sed 's,.*=,,')
	case $var in
	-q|--quiet)
		opt_quiet=y
		break
	;;
	*)
		echo >&2 "Unknown argument: $ARG"
		usage >&2
		exit 1
	;;
	esac
done

# Only one of us.
LOCKFILE="$(ls ${LOCK_DIR}/${FILE_BASE}-*.pid 2>/dev/null)"
if [ "$LOCKFILE" != "" ]; then
	if (ps -p $(cat "$LOCKFILE") -o pid= >/dev/null); then
		echo >&2 "Only one transcoder per time, please."
		echo >&2 "This will loop through all pending jobs."
		echo >&2 "File '${LOCKFILE}' indicates PID:"
		cat "$LOCKFILE" >&2
		echo >&2
		exit 0
	else
		echo >&2 "Removing stale lock file."
		rm -v "$LOCKFILE" || exit 1
	fi
fi

# Cleanup Log file
touch "${LOGFILE}"
TMPFILE=$(mktemp /tmp/recordCgi.log.XXXXXX)
head -n 500 "${LOGFILE}" > "${TMPFILE}"
mv "${TMPFILE}" "${LOGFILE}"

while true; do
	vecho "Searching ${WAV_DIR} for records to transcode."
	WAV_FILES=$(ls ${WAV_DIR}/${FILE_BASE}-*T*.w64 2>/dev/null)
	JOBS_TO_DO="none"

	# Look for all WAV files to be found there.
	for WAV_FILE in ${WAV_FILES}; do
		JOBNAME=$(basename ${WAV_FILE} | sed 's,\.w64$,,')
		PIDFILE="${LOCK_DIR}/${JOBNAME}.pid"
		vecho -n "Found WAV job ${JOBNAME}"
		if [ -r "${WAV_DIR}/${JOBNAME}.txt" ]; then
			error=0
			if [ -r "${PIDFILE}" ]; then
				vecho " (active)"
			else
				vecho " (scheduled)"
				# create the PID file
				vecho "Writing ${PIDFILE}"
				echo -n "$$" > ${PIDFILE}
				error=$?
				if [ $error != 0 ]; then
					echo >&2 "Unable to write ${PIDFILE}"
				fi
				# Start transcoding
				if [ $error == 0 ]; then
					JOBS_TO_DO="yes"
					do_transcode ${JOBNAME} 2>&1 | tee -a "${LOGFILE}"
					if [ "$(tail -n 1 ${LOGFILE})" != "0" ]; then
						echo >&2 "Error transcoding ${JOBNAME}"
						exit 1
					fi
					# No error to be evaluated here directly (after pipe, we get tee errors)
				fi
				# remove the PID file after everything is finished.
				vecho "Removing ${PIDFILE}"
				rm -f "${PIDFILE}"
			fi
			if [ $error != 0 ]; then
				exit $error
			fi
		else
			vecho " (not scheduled)"
		fi
	done
	if [ "$JOBS_TO_DO" == "none" ]; then
		vecho "Finished."
		exit 0
	else
		vecho "Restarting scan."
	fi
done


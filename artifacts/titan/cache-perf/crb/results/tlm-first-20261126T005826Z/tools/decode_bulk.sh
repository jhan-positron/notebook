#!/usr/bin/env bash
# usage: decode_bulk.sh ARM_SCRIPT BULK_FILE
# Prints Arm's decoded summary for a saved output of "stlm bulk".
# It takes the functions of Arm's script scmi_telemetry.sh and leaves out the
# call of its main function, so nothing is configured and no device is opened.
arm_script="$1"
bulk_file="$2"
# shellcheck disable=SC1090
source <(sed '/^main "\$@"$/d' "$arm_script")
dump_values "$(cat "$bulk_file")" > /dev/null
dump_decoded_summary

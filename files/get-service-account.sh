#!/bin/bash

set -eox pipefail

sa_name="$1"

grep "^${sa_name}:" /data/values.yaml | awk -F ' ' '{print $2}'


#!/bin/bash

set -o errexit
# set -o nounset
set -o pipefail
set -e
set -x

env

if [[ -z $CDN_DOMAIN ]] ; then
  echo "\$CDN_DOMAIN  not set";
  exit 0;
fi

echo "Updating css links to ${CDN_DOMAIN}";

find static/css/ -name "*.css"
find static/themes/ -name "*.css"
ls -l

find static/css/ -name "*.css"  -exec sed -i "s#url(\"/#url(\"${CDN_DOMAIN}/#" {} \;
find static/themes/ -name "*.css"  -exec sed -i "s#src=\"/#src=\"${CDN_DOMAIN}/#" {} \;



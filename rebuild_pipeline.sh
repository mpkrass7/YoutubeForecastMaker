# Rebuild a kedro project without resetting the data directory or credenentials.yaml
# Usage: `bash rebuild_kedro.sh <project_name>` where project_name is the name of the existing kedro project

set -e
cwd=$(pwd)
cd ".."
mv "$1" "$1-old"
kedro new -n $1 -s $cwd --verbose
cp "$1-old/conf/local/credentials.yml" "$1/conf/local/credentials.yml"

if test -d "$1-old/data"; then
  cp -R "$1-old/data" "$1/data"
fi

rm -Rf "$1-old"
echo $(pwd)

# cd "$1"
# kedro run
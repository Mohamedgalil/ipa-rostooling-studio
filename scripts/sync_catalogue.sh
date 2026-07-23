#!/usr/bin/env bash
# sync_catalogue.sh -- re-copy assets/roscommonobjects/ and assets/rosmodelscatalog/ from
# the local material/code checkouts, diff against the vendored copy, and remind you to
# rebuild the indexes and update each PROVENANCE.md's sync date.
#
# WHY THIS EXISTS: the vendored catalogues are a point-in-time snapshot (see each
# PROVENANCE.md). This script is the one place that knows where they came from, so
# re-syncing never means re-deriving those paths by hand.
#
# Usage:
#   scripts/sync_catalogue.sh
#       Uses default source paths (relative to the plugin's parent directory, i.e.
#       assumes rostooling-plugin/ and material/code/ are siblings, as in this repo).
#   ROSCOMMONOBJECTS_SRC=/path ROSMODELSCATALOG_SRC=/path scripts/sync_catalogue.sh
#       Override either source path.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ROSCOMMONOBJECTS_SRC="${ROSCOMMONOBJECTS_SRC:-$PLUGIN_ROOT/../material/code/RosCommonObjects/de.fraunhofer.ipa.ros.communication.objects}"
ROSMODELSCATALOG_SRC="${ROSMODELSCATALOG_SRC:-$PLUGIN_ROOT/../material/code/RosModelsCatalog}"

TYPE_DEST="$PLUGIN_ROOT/assets/roscommonobjects"
NODE_DEST="$PLUGIN_ROOT/assets/rosmodelscatalog"

sync_one() {
    local label="$1" src="$2" dest="$3"
    shift 3
    local subdirs=("$@")

    if [ ! -d "$src" ]; then
        echo "SKIP $label: source not found at $src" >&2
        return 1
    fi

    echo "== $label =="
    echo "Diffing $dest against $src ..."
    local changed=0
    for sub in "${subdirs[@]}"; do
        if [ -d "$dest/$sub" ] && [ -d "$src/$sub" ]; then
            if ! diff -rq "$dest/$sub" "$src/$sub" > /tmp/sync_catalogue_diff_$$.txt 2>&1; then
                changed=1
                echo "  CHANGED: $sub"
                cat /tmp/sync_catalogue_diff_$$.txt | sed 's/^/    /'
            fi
            rm -f /tmp/sync_catalogue_diff_$$.txt
        fi
    done

    if [ "$changed" -eq 0 ]; then
        echo "  No differences -- vendored copy is already current."
    else
        echo "  Re-copying $label into $dest ..."
        for sub in "${subdirs[@]}"; do
            rm -rf "${dest:?}/$sub"
            cp -r "$src/$sub" "$dest/$sub"
        done
        echo "  Done. Remember to:"
        echo "    1. Update $dest/PROVENANCE.md's sync date (and commit SHA, if readable)."
        echo "    2. Re-run scripts/build_type_index.py / build_node_index.py."
        echo "    3. Re-run tests/oracle/ask_oracle.py --all and diff against the known-good baseline."
    fi
}

sync_one "RosCommonObjects" "$ROSCOMMONOBJECTS_SRC" "$TYPE_DEST" basic_msgs nav2_msgs
sync_one "RosModelsCatalog" "$ROSMODELSCATALOG_SRC" "$NODE_DEST" \
    arms cameras common controllers lidar manipulation navigation perception robots

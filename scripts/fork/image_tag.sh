#!/usr/bin/env bash
# Prints the Docker tag of the fork image for HEAD: <upstream release>-fork.<n>
#   <upstream release>  latest Tandoor release tag (x.y.z) that HEAD contains
#   <n>                 number of commits on top of that tag (grows with every merge to main)
# Example: 2.6.15-fork.92. Pre-release tags (2.0.0-beta1) are skipped.
# Needs the release tags (git fetch upstream --tags) and the full history.
set -euo pipefail
cd "$(dirname "$0")/../.."
BASE=$(git describe --tags --abbrev=0 --match '[0-9]*.[0-9]*.[0-9]*' --exclude '*-*' HEAD)
N=$(git rev-list --count "$BASE"..HEAD)
echo "${BASE}-fork.${N}"

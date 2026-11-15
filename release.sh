#!/usr/bin/env bash
# Release DPC Alert: a GitHub release whose notes come from CHANGELOG.md.
# Publishing it runs .github/workflows/release.yml, which writes the version in
# the integration and attaches dpc.zip, the file HACS installs.
#
# Usage: ./release.sh VERSION [--dry-run]
#
#   ./release.sh 2026.11.0b1            beta: a GitHub pre-release
#   ./release.sh 2026.11.0              release
#   ./release.sh 2026.11.0 --dry-run    show the notes and run the checks, change nothing
#   ./release.sh 2026.2.0               the release exists: only update its notes
#
# A beta (bN) is published as a pre-release with the notes of "## [Unreleased]":
# HACS offers it only to those who turn on pre-releases for DPC. A release
# turns "## [Unreleased]" into "## [VERSION] - <today>", updates the links at
# the end of the changelog, commits it to main and pushes it.
#
# The version is in the tag only: manifest.json and version.py stay as they
# are in the repository. The Tests and Validate workflows must have passed on
# the commit being released.
set -euo pipefail

readonly REPO=caiosweet/Home-Assistant-custom-components-DPC-Alert
readonly CHANGELOG=CHANGELOG.md
readonly BRANCH=main
readonly ASSET=dpc.zip
readonly REQUIRED_WORKFLOWS=(Tests Validate)

usage() {
  awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "$0"
  exit "${1:-0}"
}
die() {
  echo "error: $*" >&2
  exit 1
}
step() { printf '\n==> %s\n' "$*"; }

# In a dry run, report what would stop the release and go on.
problems=0
check() {
  if $dry_run; then
    echo "[dry-run] would stop: $*" >&2
    problems=$((problems + 1))
  else
    die "$*"
  fi
}
# In a dry run, print the commands that change something instead of running them.
run() {
  if $dry_run; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

version=""
dry_run=false
for arg in "$@"; do
  case $arg in
    -n | --dry-run) dry_run=true ;;
    -h | --help) usage ;;
    -*)
      echo "Unknown option: $arg" >&2
      usage 2
      ;;
    *)
      [[ -z $version ]] || usage 2
      version=${arg#v}
      ;;
  esac
done
[[ -n $version ]] || usage 2
[[ $version =~ ^[0-9]{4}\.(1[0-2]|[1-9])\.[0-9]+(b[0-9]+)?$ ]] ||
  die "invalid version '$version', expected YEAR.MONTH.PATCH, optionally with bN (e.g. 2026.11.0 or 2026.11.0b1)"
readonly tag="v$version"
beta=false
[[ $version == *b* ]] && beta=true
readonly beta

cd "$(dirname "$0")"
command -v gh >/dev/null || die "the GitHub CLI (gh) is required"
gh auth status >/dev/null 2>&1 || die "gh is not logged in: run 'gh auth login'"
remote=$(git remote -v | awk -v repo="$REPO" 'index($2, repo) && / \(push\)$/ { print $1; exit }')
[[ -n $remote ]] || die "no git remote points to $REPO: add it with 'git remote add upstream https://github.com/$REPO'"
readonly remote

# The section of a changelog under "## [TITLE]", without its heading.
section() {
  awk -v heading="## [$1]" '
    index($0, heading) == 1 { found = 1; next }
    /^## \[/ || /^\[[^]]+\]: / { found = 0 }
    found
  ' "$2" | sed '/./,$!d' | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}'
}

# The definitions, at the end of a changelog, of the reference links used in a
# notes file, so that links such as [#90] work in the release notes too.
link_definitions() {
  awk '
    NR == FNR {
      while (match($0, /\[[^]]+\]/)) {
        used[substr($0, RSTART, RLENGTH)] = 1
        $0 = substr($0, RSTART + RLENGTH)
      }
      next
    }
    /^\[[^]]+\]: / { label = $0; sub(/: .*/, "", label); if (label in used) print }
  ' "$1" "$2"
}

# The changelog of a release: "## [Unreleased]" becomes the version, dated
# today, under a new empty "## [Unreleased]", and the comparison links follow.
dated_changelog() {
  awk -v version="$version" -v today="$(date +%F)" '
    $0 == "## [Unreleased]" { print; print ""; print "## [" version "] - " today; next }
    /^\[Unreleased\]: .*\/compare\/.*\.\.\.HEAD$/ {
      url = $0; sub(/^\[Unreleased\]: /, "", url)
      base = url; sub(/\/compare\/.*/, "", base)
      previous = url; sub(/.*\/compare\//, "", previous); sub(/\.\.\.HEAD$/, "", previous)
      print "[Unreleased]: " base "/compare/v" version "...HEAD"
      print "[" version "]: " base "/compare/" previous "...v" version
      next
    }
    { print }
  ' "$CHANGELOG"
}

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
notes_file=$work/notes.md
changelog_file=$CHANGELOG

if $beta; then
  {
    echo "Beta of ${version%%b*}, for testing. In HACS, turn on the pre-releases"
    echo "of DPC to install it."
    echo
    section Unreleased "$CHANGELOG"
  } >"$notes_file"
elif ! grep -q "^## \[$version\] - " "$CHANGELOG"; then
  changelog_file=$work/CHANGELOG.md
  dated_changelog >"$changelog_file"
  grep -q "^\[$version\]: " "$changelog_file" ||
    die "$CHANGELOG has no '[Unreleased]: .../compare/vX...HEAD' link at the end"
  section "$version" "$changelog_file" >"$notes_file"
else
  # Already dated, e.g. to update the notes of a published release
  section "$version" "$CHANGELOG" >"$notes_file"
fi
[[ -n $(tr -d '[:space:]' <"$notes_file") ]] ||
  die "$CHANGELOG has no notes for $version: describe the changes under '## [Unreleased]'"
if links=$(link_definitions "$notes_file" "$changelog_file") && [[ -n $links ]]; then
  printf '\n%s\n' "$links" >>"$notes_file"
fi

step "Notes of $tag"
cat "$notes_file"

# An existing release only gets its notes updated.
if gh release view "$tag" --repo "$REPO" >/dev/null 2>&1; then
  step "$tag is already published: updating its notes"
  run gh release edit "$tag" --repo "$REPO" --notes-file "$notes_file"
  $dry_run || echo "Done: $(gh release view "$tag" --repo "$REPO" --json url --jq .url)"
  exit 0
fi

step "Checking the repository"
[[ -z $(git status --porcelain) ]] ||
  check "uncommitted changes: commit or stash them first"
git fetch --quiet "$remote" "$BRANCH"
if [[ $(git branch --show-current) != "$BRANCH" ]]; then
  check "not on the $BRANCH branch"
elif ! git merge-base --is-ancestor "$remote/$BRANCH" HEAD; then
  check "$BRANCH is behind $remote/$BRANCH: pull first"
elif [[ $(git rev-parse HEAD) != $(git rev-parse "$remote/$BRANCH") ]]; then
  check "$BRANCH has commits not on GitHub: push them and wait for the checks"
fi
git ls-remote --exit-code --tags "$remote" "refs/tags/$tag" >/dev/null &&
  check "the tag $tag already exists on GitHub"

step "Checking the workflows of $(git rev-parse --short HEAD)"
runs=$(gh run list --repo "$REPO" --commit "$(git rev-parse HEAD)" \
  --json workflowName,status,conclusion \
  --jq '.[] | "\(.workflowName)\t\(.status)\t\(.conclusion)"')
for workflow in "${REQUIRED_WORKFLOWS[@]}"; do
  result=$(awk -F '\t' -v name="$workflow" '$1 == name { print $2 "/" $3; exit }' <<<"$runs")
  case $result in
    completed/success) echo "$workflow: passed" ;;
    "") check "the $workflow workflow did not run on this commit" ;;
    completed/*) check "the $workflow workflow failed (${result#*/}): fix it first" ;;
    *) check "the $workflow workflow is still running: wait for it" ;;
  esac
done

if ((problems)); then
  echo >&2
  die "dry run: $problems problem(s) would stop the release"
fi

if [[ $changelog_file != "$CHANGELOG" ]]; then
  step "Dating the $version section of $CHANGELOG"
  if $dry_run; then
    diff -u "$CHANGELOG" "$changelog_file" || true
  else
    cp "$changelog_file" "$CHANGELOG"
    git commit --quiet -m "Release $version" -- "$CHANGELOG"
  fi
  run git push --quiet "$remote" "$BRANCH"
fi

step "Publishing $tag"
release_flags=()
$beta && release_flags+=(--prerelease)
run gh release create "$tag" --repo "$REPO" --title "$version" \
  --notes-file "$notes_file" --target "$(git rev-parse HEAD)" "${release_flags[@]}"
if $dry_run; then
  echo
  echo "Dry run: nothing was changed."
  exit 0
fi

step "Waiting for $ASSET"
run_id=""
for _ in {1..20}; do
  run_id=$(gh run list --repo "$REPO" --workflow release.yml --branch "$tag" \
    --limit 1 --json databaseId --jq '.[0].databaseId // empty')
  [[ -n $run_id ]] && break
  sleep 3
done
[[ -n $run_id ]] || die "the Release workflow did not start: check GitHub Actions"
gh run watch "$run_id" --repo "$REPO" --exit-status ||
  die "the Release workflow failed: fix it, then 'gh run rerun $run_id --repo $REPO --failed'"
gh release view "$tag" --repo "$REPO" --json assets --jq '.assets[].name' | grep -qx "$ASSET" ||
  die "$tag has no $ASSET: HACS cannot install it"

echo
echo "Published: $(gh release view "$tag" --repo "$REPO" --json url --jq .url)"
if $beta; then
  echo "HACS offers it to those who turn on the pre-releases of DPC."
else
  echo "HACS offers it as an update at its next refresh."
fi

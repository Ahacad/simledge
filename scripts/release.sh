#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 <patch|minor|major>"
    exit 1
}

[[ $# -ne 1 ]] && usage

bump="$1"
file="pyproject.toml"
current=$(grep '^version = ' "$file" | head -1 | sed 's/version = "\(.*\)"/\1/')

IFS='.' read -r major minor patch <<< "$current"

case "$bump" in
    patch) patch=$((patch + 1)) ;;
    minor) minor=$((minor + 1)); patch=0 ;;
    major) major=$((major + 1)); minor=0; patch=0 ;;
    *) usage ;;
esac

next="${major}.${minor}.${patch}"

echo "Bumping $current → $next"

sed -i "0,/^version = \"${current}\"/s//version = \"${next}\"/" "$file"

git add "$file"
git commit -m "chore(release): bump version to ${next}"
git tag "v${next}"

echo "Generating CHANGELOG.md..."
git-cliff --output CHANGELOG.md
git add CHANGELOG.md
git commit -m "docs(release): update changelog for ${next}"

echo ""
echo "Done. Push with:"
echo "  git push origin master --tags"

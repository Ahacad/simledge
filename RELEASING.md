# Releasing

1. Edit the version in `pyproject.toml`:
   ```toml
   version = "0.2.0"
   ```

2. Commit the version bump:
   ```bash
   git add pyproject.toml
   git commit -m "chore(release): bump version to 0.2.0"
   ```

3. Create and push a tag:
   ```bash
   git tag v0.2.0
   git push origin master --tags
   ```

4. The GitHub Actions workflow generates release notes with git-cliff, builds the package, and creates a GitHub release with the sdist and wheel attached.

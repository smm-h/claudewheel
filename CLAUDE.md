# claudewheel

## Release workflow

This project uses [share-it-on](https://github.com/smm-h/share-it-on) for release orchestration.

- Update CHANGELOG.md with a `## X.Y.Z` entry describing changes
- Run `share-it-on release [patch|minor|major]` to bump version and create a GitHub Release
- CI handles `npm publish` automatically via OIDC Trusted Publishing (no tokens needed)
- First publish must be done locally: `npm login && npm publish --access public`
- After first publish, configure Trusted Publishing on npmjs.com (package settings)
- Never run `npm publish` manually after Trusted Publishing is configured
- Use `share-it-on release --dry-run` to preview a release without making changes

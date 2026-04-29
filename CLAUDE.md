# claudewheel

## Release workflow

This project uses [share-on-npm](https://github.com/smm-h/share-on-npm) for release orchestration.

- Update CHANGELOG.md with a `## X.Y.Z` entry describing changes
- Run `share-on-npm release [patch|minor|major]` to bump version and create a GitHub Release
- CI handles `npm publish` automatically via OIDC Trusted Publishing (no tokens needed)
- First publish must be done locally: `npm login && npm publish --access public`
- After first publish, configure Trusted Publishing on npmjs.com (package settings)
- Never run `npm publish` manually after Trusted Publishing is configured
- Use `share-on-npm release --dry-run` to preview a release without making changes

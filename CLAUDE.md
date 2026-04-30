# claudewheel

## Release workflow

This project uses [rlsbl](https://github.com/smm-h/rlsbl) for release orchestration.

- Update CHANGELOG.md with a `## X.Y.Z` entry describing changes
- Run `rlsbl release [patch|minor|major]` to bump version and create a GitHub Release
- CI handles `npm publish` automatically via OIDC Trusted Publishing (no tokens needed)
- First publish must be done locally: `npm login && npm publish --access public`
- After first publish, configure Trusted Publishing on npmjs.com (package settings)
- Never run `npm publish` manually after Trusted Publishing is configured
- Use `rlsbl release --dry-run` to preview a release without making changes

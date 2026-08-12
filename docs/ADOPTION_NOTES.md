# Adoption Notes

Авторея should track interest honestly. Do not create fake stars, fake download
activity, fake issues, or fake testimonials.

## What To Watch

- GitHub stars: a simple signal that people want to follow the project.
- Release asset download count: downloads of files attached to GitHub releases.
- Issues: bug reports, feature requests, security concerns, and documentation
  questions.
- User feedback: comments from writers, testers, and maintainers.
- Pull requests: outside contributions or review suggestions.

## Downloads

GitHub counts downloads per release asset. For Авторея, the main public asset is
usually `Avtoreya-Setup.exe`.

Download count is not the same as active users. It can include repeated
downloads, maintainer checks, failed installs, or automated fetches. Treat it as
a rough interest signal only.

## Maintainer Commands

Check the latest release and asset download counts:

```powershell
gh release view --repo ryzhkevichpavel-del/avtoreya --json tagName,assets --jq '.tagName, (.assets[] | "\(.name): \(.downloadCount) downloads")'
```

Check repository stars:

```powershell
gh repo view ryzhkevichpavel-del/avtoreya --json stargazerCount --jq '.stargazerCount'
```

List open issues:

```powershell
gh issue list --repo ryzhkevichpavel-del/avtoreya --state open
```

## Review Rhythm

Before each release, record a short maintainer note:

- latest release tag;
- release asset download count;
- number of open issues;
- notable feedback themes;
- security or data-loss concerns to address next.

Keep these notes factual. If there is little adoption yet, say that plainly.

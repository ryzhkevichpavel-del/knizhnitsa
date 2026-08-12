# Code signing policy

Книжница uses code signing so that Windows users can verify that release files
come from the project and were not changed after publication.

Free code signing provided by [SignPath.io](https://signpath.io/), certificate by
[SignPath Foundation](https://signpath.org/).

## Team roles

- Committer and reviewer: [Pavel Ryzhkevich](https://github.com/ryzhkevichpavel-del)
- Approver: [Pavel Ryzhkevich](https://github.com/ryzhkevichpavel-del)

Changes from other contributors must be reviewed before they are merged. Every
request to sign a release must be approved manually by the approver.

## Build and release rules

- Release binaries are built from the public
  [source repository](https://github.com/ryzhkevichpavel-del/knizhnitsa).
- The automated Windows build uses
  [GitHub Actions](https://github.com/ryzhkevichpavel-del/knizhnitsa/actions).
- Product names and version numbers in the executable and installer must match
  the release version.
- Only official Книжница release files built from this repository may be signed.
- Signed releases are published on
  [GitHub Releases](https://github.com/ryzhkevichpavel-del/knizhnitsa/releases).

## Privacy

The application privacy policy is available in [PRIVACY.md](PRIVACY.md).


# hao-assets

For people installing hao: the release files of [hao-patcher](https://github.com/lythka/hao-patcher).

You don't need to download anything here by hand. The one command in
[Install](https://github.com/lythka/hao-patcher#install) fetches what it needs and checks each file. Each release
holds four files:

| File | What it is |
|---|---|
| `hao` | The command you run: a short shell script you can read |
| `hao-RELEASE.tar` | Everything of ours in one archive: the builder kit, hao-runtime, the compatibility fixes and the pinned build tools |
| `release.json` | Every file the installer uses, each with its origin, size and SHA256 |
| `SHA256SUMS` | Checksums of the three files above |

A signed release adds `release.json.sig` and `SHA256SUMS.sig`. Apple's files and third-party tools are never here:
`release.json` names them and hao downloads them from their publishers.

To check a release by hand, see [Verify a release](https://github.com/lythka/hao-patcher/blob/main/docs/verify.md).

## Licence

MIT; see [LICENSE](LICENSE).

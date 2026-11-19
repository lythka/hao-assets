# hao-assets

For people installing hao: the prebuilt files each release of [hao-patcher](https://github.com/lythka/hao-patcher) uses.

`hao create-installer` downloads them for you; you don't need to download anything here by hand. Each release holds
`release.json` (the list of every file a hao release uses, with its size and sha256), the prebuilt files and
`SHA256SUMS`. Apple's own files are never here: `release.json` names them and hao downloads them from Apple.

To check your downloads, see [Verify this release](https://github.com/lythka/hao-patcher/blob/main/docs/verify.md).

## Licence

MIT; see [LICENSE](LICENSE).

# hao-assets

The contract between the hao repositories, and (later) their release manifests. Workflow plan step 3. This is
a local repository with no remote yet: whether and when it becomes the public `hao-assets` is the owner's
decision.

| Boundary | File | The checker refuses |
|---|---|---|
| research → runtime | `generated.lock` in hao-runtime: every generated file with sha256, export id, OS build, cache UUID, format | hand-edited or unlisted generated files; a file stamped for another OS build than its entry |
| runtime → patcher | `payload-manifest.json` in a hao-runtime payload: version, commit, clean, OS build, cache UUID, units version and hash, install-layout version, file hashes | a dirty build; an OS build or layout version the patcher did not declare; a missing or changed file |
| all → public | tracked files and commit messages | private repositories, evidence folders, home folders |

```sh
python3 -I hao_contract.py check REPO                  # the checks REPO/contract.json names
python3 -I hao_contract.py stamps REPO 'src/*_gen.inc'  # OS build stamped in each generated file
python3 -I hao_contract.py lock REPO 'src/*_gen.inc' --os-build 26B131 --cache-uuid U --format F
```

Standard library only; each repository vendors a pinned copy and declares its checks in `contract.json`.

## Verify

```sh
python3 -I -B -m unittest discover -s tests
```

Each check passes on a matching fixture and refuses a seeded violation (hand edit, unlisted file, stamp for
another OS build, dirty payload, wrong OS build or layout version, changed file, private path in a file or a
commit message).

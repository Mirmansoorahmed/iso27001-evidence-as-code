# Demo

A quarter of an hour, on a laptop that already has Python 3.12, Terraform 1.10.5, Conftest 0.71.1, Checkov 3.2.449, `jq` and `sha256sum`. The figures below are the committed run of `eac demo`, recorded in [`results/summary.json`](../results/summary.json). That run started at `2026-10-27T12:19:08Z` and finished at `2026-10-27T12:19:12Z` on host `cursor` (Python 3.12.3, Checkov 3.2.449, Conftest 0.71.1, OPA 1.21.1, Terraform v1.10.5). A fresh run prints the same shape of transcript and new timestamps.

## 0–3 min — install and scan

```bash
python3 -m pip install -e ".[dev]"
make demo
```

`make demo` is `eac demo`. It scans `lz/`, the labelled fixtures, the drift pair and the sample pull request. Then it builds a genesis pack (empty previous hash) and ten linked packs, fetches TerraGoat, writes `results/` and `dashboard/`, verifies the pack, and flips one byte.

Read the transcript before opening anything else. On the committed run it said:

- Landing zone failures: 0
- Annex A: 15 of 93 have an automated check (16.1%). partial 15, manual 76, not applicable 2, automated-pass 0, automated-fail 0
- C5:2020: 15 of 121 (12.4%). DORA tracked slice: 4 of 8 (50.0%)
- Own fixtures: TP 26, FP 0, FN 0, TN 270
- Drift: A.8.9 and A.8.24 lost evidence at `35d84e21208c6d0758dc0cb8cb77d41d5b402cf2`
- Auditor pack: median 0.004488 s over 10 builds (min 0.004225 s, max 0.004686 s)
- Pipeline wall clock, including the scan: 3.9689 s. The scan alone was 2.4114 s
- TerraGoat `729f8da62c6a` technical: TP 17, FP 0, FN 1, TN 3. The FN rule is `CKV_AZURE_3`
- TerraGoat, NordPay Rego only: TP 3, FP 0, FN 0, TN 5

The median is the export, after collection. Quoting 0.004488 s as the time to scan Azure would be wrong; there is no Azure call, and the scan of the Terraform is the 2.4114 s.

## 3–7 min — the statement of applicability

Open `dashboard/index.html`. The page is static. The header is the 2026-Q4 rollup for `lz/`.

The five counts on a clean landing zone are partial 15, automated-fail 0, automated-pass 0, manual 76, not applicable 2. Press **Partial**. Fifteen rows remain: A.5.9, A.5.12, A.5.15, A.5.23, A.5.28, A.8.2, A.8.3, A.8.5, A.8.9, A.8.13, A.8.14, A.8.15, A.8.16, A.8.20, A.8.24. Press **N/A** and you get A.7.6 and A.8.30, each with the reason the fiction is out of scope. Press **Manual** for the other 76. The search box filters by id or title; `A.8.24` is the cryptography gloss.

Partial means the automated checks passed and someone still has to do the rest of the control. That is why automated-pass stays at 0 even though the landing zone has no failures. The same table is `dashboard/soa.md` if you would rather read it in a diff.

## 7–11 min — the pack and a one-byte tamper

The demo leaves the pack at `dist/demo/pack/` and a tarball at `dist/demo/nordpay-evidence-2026-Q4.tar.gz`. `dist/` is gitignored, so a clone rebuilds it. The committed chain is `results/chain/`.

```bash
tar -tzf dist/demo/nordpay-evidence-2026-Q4.tar.gz | head
( cd dist/demo/pack && sh ./verify.sh )
```

`verify.sh` asks `jq` for each file hash in `MANIFEST.json`, checks them with `sha256sum -c`, checks `MANIFEST.sha256`, then checks the embedded `previous/MANIFEST.json` the same way. It does not call Python, OpenSSL, Cosign or awk. On the committed run the previous manifest hash was `fb0583cd102f641812835d897753f2eae3f89c79f42a3c9ef9023826fac4d5fa` and the linked manifest was `a3f8cd9d35b6ec262fe9780687261ed321518607fc3f5cada34ac89cc4a748dc`. Those two change when `observed_at` changes. The counts above do not.

`make demo` already flips one byte of `evidence/records.json`, expects `verify.sh` to exit non-zero, and restores the file. To do it by hand:

```bash
cd dist/demo/pack
cp evidence/records.json /tmp/records.json
printf 'x' | dd of=evidence/records.json bs=1 seek=20 conv=notrunc status=none
sh ./verify.sh ; echo "exit $?"
cp /tmp/records.json evidence/records.json
sh ./verify.sh
```

The first `verify.sh` fails. The restored file passes.

## 11–14 min — drift and the sample pull request

`fixtures/drift/baseline` is a storage account on TLS 1.2. `fixtures/drift/broken` is the same account on TLS 1.0. The pipeline compares the two SoA rollups and reports controls that newly fail.

```bash
python3 -c 'import json; print(json.load(open("results/drift.json"))["lost"])'
```

Both A.8.9 and A.8.24 come back, rule `CKV_AZURE_44`, file `fixtures/drift/broken/main.tf`, commit `35d84e21208c6d0758dc0cb8cb77d41d5b402cf2`. That commit is the one that added the broken file (`git log -1 -- fixtures/drift/broken/main.tf`). Nothing in a subscription moved.

`fixtures/pr-preview/main.tf` turns anonymous blob access on and drops TLS to 1.0. The failed controls are A.5.15, A.8.3, A.8.9 and A.8.24. They are listed on the dashboard under “If the sample pull request landed” and in `results/summary.json` as `pr_preview_failed_controls`.

The own-fixture matrix is `results/fixture-score.json`. 22 directories are misconfigured, one (`23-role-owner-on-group`) is a negative control: Owner on a resource group is allowed by the Rego, Owner on a subscription is not. TP 26, FP 0, FN 0, TN 270. Treat that as “the labels still match”, and read the TerraGoat block for a tree this repo did not write. The technical FN of 1 is `CKV_AZURE_3` only.

## 14–15 min — what is switched off

```bash
eac capa --evidence results/evidence.json
eac sign --manifest results/chain/latest.sha256
```

Both print `skipped` unless you opt in. CAPA wants `EAC_CAPA=1`, `GITHUB_TOKEN` and `GITHUB_REPOSITORY`. Cosign wants `EAC_COSIGN=1` and a `cosign` binary. The workflow has the same gates as repository variables. The sha256 chain is already in the pack either way.

Tests, including the TerraGoat fetch:

```bash
make validate
pytest
```

`make validate` is `terraform fmt -check`, `init -backend=false`, and `validate` in `lz/`.

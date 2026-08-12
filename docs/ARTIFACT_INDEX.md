# Local artifact index

All packages below were moved from the repository root to
`.artifacts/packages/` during the August 2026 consolidation. No package was
deleted. SHA-256 values were recomputed after the move; every available sidecar
checksum verified successfully. The artifact directory is ignored by Git by
design.

| Package | Size (bytes) | SHA-256 | Phase/status | Raw/provenance contents | Canonical report |
|---|---:|---|---|---|---|
| `auto-research-package-20260808T142104Z.tar.gz` | 257,787 | `6b6104f14d2cb9a07d7a9ac4c1a637bdfd7b6698b45ffea8bc2e63d64a7266b1` | historical handoff | docs/provenance bundle | [AUTO_RESEARCH_FINAL_BRIEF](AUTO_RESEARCH_FINAL_BRIEF.md) |
| `cross-domain-transfer-bottleneck-v1-package.tar.gz` | 3,493,943 | `cac3ea3758f4c69005e349cf0004bf772927aa545b75258cb326ff81563dca78` | partial / not qualified | source, tests, docs, analysis | [report](CROSS_DOMAIN_TRANSFER_BOTTLENECK_V1_REPORT.md) |
| `developmental-dynamics-v2-clean2x2-package.tar.gz` | 10,254,983 | `81448808f20fae3af17d10f8e8856795bce935e3072421f3e865879fe461a88c` | exploratory clean/recovered | campaign manifest and run artifacts | [CLEAN_2X2 report](CLEAN_2X2_MECHANISM_REPORT.md) |
| `ecological-information-geometry-v3-package.tar.gz` | 580,500 | `e22e269b9ea9b78bbb516f46c588af97e6accbff314232588dad0bb49ce69e2f` | offline prerequisite | source, tests, formalism | [V3 report](ECOLOGICAL_INFORMATION_GEOMETRY_V3_REPORT.md) |
| `ecology-regime-observability-v1-package.tar.gz` | 820,331 | `0ae79288e1a33e79f5e5e48baf6aaca027f09a7cac533c7052a4c0bb9d8d4030` | diagnostic | source/tests/reports | [report](ECOLOGY_REGIME_OBSERVABILITY_V1_REPORT.md) |
| `local-plasticity-curve-v1-package.tar.gz` | 2,291,461 | `bf6f02bb0d25049e230e20350443a36f330f44c714cdb1d72e9567e4d793bfb2` | **qualified microscopic gate** | manifest, raw events, analysis | [report](LOCAL_PLASTICITY_CURVE_V1_REPORT.md) |
| `memory-representation-thinking-v1-package.tar.gz` | 2,997,344 | `0c35d5a049ff68c0e256c5c63592bbc4817a592ef53787de9ba2673549ce5d2c` | diagnostic calibration | calibration events/manifest | [report](MEMORY_REPRESENTATION_THINKING_REPORT.md) |
| `minimal-developmental-society-v1-analysis-repair-package.tar.gz` | 9,081,339 | `761bea6649eed5e1f435d8e04b1cfe7097bad303303f7ca74d2c266a40f92cfd` | **repaired analysis** | repair source/tests/docs/derived outputs | [repair report](MINIMAL_DEVELOPMENTAL_SOCIETY_V1_ANALYSIS_REPAIR_REPORT.md) |
| `minimal-developmental-society-v1-package.tar.gz` | 18,421,676 | `fdcaf374559e0478c2b13738a7ec7f8b275c81ea1373cb163d390d7886574de6` | paid run; derived analysis superseded | raw/protocol/report bundle | [execution log](MINIMAL_DEVELOPMENTAL_SOCIETY_V1_EXECUTION_LOG.md) |
| `observable-ecological-information-v31-package.tar.gz` | 59,434 | `62281c3bdc9345216d800f77fb5148cf706c02eabfd94cebf0e7490a0896c7cf` | offline observation-channel prerequisite | source/tests/docs | [V3.1 report](ECOLOGICAL_INFORMATION_GEOMETRY_V31_REPORT.md) |
| `observable-learner-calibration-v1-package.tar.gz` | 495,538 | `569d33fe0f2d7766ffaf34bc50fcde6916599162de633fb85f6bc77254af33dc` | partial / not qualified | derived response-level tables | [report](OBSERVABLE_LEARNER_CALIBRATION_V1_REPORT.md) |
| `observable-learner-calibration-v2-package.tar.gz` | 632,173 | `f8f4f17b5428cb9ef0f01013a5f944a115e0d5fc307a7bca9086c222f97b4399` | partial / not qualified | source/tests/provenance/report | [report](OBSERVABLE_LEARNER_CALIBRATION_V2_REPORT.md) |
| `overnight-research-package.tar.gz` | 11,281,973 | `62e3379d425e98e5d1869119b645d01b57752e42b5a71d38fa8b84a307ad228f` | historical overnight handoff | reports and reproducibility notes | [overnight report](OVERNIGHT_RESEARCH_REPORT.md) |
| `relation-signal-causal-transfer-v1-package.tar.gz` | 3,284,782 | `8cc1c3c2b135d065f82179d161a35456044a11cb6b723a97db8cf80e2e5bddc6` | partial relation control | analysis/manifest/tests | [report](RELATION_SIGNAL_CAUSAL_TRANSFER_V1_REPORT.md) |
| `semantic-task-ecology-qualification-v1-package.tar.gz` | 1,612,368 | `ea467ec3466fb6b2696e18ca86984e831abb9d9544092f96fde3b090477f6238` | ecology qualification handoff | project source and protocol | [qualification](SEMANTIC_TASK_ECOLOGY_QUALIFICATION.md) |
| `transfer-geometry-control-v1-package.tar.gz` | 2,863,526 | `278010f194994c3dd132e4f3b015fed6ae20344591d01d741a032715df905198` | partial controlled geometry | raw geometry data/manifests | [report](TRANSFER_GEOMETRY_CONTROL_V1_REPORT.md) |

Sidecar `.tar.gz.sha256` files are retained beside the packages when they were
present. The package itself is not a substitute for the canonical report or for
the original local raw run directory; both references should be preserved when
making a scientific handoff.

## Verification command

From the repository root:

```bash
for f in .artifacts/packages/*.sha256; do
  expected=$(awk '{print $1}' "$f")
  archive="${f%.sha256}"
  test -f "$archive" || archive="${archive}.tar.gz"
  actual=$(shasum -a 256 "$archive" | awk '{print $1}')
  test "$expected" = "$actual" || exit 1
done
```

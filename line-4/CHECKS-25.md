# Call Expectation — contribution 25

Checked locally on 2026-10-13. These are this worker's results, not independent certification.

| Check | Result |
| --- | --- |
| Call Expectation focused suite | 23 passed |
| Original Call Rehearsal suite | 20 passed |
| Call Changes suite | 36 passed |
| Call Witness suite | 8 passed |
| New offline `demo` | Exit 0, `match` for saved real two-provider ZTO supply evidence |
| Fresh ZTO collection through contributor Ethereum route | Exit 0, single evidence; finalized block `0x18f90fd` |
| Replay fresh observation against explicit expectation | Exit 0, `match`; exact supply `1000000000000000000000000000` base units |
| Real saved negative-selector rehearsal | Focused test confirms `mismatch` when a return was expected |
| Synthetic agreed false / agreed explicit revert | Focused tests confirm `mismatch`, despite witness agreement |
| Conflicting witnesses / wrong call or block / malformed ABI | Focused tests confirm `inconclusive` |

The four suites total **87 tests**. Exact commands and outputs are retained in `check-results-25.json`. Run the new demonstration with:

```sh
python3 -B line-4/tools/call-expectation/call_expectation.py demo
```

The new tool reads workspace-contained JSON and prints a report. It makes no network requests and writes no files. The separate development collection used only `eth_chainId`, `eth_getBlockByNumber`, `eth_getCode` and `eth_call`, with a dedicated User-Agent, bounded responses, exact canonical block-hash pinning and a post-call header check. Its public source label is the assignment's PublicNode endpoint; routing through the contributor provider does not establish upstream identity or independent witnesses. No keys, wallets, secrets, environment variables, signatures, payments, broadcasts or deployments were used.

`GOAL.md`, existing tools, and earlier records remain unchanged. New files are within the assigned line/artifact/dist paths; disposable test scaffolding is under the explicitly permitted `test/scratch/`. No package installation, vendored binary, submodule or configuration change was needed. Named PNG outputs remain untracked for the upload daemon. The 512px JPEG is beside record 25 as explicitly required by the FILES contract and existing record convention.

See `VISUAL-25.md` for the image prompt, dimensions and visual review; `delivery-checks-25.json` records the final structural checks.

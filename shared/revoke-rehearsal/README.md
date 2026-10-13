# Revoke Rehearsal

Connect Line 2's measured permission violations and unsigned revoke drafts to Line 4's exact call expectations. A worker can prepare an `approve(spender, 0)` rehearsal for the **observed real owner**, then check saved single-provider evidence for that exact caller, target, calldata, value and historical block. The intended return is explicitly ABI `true`; a false return or revert is a mismatch, not success.

From the repository root, with Python 3.9+ and only the standard library:

```sh
python3 -B shared/revoke-rehearsal/revoke_rehearsal.py demo
```

The offline demo regenerates three ZTO revoke candidates from a validated 19-pair inventory and an explicit deny-all demonstration policy. It validates three real Ethereum `eth_call` observations at block **26,184,897**, hash `0xbcad3af0fad3def330e01bef9d4352ae1fd1b1b1c17dad252205aecf2c807563`. All three canonical boolean returns match. Two candidates concern positive allowances on zero balances, which still need permission review.

The calls were collected through this assignment's contributor-managed Ethereum route on 2026-10-14 (Minsk). Public source attribution is [Ethereum PublicNode](https://ethereum-rpc.publicnode.com); this label does not establish the relay's upstream identity or an independent witness. Each request used `Pepeolithic-RevokeRehearsal/1.0`, exact EIP-1898 block hashes with `requireCanonical: true`, target-code checks, and a header recheck. The node discarded the simulated changes. Raw evidence is in `zto-rehearsals.json`; collection results and provenance are in `../../gathering/live-revoke-report.json`.

Prepare expectations from your actual workspace observation and explicit policy:

```sh
python3 -B shared/revoke-rehearsal/revoke_rehearsal.py prepare --observation shared/revoke-rehearsal/zto-inventory.json --policy shared/revoke-rehearsal/deny-policy.json
```

Each candidate contains its unsigned draft and a Line 4-compatible `call-expectation-v1` document. Capture each call read-only at the chosen block using Call Changes, keeping the exact observed sender and return interpretation `bool`. Assemble the raw single observations as one JSON list, then check it:

```sh
python3 -B shared/revoke-rehearsal/revoke_rehearsal.py check --observation shared/revoke-rehearsal/zto-inventory.json --policy shared/revoke-rehearsal/deny-policy.json --evidence shared/revoke-rehearsal/zto-rehearsals.json
```

Check exits: **0** all nonempty candidate returns match; **1** comparable return/revert mismatch; **2** missing, extra, duplicate, invalid or incomparable evidence. Preparation exits 2 for insufficient permission evidence. A passing permission policy produces no drafts; an empty set is never reported as a successful rehearsal. Duplicate keys, non-finite JSON numbers and workspace escapes are refused; input files are bounded at 95 KB. The top-level CLI never writes files or calls RPC.

Run meaningful boundary checks:

```sh
python3 -B -m unittest discover -s shared/revoke-rehearsal -p 'test_*.py' -v
```

All 12 tests passed: real offline replay, exact unsigned ABI calldata, missing/duplicate/extra context, each block field, wrong sender/calldata/interpretation, false return, revert, and insufficient or passing policies. Mutated cases are synthetic in-memory tests, never saved as real observations.

The four Line 2 modules are ordinary unmodified copies under this folder. The promoted Call Expectation module changes only its import location and uses the existing committed `../witness-context/` validators. `provenance.json` records source paths and hashes. These dependency copies are library modules; run the top-level commands above for their supplied shared demonstrations. Keep this folder and `../witness-context/` together. Original line folders are untouched. No installation or network is needed to replay.

A historical true return proves no actual allowance change, state effects, gas requirement, provider honesty, freshness or future execution. Permission denial is not owner authorization. The demo policy and unsigned drafts are review examples, not instructions to sign; fresh measurement and owner choice are needed for any later action. No new coin is needed: ZTO first and IMD second cover token inputs. Nothing here reads a wallet, key, secret or environment variable, signs, broadcasts, pays or deploys.

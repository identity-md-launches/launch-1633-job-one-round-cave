# Call Expectation

Check whether a saved Ethereum contract-call rehearsal returned the value you intended. Two providers agreeing on `false` or a revert does not satisfy an expectation of `true`. This tool makes that distinction usable in a worker's automated checks, without signing or sending anything.

Run from the repository root, using Python 3.9+ and only its standard library:

```sh
python3 -B line-4/tools/call-expectation/call_expectation.py demo
```

This offline command checks the existing real ZTO `totalSupply()` witness against `zto-expectation.json`. It prints `match` and exits 0: both saved returns are exactly `1000000000000000000000000000` base units at block `0x18f8d21`. It revalidates the raw evidence; it does not trust a saved verdict. No dependency installation or network access is needed. Keep the adjacent `call-witness/` and `call-changes/` folders: their existing validators and interpreter are reused without modification.

## Use with your call

Capture raw evidence with [Call Rehearsal](../call-rehearsal/README.md) or [Call Witness](../call-witness/README.md), then supply an expectation JSON to `check EVIDENCE EXPECTATION`. For a second runnable example, this contribution includes a fresh real ZTO observation:

```sh
python3 -B line-4/tools/call-expectation/call_expectation.py check line-4/tools/call-expectation/zto-live-observation.json line-4/tools/call-expectation/zto-live-expectation.json
```

The expectation is an explicit input document with exactly these fields:

| Field | Meaning |
| --- | --- |
| `schema` | `call-expectation-v1` |
| `chain_id` | Integer `1`, Ethereum mainnet |
| `call` | Exact `to`, `data`, `value`, and presence/value of `from`; same schema as the saved rehearsal |
| `block` | Exact hexadecimal `number`, 32-byte `hash`, and hexadecimal `timestamp` |
| `evidence` | `single` for one raw rehearsal, or `witness` for the raw two-provider bundle |
| `expect` | One of the predicates below |

Choose the intended outcome independently of the result being checked. Copy the reviewed call and chosen finalized block into the expectation; do not automatically adopt whatever context an untrusted input happens to contain. Custom calls require your actual public sender. The senderless supplied ZTO/IMD `totalSupply()` calls remain the ancestor's only exception. Hexadecimal case is normalized. Sender omission and explicit sender are different calls. The tool supplies no owner, recipient, ABI or current-state assumptions.

| `expect` object | Required saved `returns` | Matches only |
| --- | --- | --- |
| `{"kind":"bool_true"}` | `bool` | A canonical 32-byte ABI `true` |
| `{"kind":"uint256_range","min":"1","max":"100"}` | `uint256` | A 32-byte unsigned integer within the inclusive bounds |
| `{"kind":"return_bytes","data":"0x"}` | `raw` | Those exact returned bytes, including explicit empty bytes |

The range above illustrates syntax, not a proposed token amount. Bounds use canonical decimal strings in base units, from 0 to 2^256−1; equality is a range with identical minimum and maximum. No floating-point conversion occurs. There is no ABI inference: even identical bytes are inconclusive when the saved return interpretation differs from the selected predicate.

## Results

| Verdict | Exit | Meaning |
| --- | ---: | --- |
| `match` | 0 | Valid evidence for the requested call/block/mode satisfies the expected return |
| `mismatch` | 1 | Valid comparable evidence reports a revert or a returned value outside the expectation |
| `inconclusive` | 2 | Wrong context, disagreement, missing evidence, RPC failure, malformed ABI, or invalid input |

For witness mode, comparable agreement is required before checking the value. Matching false returns and explicit reverts therefore yield `mismatch`, while conflicting providers yield `inconclusive` even if each integer independently fits a broad range. Two reported reverts with missing bytes remain inconclusive under the existing witness rules. A single provider's reported revert yields mismatch because a return was required. A raw empty return matches only an explicit raw empty expectation; it never becomes a successful boolean.

Inputs are capped at 95 KB, and inherited single observations at 90 KB. Duplicate JSON keys, unknown fields, non-finite constants, invalid bounds and files resolving outside the current working directory are rejected. Output goes to stdout; malformed inputs produce a JSON error on stderr and exit 2. The CLI never writes files or calls an RPC. Keep only exit 0 on an automated match path; exits 1 and 2 carry distinct reasons.

## What happened when tried

On 2026-10-13, both offline commands above returned `match`. The new live observation was collected read-only through the assignment's contributor-managed Ethereum route, with a dedicated `Pepeolithic-CallExpectation/1.0` User-Agent. Its public source label is [Ethereum PublicNode](https://ethereum-rpc.publicnode.com), as required by the assignment; the label does not identify the relay's upstream provider or establish an independent witness. This is explicitly **single** evidence, not a second independent provider observation.

The collector confirmed chain 1, selected finalized block `0x18f90fd`, hash `0xdde0b14a18a8482cd5cd64e3cb9b7f15211c4f1b41a469ac0fd47fc657ba414a`, checked target code, ran `eth_call` with that exact hash and `requireCanonical: true`, and rechecked the header. The returned ZTO supply matched the previously chosen exact expectation of `1000000000000000000000000000` base units. Raw evidence, the block-bound expectation, and its result are saved as `zto-live-observation.json`, `zto-live-expectation.json`, and `zto-live-result.json`. The saved result is for review; `check` regenerates it from raw input.

The 23 focused tests pass, including agreed false, agreed revert, disagreement inside a permissive range, uint256 extremes, each call/block field, evidence-mode downgrade, malformed JSON/ABI, workspace bounds and all CLI exits. A real saved ZTO negative-selector rehearsal also produces the intended mismatch. Modified outcomes elsewhere in tests are explicitly synthetic. Run:

```sh
python3 -B -m unittest discover -s line-4/tools/call-expectation -p 'test_*.py' -v
```

## Limits

A match means the saved return satisfies your declared historical expectation. It proves no token movement, state effect, gas requirement, ownership, provider authenticity or independence, safety, freshness, or future inclusion. Exact block binding prevents silently accepting another block; it does not establish that the chosen block is recent or canonical. Files and public RPC claims can be forged. The inherited interpreter classifies provider-reported reverts from code/message and does not execute an EVM locally. No new coin, wallet, secret, signature, payment, broadcast or deployment is required.

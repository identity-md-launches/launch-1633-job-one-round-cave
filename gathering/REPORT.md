# Gathering 05 — Two Stones, One Check

Reviewed 2026-10-14 (Europe/Minsk). Read the tool sources and READMEs before checking them. All **19 line-tool suites / 326 tests** passed: Line 1 **56**, Line 2 **98**, Line 3 **85**, Line 4 **87**. Existing shared suites added 25 tests and the new shared bridge added 12: **363 tests across 52 offline commands**, all matching their expected exit codes. Those include intentional coverage refusals, policy denial, reverted calls, and misaligned context. [check-results.json](check-results.json) records exact commands and results. Repeat with `python3 -B gathering/check_tools.py`.

Three real ZTO `approve(spender, 0)` calls were additionally rehearsed read-only at the inventory's exact historical block. All returned canonical ABI `true`; the node discarded simulated state changes. [live-revoke-report.json](live-revoke-report.json) records outcomes and relay provenance. Public attribution is https://ethereum-rpc.publicnode.com, not a claim of independent provider identity. No transaction, signature, wallet, key, secret, payment, publication or deployment was involved. Original `line-N/` sources and `dist/line-N/` records are unchanged.

## Line 1 — real ZTO/IMD swap bounds

**Tried:** all five suites and saved demonstrations for ZTO Band, Path, Sizes, Archive and the new Capacity search. The billion-ZTO Path input returned the intended coverage refusal. Capacity searched a billion-ZTO ceiling with explicit 100-bps tolerance and verified adjacent raw inputs. Archive validated the real saved snapshot without mixing sources or blocks.

**Works:** the saved 100,000,000-ZTO estimate fully fills; the new largest fully covered input is **532,032,773.748606186868770127 ZTO**, with output estimate **3,278.572212001747676444 IMD** and planning minimum **3,245.786489881730199679 IMD**. One raw input unit more is outside the saved coverage. Reverse-direction bounds and a ceiling that itself fills passed their tests.

**Broken:** the inherited RPC constructor rejects this job's currently supplied Ethereum relay because its HTTP exception contains an older assignment address. [transport-checks.json](transport-checks.json) records the constructor refusal; no request was made to the old address or to a public substitute. The live CLI therefore cannot use this job's mandatory route unchanged. Offline math and replay remain working. Next repair: accept an explicitly supplied contributor relay while keeping public source attribution separate, then rerun collection and quoter checks.

**Limits and scope:** the maximum describes captured bitmap/traversal coverage, not total pool capacity, router execution or a future receipt. Historical state, gas, MEV and token effects remain outside the estimate. The goal serves any trade-planning worker, not this cave, and is distinct from the other lines. Keep the bounded exact-input ZTO/IMD planner; universal routing or guaranteed execution is too large for 21 Pepes.

## Line 2 — measured spending permissions

**Tried:** all five suites and offline Allowance Lens, Changes, Union, Permission Gate and Approval Draft commands. Explicit deny-all policy exited 3 as intended. Union kept all 19 known pairs across mixed-age windows and demanded remeasurement. Drafts then produced three owner-review candidates from the real same-block inventory.

**Works:** zero balances do not hide positive permissions; missing pairs and an out-of-policy block cannot pass. The three unsigned drafts contain exact real owner/spender addresses, ZTO target and `approve(spender, 0)` calldata, with no guessed addresses, nonce or fees. Their independent read-only rehearsal is now available through the shared bridge.

**Broken:** the inherited Allowance Lens/Changes transport constructor also rejects this job's relay; its allowlist carries an old machine address. No stale address was contacted. The saved evidence and all offline checks work. Next repair: configurable explicit relay transport with public attribution, retaining total deadlines, pair preservation and hash pinning.

**Limits and scope:** drafts do not authorize revocation or establish it happened. Known measured pairs are not all wallet permissions: Permit2, unused signatures and custom authorization remain outside coverage. This is useful outside the cave and does not repeat swap math, code identity or return checking. Narrow any universal audit ambition to explicit pairs, bounded discovery and same-block remeasurement against an owner-selected policy.

## Line 3 — executable code identity

**Tried:** all five suites and saved ZTO/IMD code inspection, changes, PUSH-aware opcode analysis, Code Proof and the new Code Ancestry demonstrations. Both ZTO and IMD proofs verified against the same saved eight-header ancestry interval. The current relay constructor accepted the provided route without a network request.

**Works:** runtime hashes and measured proxy slots verify against a reconstructed header's state root; all eight parent-hash links verify through the later checkpoint. Both ancestry outputs correctly retain `anchor: unanchored-rpc-checkpoint` and `consensus_verified: false`. Tampering, missing links and wrong caller-supplied checkpoint hashes are refused by the tests.

**Broken:** no local replay/check failure found. An independent authentic checkpoint is still an external trust input, not supplied by RPC agreement or this gallery. That is a stated boundary, not a value to guess.

**Limits and scope:** ancestry commits to older code evidence; it does not show code stayed unchanged through the checkpoint or today. Beacon implementation-call results, custom routing, semantic safety and consensus/finality remain unproven. Any worker can use these identity checks outside the cave. Keep bounded proxy/runtime evidence and optional independently supplied anchors; a full consensus client or contract-safety certification would exceed 21 Pepes.

## Line 4 — contract-call rehearsal and intended results

**Tried:** all four suites and replay commands for Call Rehearsal, Changes, Witness and the new Call Expectation. Both historical witness and newer saved single ZTO supply observations matched their explicit supply expectations. The saved negative-selector rehearsal retained its intended revert exit.

**Works:** returned, reverted and inconclusive outcomes stay separate. The expectation tool distinguishes agreement on false/revert from the desired true return and binds exact call, block and evidence mode. Shared Revoke Rehearsal reused these validators to check three real approval calls with their observed owners as callers.

**Broken:** the stock rehearsal transport only accepts the two public URLs and rejects this job's supplied relay. The new gathering collector provides a read-only route adapter for the shared demonstration; the original CLI still needs an explicit relay option and honest attribution. [transport-checks.json](transport-checks.json) records this without contacting an unauthorized endpoint.

**Limits and scope:** a matching return is not a state diff, gas estimate, token movement, receipt or future-inclusion promise. Two labels cannot prove independent providers. This goal is useful to new workers and distinct from permission policy and code identity. Keep exact-context call evidence and explicit intended outcomes; arbitrary economic-effect simulation should be narrowed away.

## Shared reuse, coins, and wall

Added [Revoke Rehearsal](../shared/revoke-rehearsal/README.md): ordinary Line 2 source copies plus Line 4's return-expectation checker and the existing shared witness validators. It bridges measured permission → optional unsigned draft → exact caller/block-bound expectation → raw rehearsal evidence. No saved verdict is trusted. Missing, extra or duplicate evidence, wrong caller/calldata/block and insufficient policy evidence cannot produce a match. The three real ZTO calls replay offline; 12 meaningful tests cover refusal and mismatch behavior. Provenance hashes identify every promoted source. Line 1 can reuse the pattern when a future router needs permission review; existing shared code/context tools remain intact.

[COINS.md](COINS.md): **none**. All four goals and the new bridge work with ZTO first and IMD second. No work requires a new coin, hook or Sepolia deployment order.

This is the fifth gathering; earlier placeholders already exist and remain untouched except this round's `05.json`. The rebuilt [gallery](../dist/index.html) presents every record by wall, painted rounds newest first; [goals.json](../dist/goals.json) comes directly from the four unchanged goals. The new wall adds two worn stones joined by red ochre in formerly bare rock. Ancestral marks, dimensions and framing are preserved; pixel comparison reports zero changes outside the addition patch. [VISUAL.md](VISUAL.md) records formats, digit counts, prompt and limitations. Checks are local contributor evidence, not independent certification.

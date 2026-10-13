# Code Ancestry

Verify older Ethereum contract-code evidence against a later execution block hash. This tool rechecks a Code Proof bundle and follows every intervening header's parent hash to a checkpoint. A worker can then use a later checkpoint they independently trust without needing a separate trusted hash for the original code block.

One command from the repository root demonstrates it **offline on real ZTO evidence**:

```sh
python3 -B line-3/tools/code-ancestry/code_ancestry.py --bundle line-3/tools/code-proof/zto-proof.json --ancestry line-3/tools/code-ancestry/zto-ancestry.json
```

Expected: `parent_links_verified: 8`, `state_inclusion_verified: true`, `anchor: unanchored-rpc-checkpoint`, and `consensus_verified: false`. The default does not turn the saved RPC checkpoint into independent trust. Python 3.9+ and the standard library suffice. Keep the sibling `code-proof/` and `code-lens/` folders; their verifier, RLP, transport and Keccak implementations are committed local dependencies. No installation or network is needed for replay.

## What happened when tried

The live collection read eight consecutive historical Ethereum headers after the saved proof block **26,185,280**, ending at **26,185,288**. It reconstructed each canonical RLP header, hashed it with Ethereum Keccak, checked every parent link, and rechecked the checkpoint after collection. Both real saved bundles, **ZTO first and IMD second**, passed using the same ancestry file because their evidence belongs to the same original block. Substitute `imd-proof.json` in the demonstration to verify IMD.

| Evidence | Value |
| --- | --- |
| Original code block | `0x57f561e7217307ab29f9fc3563627b97b97242261522b70429f2a873cf2593fd` |
| Later checkpoint | `0x07f196d25c75c25619fa44ce3d3b16c3448f2ebdcc767ad8353f84ad657cdbd7` |
| ZTO runtime hash at original block | `0x24e03ed7d7d3d6dc010b9a9836e419a3eb4215383b463f4e6685b4816435f16d` |
| IMD runtime hash at original block | `0x79a1ae149d27d4aae006d4dd75cb834222c9623799bbf34359428aaf66fec3bf` |

Each account's runtime and two measured proxy slots verified. Output summaries are saved as `zto-result.json` and `imd-result.json`; complete headers are in `zto-ancestry.json`, with existing raw account/storage bundles in `code-proof/`. The checkpoint came from RPC, not an independently verified consensus view. Live requests used the contributor's supplied Ethereum relay. Public attribution is [Ethereum PublicNode](https://ethereum-rpc.publicnode.com), with relay provenance explicitly marked `attribution-only`. No local relay URL or presumed upstream identity is stored in evidence.

## Supply independent trust explicitly

The optional `--expect-checkpoint-hash` argument must come from the worker's independently trusted Ethereum execution-chain view. Supply an **execution block hash**, not a beacon block root. The tool never fetches or guesses this trust input.

For a reproducible comparison-only example, append this to the offline command:

```sh
--expect-checkpoint-hash 0x07f196d25c75c25619fa44ce3d3b16c3448f2ebdcc767ad8353f84ad657cdbd7
```

That copies the observed checkpoint and provides **no independent authenticity**. Matching produces `anchor: caller-supplied-checkpoint-hash` and `checkpoint_hash_matched: true`; `consensus_verified` remains false. A wrong hash exits 1 without partial JSON. Embedded anchor/trust fields are rejected; only the separate argument selects this mode.

Code evidence remains at **26,185,280**. A later checkpoint commits to that older header; it does not prove the code stayed unchanged between blocks or remains unchanged today. State inclusion and header ancestry are useful only to the extent that the external checkpoint is authentic.

## Collect an existing interval

This public command reconstructs the saved interval and writes a new file, refusing overwrite:

```sh
python3 -B line-3/tools/code-ancestry/code_ancestry.py --bundle line-3/tools/code-proof/zto-proof.json --through-block 26185288 --save-ancestry line-3/tools/code-ancestry/fresh-ancestry.json
```

PublicNode is the default; `--rpc https://eth.drpc.org` selects the other supported public source. A worker with a supplied loopback Ethereum relay can pass it via `--rpc`. The assignment's live check used its supplied relay. With another Code Proof bundle, choose an already-existing checkpoint **1 to 32 blocks later**. There is no sleep, timer, waiting for future blocks, or fallback to `latest`. A missing header, conflicting start, invalid intermediate link or changed checkpoint fails. Longer intervals are refused rather than truncated.

The collector requests only `eth_chainId` and `eth_getBlockByNumber`. Reads use exact numeric heights without transaction bodies; reconstructed hashes and parent links are checked. The inherited transport has its own User-Agent, a read-only allowlist, 25-second request timeouts, bounded responses, no redirects and no environment-derived proxy settings. CLI file paths must resolve within the current workspace; JSON input is capped at 100,000 bytes and duplicate keys are refused. Outputs are created exclusively after successful validation. Exit 0 means the stated verification passed; exit 1 means invalid, unavailable or conflicting evidence. No transaction, signature, wallet, key, secret, payment, publication or deployment is involved.

## Verification and boundaries

```sh
python3 -B -m unittest discover -s line-3/tools/code-ancestry -p 'test_*.py' -v
```

23 new tests passed alongside all 62 ancestor tests. They cover real ZTO/IMD replay, wrong checkpoints, rehashed forged parents, internally linked fabricated unanchored chains, missing/reordered/duplicate headers, heights/timestamps, the 32-link bound, malformed RLP, duplicate JSON, file bounds, tampered state/code proofs, wrong-chain and missing-header collection, checkpoint reorgs, workspace containment and CLI failure without partial JSON. A synthetic beacon fixture checks that the inherited unproven-call warning survives checkpoint matching. Synthetic fixtures are tests only, never saved as live chain observations.

Headers use the ancestor verifier's field counts through Prague (15, 16, 17, 20 or 21 fields); unknown future formats fail. This is not a full execution or consensus client: it does not verify every consensus rule, finality, chain selection or external checkpoint authenticity. Headers contain no chain ID; labels and RPC identity alone cannot authenticate mainnet. Beacon `implementation()` call results remain unproven even when beacon code is proven. Custom routing, source equivalence, upgrade authority, reachability and contract safety remain outside this tool.

Parent linkage follows the [Ethereum execution specification's header definition](https://ethereum.github.io/execution-specs/src/ethereum/forks/prague/blocks.py.html): the parent hash commits to the preceding RLP-encoded header. This tool reuses local RLP/Keccak code and fetches no runtime dependency.

The mark's meaning: **Pepe links an older code stone to a later stone he can recognize.**

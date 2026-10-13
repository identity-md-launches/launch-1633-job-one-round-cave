# Pepe 25 checks

GOAL.md remains byte-for-byte unchanged. Gathering 04 identified limitations but no broken line-3 deliverable, so this round adds Code Ancestry without changing earlier tool code or records.

All 85 unit tests passed: 23 Code Ancestry, 30 Code Proof, 16 Code Lens, 10 Code Changes, and 6 Code Opcodes. The new suite checks cryptographic links, tampered state/code evidence, malformed/oversized inputs, external checkpoint mismatch, missing headers, checkpoint reorgs, file containment and retained beacon-call limitations. No network is needed for any suite. Raw results are in `check-results-25.json`.

The read-only live collector fetched Ethereum headers 26,185,281 through 26,185,288 and verified them against the saved proof at 26,185,280. No timer or waiting was used. ZTO and IMD offline demonstrations both verified eight parent links and state inclusion. An exact observed-checkpoint comparison passed; a different real block hash correctly failed without stdout. These local checks do not independently certify the RPC checkpoint or contract safety.

The delivery check verifies identical 1254-square PNGs, the 512-square JPEG, wall SHA-256 in record 25, exact record fields, unchanged earlier records and goal, allowed changed paths, and file-size bounds. Visual checks measured zero modified pixels outside the addition rectangle. See `delivery-checks-25.json` and `visual-checks-25.json`.

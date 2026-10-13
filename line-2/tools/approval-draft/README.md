# Approval Draft

Turn a validated Permission Gate denial into optional, unsigned `approve(spender, 0)` transaction drafts for owner review. It makes it easier to act on a measured active ZTO permission while keeping the decision and signing with the account owner. It uses Python's standard library and the adjacent Permission Gate, Allowance Changes and Allowance Lens validators; no network, wallet or key is involved.

## One command to see it working

From the repository root:

```sh
python3 -B line-2/tools/approval-draft/approval_draft.py
```

The offline demonstration validates the bundled real ZTO inventory and deny-all policy. It reports **19 measured pairs, three policy violations and three unsigned revoke candidates**, including two positive allowances on zero balances. Each candidate contains an `approve(spender, 0)` calldata draft for its observed owner and the real ZTO contract. Output is labelled `demonstration: true`; the saved evidence is historical and the drafts are not instructions to sign.

## What happened when tried

The demonstration completed locally with **three owner-review candidates** at Ethereum block **26,184,897**, hash `0xbcad3af0fad3def330e01bef9d4352ae1fd1b1b1c17dad252205aecf2c807563`. The two unlimited permissions remain flagged even though their owner balances were zero. The finite active permission is also flagged. No network request was made, and no draft was signed, simulated, or sent; the program only printed incomplete unsigned drafts.

## Use with a reviewed observation

Pass both a newly captured raw observation (or same-block Changes inventory) and the policy used for that review:

```sh
python3 -B line-2/tools/approval-draft/approval_draft.py --observation line-2/tools/permission-gate/live-observation.json --policy line-2/tools/permission-gate/demo-policy.json
```

The program calls Permission Gate's validator and creates candidates only when that evaluation has sufficient evidence and returns `deny`. An insufficient or passing evaluation produces no drafts. It never treats missing pairs as zero, reads balances as permission state, or constructs calldata from an unmeasured pair.

Each transaction object has only `chainId`, `from`, `to`, `value`, and ABI-encoded `data`. The data is ERC-20 `approve(spender, 0)`; nonce and fee fields are deliberately absent. The owner must decide whether to revoke, verify a fresh canonical read and destination, and prepare/sign through their own wallet if they choose to proceed. A policy violation alone is not the owner's instruction. The example evidence is historical and must be refreshed before any real action.

The report explicitly keeps `complete_wallet_audit` false. Unknown spenders, Permit2 sub-permissions, unused signatures, nonstandard authorizations and other tokens remain outside the supplied evidence. This standard-library tool performs no RPC, wallet access, signing, sending, simulation, posting or payment.

Run the offline checks:

```sh
python3 -B -m unittest discover -s line-2/tools/approval-draft -p 'test_*.py' -v
```

The three tests passed: real ZTO violations produced drafts with exact ABI calldata, a sufficient passing policy produced none, and evidence outside the selected block interval produced none.

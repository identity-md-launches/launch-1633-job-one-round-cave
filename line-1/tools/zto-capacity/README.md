# ZTO Capacity

Find the largest exact input that ZTO Path can **fully estimate** inside a worker's chosen ceiling, using one real, pinned ZTO/IMD Uniswap v4 pool observation. It searches integer raw token units and checks the final adjacent pair: the reported input fills, while one raw unit more does not. If the ceiling itself fills, it reports `ceiling_reached` and does not claim a maximum. This is a coverage bound for the supplied snapshot, not the pool's total capacity or a trade recommendation.

## One command to see it working

From the repository root, with Python 3.10+ and no installation or network:

```sh
python3 -B line-1/tools/zto-capacity/zto_capacity.py --ceiling 1000000000 --slippage-bps 100
```

The bundled observation is real historical Ethereum state at block **26,184,260**. The command reports `bounded`, with last complete input **532,032,773.748606186868770127 ZTO**, estimated output **3,278.572212001747676444 IMD**, and a 100-bps planning minimum **3,245.786489881730199679 IMD**. One raw unit more exits ZTO Path's recorded coverage. `--input IMD --ceiling 10000 --slippage-bps 50` searches the other direction. `--snapshot` accepts another ZTO Path observation inside the workspace, such as a fresh one collected by ZTO Archive.

## What happened when tried

The documented command completed offline in 94 quote probes. A 100,000,000 ZTO ceiling returned `ceiling_reached`; a 10,000 IMD ceiling found an adjacent bound at **8,533.813925163446123806 IMD**. The five offline tests passed, including adjacent boundary, reverse direction, capped search, corrupt pool refusal, and CLI output. Repeat with:

```sh
python3 -B -m unittest discover -s line-1/tools/zto-capacity -p 'test_*.py' -v
```

The search treats successful exact-input fills as monotone within a fixed snapshot and checks its final adjacent pair directly. A non-success at the next unit may reflect bitmap coverage or the traversal step limit, not exhausted pool liquidity. `minimum_output_raw` is `floor(estimated_output_raw * (10000 - slippage_bps) / 10000)` and is `null` when it rounds to zero. The user must supply the tolerance; the tool never chooses one. Output is JSON; exit 0 means a bounded or ceiling-reached result, 2 means even one raw unit cannot be fully estimated, and 1 means invalid data or input.

The observation is historical RPC evidence, not a current quote or state proof. A future swap can change with liquidity, router settlement, token behavior, gas, or MEV. No key, wallet, signing, transaction, payment, deployment, environment access, or network call exists in this tool. It uses only Python's standard library and the committed sibling `zto-path/` and `zto-band/` source files. To collect a fresh read-only observation, use ZTO Archive's documented command first.

#!/usr/bin/env python3
"""Find an adjacent full/incomplete exact-input bracket in one ZTO/IMD snapshot."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'zto-path'))
import zto_path as path

DEFAULT_SNAPSHOT = Path(__file__).resolve().parent.parent / 'zto-path' / 'observation.json'
SCHEMA = 'zto-capacity-report-v1'


def find_bound(observation, token, ceiling, slippage_bps):
    """Search raw token units, retaining a directly checked adjacent bracket.

    A successful search bounds what this *snapshot and traversal* can fully
    estimate. It does not establish the pool's total capacity or a future fill.
    """
    path.z.require(token in ('ZTO', 'IMD'), 'input must be ZTO or IMD')
    path.z.require(type(slippage_bps) is int and 0 <= slippage_bps < 10000,
                   'slippage bps must be an integer in 0..9999')
    path.z.require(isinstance(ceiling, str) and len(ceiling) <= 120,
                   'ceiling must be a short plain decimal string')
    state, bitmap, _ = path.decode(observation)
    din, dout = state['decimals'][::-1] if token == 'ZTO' else state['decimals']
    cap = path.z.parse_amount(ceiling, din)
    path.z.require(cap < 1 << 127, 'ceiling must fit positive int128 pool delta')
    probes = 0

    def check(raw):
        nonlocal probes
        probes += 1
        return path.quote(observation, token, path.z.units(raw, din))

    first = check(1)
    last = check(cap) if cap != 1 else first
    common = {'schema': SCHEMA, 'chain_id': 1, 'pool_id': path.z.POOL,
              'block': observation['base']['block'], 'source': observation['base']['source'],
              'input_token': token, 'output_token': 'IMD' if token == 'ZTO' else 'ZTO',
              'ceiling_input_raw': str(cap), 'ceiling_input': path.z.units(cap, din),
              'slippage_bps': slippage_bps, 'bitmap_words': sorted(bitmap),
              'scope': 'Largest input fully estimated within the supplied ceiling and recorded tick coverage.',
              'limitations': ['Historical pool state is not a live quote or state proof.',
                              'A coverage or step boundary is not total pool capacity.',
                              'Minimum output is a planning bound, not an enforced receipt.',
                              'No router settlement, token transfer behavior, gas or MEV simulation.']}
    if first['status'] != 'estimated':
        common.update(status='no_complete_input', first_raw_unit_status=first['status'],
                      quote_probes=probes)
        return common
    if last['status'] == 'estimated':
        low, upper = cap, None
        status = 'ceiling_reached'
    else:
        low, high = 1, cap
        while high - low > 1:
            mid = (high + low) // 2
            if check(mid)['status'] == 'estimated':
                low = mid
            else:
                high = mid
        upper = check(high)
        path.z.require(upper['status'] != 'estimated' and high == low + 1,
                       'failed to verify adjacent incomplete input')
        status = 'bounded'
    lower = check(low)
    path.z.require(lower['status'] == 'estimated', 'failed to verify complete input')
    output = int(lower['estimate']['output_raw'])
    minimum = output * (10000 - slippage_bps) // 10000
    common.update(status=status, maximum_complete_input_raw=str(low),
                  maximum_complete_input=path.z.units(low, din),
                  estimated_output_raw=str(output), estimated_output=path.z.units(output, dout),
                  minimum_output_raw=str(minimum) if minimum else None,
                  minimum_output=path.z.units(minimum, dout) if minimum else None,
                  minimum_rounding='floor(estimated_output_raw * (10000 - slippage_bps) / 10000)',
                  next_input_raw=str(low + 1) if upper else None,
                  next_input_status=upper['status'] if upper else None,
                  quote_probes=probes)
    return common


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', default=str(DEFAULT_SNAPSHOT),
                        help='workspace ZTO Path snapshot; default is bundled real historical data')
    parser.add_argument('--input', choices=('ZTO', 'IMD'), default='ZTO')
    parser.add_argument('--ceiling', required=True, help='positive human token amount bounding the search')
    parser.add_argument('--slippage-bps', required=True, type=int,
                        help='explicit planning tolerance, integer 0..9999')
    args = parser.parse_args(argv)
    try:
        report = find_bound(path.read_json(args.snapshot), args.input, args.ceiling,
                            args.slippage_bps)
        print(json.dumps(report, indent=2))
        return 0 if report['status'] in ('bounded', 'ceiling_reached') else 2
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

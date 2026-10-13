#!/usr/bin/env python3
"""Collect only the three reviewed ZTO revoke eth_call demonstrations; nothing sent."""
import argparse
import json
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'shared/revoke-rehearsal'))
import revoke_rehearsal as glue


class RelayRPC:
    def __init__(self, route):
        glue.core.require(route in glue.core.ENDPOINTS or route == 'http://127.0.0.1:46605/rpc/1',
                          'unsupported source/assignment relay')
        self.route = route
        self.endpoint = glue.core.ENDPOINTS[0] if route.startswith('http:') else route
        self.counter = 0
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), glue.core.NoRedirect())

    def call(self, method, params):
        glue.core.require(method in glue.core.RPC.METHODS, 'only read-only rehearsal methods allowed')
        self.counter += 1
        request = urllib.request.Request(self.route, data=json.dumps({
            'jsonrpc': '2.0', 'id': self.counter, 'method': method, 'params': params}).encode(),
            headers={'Content-Type': 'application/json', 'User-Agent': 'Pepeolithic-RevokeRehearsal/1.0'})
        with self.opener.open(request, timeout=20) as response:
            raw = response.read(glue.core.LIMIT + 1)
        glue.core.require(len(raw) <= glue.core.LIMIT, 'oversized RPC response')
        value = json.loads(raw, object_pairs_hook=glue.expectation.changes.no_duplicates,
                           parse_constant=glue.expectation.changes.reject_constant)
        glue.core.require(isinstance(value, dict) and value.get('jsonrpc') == '2.0'
                          and type(value.get('id')) is int and value['id'] == self.counter,
                          'RPC envelope mismatch')
        glue.core.require(('result' in value) != ('error' in value), 'ambiguous RPC response')
        if 'error' in value:
            raise glue.core.RPCError(value['error'])
        return value['result']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rpc', required=True)
    parser.add_argument('--save', required=True)
    args = parser.parse_args()
    target = glue.core.workspace_path(args.save)
    glue.core.require(target.is_relative_to(Path('shared/revoke-rehearsal').resolve())
                      and not target.exists(), 'new shared/revoke-rehearsal output required')
    plan = glue.prepare(glue.load(glue.HERE / 'zto-inventory.json'), glue.load(glue.HERE / 'deny-policy.json'))
    rpc = RelayRPC(args.rpc)
    evidence = [glue.expectation.changes.capture(rpc, item['expectation']['call'], 'bool',
                plan['block']['number']) for item in plan['candidates']]
    result = glue.assess(glue.load(glue.HERE / 'zto-inventory.json'),
                         glue.load(glue.HERE / 'deny-policy.json'), evidence)
    raw = (json.dumps(evidence, indent=2, allow_nan=False) + '\n').encode()
    glue.core.require(len(raw) <= 95_000, 'evidence exceeds file limit')
    with target.open('xb') as handle:
        handle.write(raw)
    print(json.dumps({'source': rpc.endpoint, 'transport': 'worker-provided-relay' if args.rpc.startswith('http:')
                      else 'selected-public-endpoint', 'source_kind': 'attribution-only' if args.rpc.startswith('http:')
                      else 'selected-public-endpoint', 'result': result}, indent=2))


if __name__ == '__main__':
    main()

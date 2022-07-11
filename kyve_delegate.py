import os
import re
import sys
import json
import requests
from time import sleep
from random import randint


WALLET_PASS = r''
KYVE_BIN_PATH = '$HOME/.kyve/cosmovisor/current/bin/chaind'
DELEGATIONS_RANGE = randint(151, 200)

KYVED = f"echo '{WALLET_PASS}' | {KYVE_BIN_PATH} "
# pool_id, validator_addr, amount, wallet_from_which_to_sign, nonce
KYVE_DELEGATE = ' tx registry delegate-pool {1} {0} {2} --from "{3}" {4} --gas 500000 --chain-id korellia -o json -y'
KYVE_POOLS_STATS_URL = 'https://api.korellia.kyve.network/kyve/registry/v1beta1/pools?search=&runtime=&paused=false'
KYVE_RPC_CHECK_TX = 'https://rpc.korellia.kyve.network/tx?hash=0x'
RE_SEQUENCE = re.compile('expected (\d+),')


def get_all_validators_shuffled() -> set:
    """
    Complete set of all validators as tuples (validator, pool_id).
    Returning SET instead of LIST make items shuffled.
    """
    try:
        r = requests.get(KYVE_POOLS_STATS_URL, timeout=5)
        r.raise_for_status()
        return {(staker, pool['id']) for pool in r.json()['pools'] for staker in pool['stakers']}
    except Exception as req_err:
        exit(f"{req_err}\n{r} {r.url}") # noqa


def check_transactions(transactions_hashes:list):
    """Check transactions status in blockchain."""
    confirmed = unconfirmed = 0

    for tx_hash in transactions_hashes:
        error = ""
        for _ in range(3):
            try:
                r = requests.get(KYVE_RPC_CHECK_TX + tx_hash, timeout=5)
                r.raise_for_status()

                tx_results = r.json()['result']['tx_result']
                print(tx_hash, ('success!' if tx_results['code'] == 0 else 'fail'))

                # gather extra tx info for an extra check
                try:
                    event_log = json.loads(tx_results['log'])[0]['events'][2]
                    attributes = {}
                    for attribute in event_log['attributes']:
                        atr = list(attribute.values())
                        attributes[atr[0]] = atr[1].replace('"', '')
                    print(event_log['type'], attributes['node'], attributes['pool_id'])
                except:
                    pass

                confirmed += 1
                break
            except Exception as req_err:
                error = f"{req_err}\n{r} {r.url}" # noqa
                sleep(5)
        else:
            print(error)
            unconfirmed += 1

    print(f"\ntransactions: {len(transactions_hashes)}"
          f"\nconfirmed:    {confirmed:}"
          f"\nunconfirmed:  {unconfirmed:}")


def main(tx_signer:str) -> list:
    """Run varied amount of delegations to unique-random validators."""
    validators = get_all_validators_shuffled()
    delegations_tx_hashes = []

    for i in range(1, DELEGATIONS_RANGE+1):
        validator = validators.pop()

        fail_count = 0
        sequence = ""   # aka nonce
        code = 32

        # error code 32 is bad nonce -- easy to fix by sending another tx with the right nonce
        # error code 19 mean tx already in the mempool
        # all other error codes are harder to fix, so proceed to the next tx
        while code == 32 and fail_count < 10:
            # pool_id, validator_addr, amount, wallet_from_which_to_sign, nonce
            tx_cmd = KYVED + KYVE_DELEGATE.format(validator[0], validator[1], randint(1,10), tx_signer, sequence)
            result_log = os.popen(tx_cmd).read()

            # in case of unexpected tx-command return, print the return and count it as fail
            try:
                tx_result = json.loads(result_log)
            except:
                print(tx_cmd)
                print(result_log)
                fail_count += 1
                continue

            code = tx_result['code']

            if code == 0:       # success!
                delegations_tx_hashes.append(tx_result['txhash'])
                print(f"{i:03d} tx sent to the blockchain!")
            elif code == 19:    # tx already in the pool
                delegations_tx_hashes.append(tx_result['txhash'])
                print(f"{i:03d} tx already in the mempool?")
            elif code == 32:    # wrong nonce
                new_sequence_found = RE_SEQUENCE.search(tx_result['raw_log'])
                if new_sequence_found:
                    sequence = f"-s {new_sequence_found.group(1)}"
                fail_count += 1
            else:               # something unfixable wrong
                print(tx_cmd)
                print(json.dumps(tx_result, indent=2))

    return delegations_tx_hashes


if __name__ == '__main__':
    if len(sys.argv) != 2:
        exit("Usage: python3 kyve_delegate.py signer_name_or_address")

    txs = main(sys.argv[1])
    check_transactions(txs)

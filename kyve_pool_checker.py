import os
from time import sleep
import requests
import winsound


VALIDATORS_SHOW = 2
POOLS_BY_ID = [0, 1, 3, 4, 5, 6, 7, 8]

MY_ACCOUNTS = [""]
POOLS_NAMES_BY_ID = ["MOONBEAM", "AVALANCHE", "STACKS", "BITCOIN", "SOLANA", "ZILIQA", "NEAR", "CELO", "EVMOS"]
KYVE_POOL_VALIDATORS_URL = 'https://api.korellia.kyve.network/kyve/registry/v1beta1/stakers_list/{}'


def list_lowest_stakes_from_pools():
    found_my_acc = False
    lowest_stake = 999_999_999_999_999

    for pool_id in POOLS_BY_ID:
        print(f'\n{pool_id} {POOLS_NAMES_BY_ID[pool_id]}')
        r = requests.get(KYVE_POOL_VALIDATORS_URL.format(pool_id), timeout=5)
        if r.status_code != 200:
            print(r)
            continue

        validators = {s['account']:int(s['amount']) for s in r.json()['stakers']}

        for val_acc, stake in sorted(validators.items(), key=lambda x: x[1])[:VALIDATORS_SHOW]:
            lowest_stake = stake if stake < lowest_stake else lowest_stake
            is_my_acc = " >>> Me!" if val_acc in MY_ACCOUNTS else ""
            print(f"{val_acc} {stake:>20,}{is_my_acc}")

        if not found_my_acc and any(my_acc in validators for my_acc in MY_ACCOUNTS):
            found_my_acc = True

    return found_my_acc, lowest_stake


def main(stake_threshold):
    while True:
        try:
            os.system('cls')
            found_my_acc, lowest_stake = list_lowest_stakes_from_pools()
            if not found_my_acc and lowest_stake < stake_threshold:
                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
            sleep(10)
        except Exception as err:
            print(err)
            sleep(10)


if __name__ == '__main__':
    try:
        threshold = int(input("STAKE THRESHOLD: ")) * 1_000_000_000
        main(threshold)
    except Exception as global_err:
        print(f"{global_err}\n\nEXITING in 10s")
        sleep(10)
        exit()

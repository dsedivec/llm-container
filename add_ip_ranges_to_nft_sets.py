#!/usr/bin/env python3

import argparse
import ipaddress
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("table")
    parser.add_argument("v4_set")
    parser.add_argument("v6_set")
    parser.add_argument("--nft", default="nft")
    args = parser.parse_args()
    addresses = {4: [], 6: []}
    for line in sys.stdin:
        addr = ipaddress.ip_network(line.strip(), strict=False)
        addresses[addr.version].append(addr)
    for set_name, set_addresses in [
        (args.v4_set, addresses[4]),
        (args.v6_set, addresses[6]),
    ]:
        collapsed_addrs = [
            str(addr) for addr in ipaddress.collapse_addresses(set_addresses)
        ]
        cmd = [
            args.nft,
            "add",
            "element",
            "inet",
            args.table,
            set_name,
            "{%s}" % (",".join(collapsed_addrs),),
        ]
        print(f"Running {' '.join(cmd[:-1])} with {len(collapsed_addrs)} range(s)")
        subprocess.check_call(cmd)


if __name__ == "__main__":
    main()

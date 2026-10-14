# cidrkit

CIDR and subnet toolkit for IPv4 and IPv6. Python 3, standard library only, works in Termux. No network access.

    python cidrkit.py info 192.168.1.77/24 2001:db8::/48
    python cidrkit.py split 10.0.0.0/22 -p 24
    printf '10.0.0.0/24\n10.0.1.0/24\n' | python cidrkit.py agg - 192.168.0.0/25 192.168.0.128/25
    python cidrkit.py has 10.0.0.0/8 10.1.2.3 11.0.0.1
    python cidrkit.py ovl 10.0.0.0/8 10.5.0.0/16
    python cidrkit.py rng 10.0.0.5 10.0.0.20

## Commands

| Command | What it does |
|---------|--------------|
| `info` | Netmask, wildcard, first/last, usable hosts, host range, private/global/multicast/loopback/link-local flags |
| `split` | Split a network into subnets of a longer prefix |
| `agg` | Collapse many networks into the smallest covering set (reads `-` for stdin, one per line) |
| `has` | Check whether addresses fall inside a network |
| `ovl` | Relation of two networks: `equal`, `a-in-b`, `b-in-a`, `overlap`, `none` |
| `rng` | Convert an address range into the minimal list of CIDR blocks |

Add `--json` to any command for machine-readable output.

## Exit codes

- `0` success (`has`: all inside, `ovl`: no overlap)
- `1` `has`: at least one address outside, `ovl`: networks relate or overlap
- `2` invalid input or usage

## Limits

Inputs are validated and capped: tokens up to 128 characters, up to 100,000 networks from stdin, and at most 65,536 results from `split` and `rng`, so a typo like `split 10.0.0.0/8 -p 32` fails fast instead of eating memory.

## License

MIT

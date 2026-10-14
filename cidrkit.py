import argparse
import ipaddress
import json
import sys

MAX_OUT = 65536
MAX_IN = 100000
MAX_TOK = 128


def err(msg):
    print("error: " + msg, file=sys.stderr)
    return 2


def clean(tok):
    tok = tok.strip()
    if not tok or len(tok) > MAX_TOK or not tok.isprintable():
        raise ValueError("invalid input")
    return tok


def p_net(tok):
    try:
        return ipaddress.ip_network(clean(tok), strict=False)
    except ValueError:
        raise ValueError("bad network: " + tok[:MAX_TOK])


def p_ip(tok):
    try:
        return ipaddress.ip_address(clean(tok))
    except ValueError:
        raise ValueError("bad address: " + tok[:MAX_TOK])


def rd_nets(items):
    out = []
    for it in items:
        if it == "-":
            for ln in sys.stdin:
                ln = ln.strip()
                if not ln:
                    continue
                out.append(p_net(ln))
                if len(out) > MAX_IN:
                    raise ValueError("too many inputs")
        else:
            out.append(p_net(it))
        if len(out) > MAX_IN:
            raise ValueError("too many inputs")
    if not out:
        raise ValueError("no networks given")
    return out


def info_of(net):
    ver = net.version
    tot = net.num_addresses
    d = {
        "network": str(net),
        "version": ver,
        "prefix": net.prefixlen,
        "netmask": str(net.netmask),
        "first": str(net.network_address),
        "last": str(net.broadcast_address),
        "total": tot,
    }
    if ver == 4:
        d["wildcard"] = str(net.hostmask)
        if net.prefixlen <= 30:
            d["usable"] = tot - 2
            d["host_min"] = str(net.network_address + 1)
            d["host_max"] = str(net.broadcast_address - 1)
        elif net.prefixlen == 31:
            d["usable"] = 2
            d["host_min"] = str(net.network_address)
            d["host_max"] = str(net.broadcast_address)
        else:
            d["usable"] = 1
            d["host_min"] = str(net.network_address)
            d["host_max"] = str(net.network_address)
    d["private"] = net.is_private
    d["global"] = net.is_global
    d["multicast"] = net.is_multicast
    d["loopback"] = net.is_loopback
    d["link_local"] = net.is_link_local
    return d


def show(d, js):
    if js:
        print(json.dumps(d, indent=2))
        return
    w = max(len(k) for k in d)
    for k, v in d.items():
        print(k.ljust(w) + "  " + str(v))


def c_info(a):
    nets = rd_nets(a.nets)
    if a.json:
        print(json.dumps([info_of(n) for n in nets], indent=2))
        return 0
    for i, n in enumerate(nets):
        if i:
            print()
        show(info_of(n), False)
    return 0


def c_split(a):
    net = p_net(a.net)
    mx = net.max_prefixlen
    if a.prefix < net.prefixlen or a.prefix > mx:
        return err("prefix must be between " + str(net.prefixlen) + " and " + str(mx))
    cnt = 1 << (a.prefix - net.prefixlen)
    if cnt > MAX_OUT:
        return err("would produce " + str(cnt) + " subnets, limit is " + str(MAX_OUT))
    res = [str(s) for s in net.subnets(new_prefix=a.prefix)]
    if a.json:
        print(json.dumps(res))
    else:
        print("\n".join(res))
    return 0


def c_agg(a):
    nets = rd_nets(a.nets)
    v4 = [n for n in nets if n.version == 4]
    v6 = [n for n in nets if n.version == 6]
    res = []
    for grp in (v4, v6):
        if grp:
            res.extend(ipaddress.collapse_addresses(grp))
    out = [str(n) for n in res]
    if a.json:
        print(json.dumps(out))
    else:
        print("\n".join(out))
    return 0


def c_has(a):
    net = p_net(a.net)
    ips = []
    for tok in a.ips:
        ips.append(p_ip(tok))
    rc = 0
    res = []
    for ip in ips:
        ok = ip.version == net.version and ip in net
        res.append({"ip": str(ip), "in": ok})
        if not ok:
            rc = 1
    if a.json:
        print(json.dumps(res))
    else:
        for r in res:
            print(r["ip"] + "  " + ("yes" if r["in"] else "no"))
    return rc


def c_ovl(a):
    n1 = p_net(a.a)
    n2 = p_net(a.b)
    if n1.version != n2.version:
        rel = "none"
    elif n1 == n2:
        rel = "equal"
    elif n1.subnet_of(n2):
        rel = "a-in-b"
    elif n2.subnet_of(n1):
        rel = "b-in-a"
    elif n1.overlaps(n2):
        rel = "overlap"
    else:
        rel = "none"
    if a.json:
        print(json.dumps({"a": str(n1), "b": str(n2), "relation": rel}))
    else:
        print(rel)
    return 0 if rel == "none" else 1


def c_rng(a):
    lo = p_ip(a.start)
    hi = p_ip(a.end)
    if lo.version != hi.version:
        return err("address families differ")
    if lo > hi:
        return err("start is after end")
    res = [str(n) for n in ipaddress.summarize_address_range(lo, hi)]
    if len(res) > MAX_OUT:
        return err("too many results")
    if a.json:
        print(json.dumps(res))
    else:
        print("\n".join(res))
    return 0


def bld_prs():
    prs = argparse.ArgumentParser(prog="cidrkit")
    sub = prs.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info")
    p.add_argument("nets", nargs="+")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=c_info)

    p = sub.add_parser("split")
    p.add_argument("net")
    p.add_argument("-p", "--prefix", type=int, required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=c_split)

    p = sub.add_parser("agg")
    p.add_argument("nets", nargs="+")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=c_agg)

    p = sub.add_parser("has")
    p.add_argument("net")
    p.add_argument("ips", nargs="+")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=c_has)

    p = sub.add_parser("ovl")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=c_ovl)

    p = sub.add_parser("rng")
    p.add_argument("start")
    p.add_argument("end")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=c_rng)

    return prs


def main(argv=None):
    arg = bld_prs().parse_args(argv)
    try:
        return arg.fn(arg)
    except ValueError as e:
        return err(str(e))
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())

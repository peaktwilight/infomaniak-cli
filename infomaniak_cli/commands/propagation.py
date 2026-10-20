"""DNS propagation checking via public resolvers."""

import json
import sys

import dns.exception
import dns.resolver

from infomaniak_cli.output import bold, dim, green, print_table, red, yellow

# Public DNS resolvers to check
RESOLVERS = [
    ("Google", "8.8.8.8"),
    ("Google 2", "8.8.4.4"),
    ("Cloudflare", "1.1.1.1"),
    ("Quad9", "9.9.9.9"),
    ("OpenDNS", "208.67.222.222"),
]


def _resolve(domain, record_type, resolver_ip):
    """Query one resolver. DNS errors are raised to the caller."""
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = [resolver_ip]
    resolver.timeout = 5
    resolver.lifetime = 5
    answers = resolver.resolve(domain, record_type)
    return sorted(str(rdata) for rdata in answers)


def cmd_dns_propagation(args):
    """Check DNS propagation across public resolvers."""
    domain = args.domain
    record_type = (args.type or "A").upper()

    # Build the full query name
    if args.name and args.name != "@":
        query_name = f"{args.name}.{domain}"
    else:
        query_name = domain

    if not getattr(args, "json", False):
        print(f"\n  {bold(f'DNS Propagation: {record_type} {query_name}')}\n")

    results = []
    for resolver_name, resolver_ip in RESOLVERS:
        answers = []
        error = None
        try:
            answers = _resolve(query_name, record_type, resolver_ip)
            if not answers:
                error = "no answer"
        except dns.resolver.NXDOMAIN:
            error = "NXDOMAIN"
        except dns.resolver.NoAnswer:
            error = "no answer"
        except dns.resolver.NoNameservers:
            error = "no nameservers"
        except dns.exception.Timeout:
            error = "timed out"
        except (dns.exception.DNSException, OSError) as exc:
            error = str(exc)
        answer_str = error if error is not None else ", ".join(answers)
        results.append({
            "resolver": resolver_name,
            "ip": resolver_ip,
            "answers": answers,
            "answer_str": answer_str,
            "error": error,
        })

    failed = sum(r["error"] is not None for r in results)
    unique_answers = {tuple(r["answers"]) for r in results if r["error"] is None}
    all_agree = failed == 0 and len(unique_answers) == 1
    exit_code = 0 if all_agree else 1

    if getattr(args, "json", False):
        print(json.dumps(results, indent=2, ensure_ascii=False))
        sys.exit(exit_code)

    headers = ["Resolver", "IP", "Result"]
    rows = []
    for r in results:
        if r["error"] is not None:
            status = red(r["answer_str"])
        elif all_agree:
            status = green(r["answer_str"])
        else:
            status = yellow(r["answer_str"])

        rows.append([
            r["resolver"],
            dim(r["ip"]),
            status,
        ])

    print_table(headers, rows)

    if failed:
        print(f"\n  {red(f'{failed} resolver(s) failed.')} Propagation could not be verified.\n")
    elif all_agree:
        print(f"\n  {green('All queried resolvers agree.')} This does not guarantee global propagation.\n")
    else:
        unique = len(unique_answers)
        print(f"\n  {yellow(f'Inconsistent results ({unique} different answers).')} DNS may still be propagating.\n")

    if exit_code:
        sys.exit(exit_code)

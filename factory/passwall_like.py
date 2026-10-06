# -*- coding: utf-8 -*-
"""Convert the public data sources used by PassWall to Shadowrocket lists.

Shadowrocket cannot read V2Ray/Xray geosite.dat and geoip.dat directly, so the
source text is validated and converted during each scheduled build.
"""

from __future__ import annotations

import argparse
import ipaddress
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


CHINA_DOMAIN_URLS = (
    "https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/accelerated-domains.china.conf",
    "https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/apple.china.conf",
)
CHINA_IPV4_URL = (
    "https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/china.txt"
)
CHINA_IPV6_URL = (
    "https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/china6.txt"
)
MINIMUM_RULE_COUNTS = {"domains": 50_000, "ipv4": 1_000, "ipv6": 500}


def make_session() -> requests.Session:
    retries = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(("GET",)),
    )
    session = requests.Session()
    session.headers["User-Agent"] = "Shadowrocket-ADBlock-Rules-Forever builder"
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def download(session: requests.Session, url: str) -> str:
    print(f"Downloading {url}")
    response = session.get(url, timeout=(15, 90))
    response.raise_for_status()
    if not response.text.strip():
        raise RuntimeError(f"Downloaded an empty rule source: {url}")
    return response.text


def parse_dnsmasq_domains(text: str, source_url: str) -> set[str]:
    domains: set[str] = set()
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith("server=/"):
            raise ValueError(
                f"Unexpected dnsmasq rule at {source_url}:{line_number}: {line}"
            )
        parts = line.split("/")
        if len(parts) < 3 or not parts[1]:
            raise ValueError(
                f"Malformed dnsmasq rule at {source_url}:{line_number}: {line}"
            )
        domain = parts[1].removeprefix(".").lower()
        if re.fullmatch(r"[a-z0-9_](?:[a-z0-9._-]*[a-z0-9_])?", domain):
            domains.add(domain)
        else:
            raise ValueError(
                f"Unexpected domain at {source_url}:{line_number}: {domain}"
            )
    return domains


def parse_networks(text: str, version: int, source_url: str) -> list[str]:
    networks: set[ipaddress.IPv4Network | ipaddress.IPv6Network] = set()
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            network = ipaddress.ip_network(line, strict=True)
        except ValueError as exc:
            raise ValueError(
                f"Invalid CIDR at {source_url}:{line_number}: {line}"
            ) from exc
        if network.version != version:
            raise ValueError(
                f"Expected IPv{version} at {source_url}:{line_number}: {line}"
            )
        networks.add(network)
    return [str(network) for network in sorted(networks)]


def write_lines(path: Path, lines: list[str] | set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_lines = sorted(lines) if isinstance(lines, set) else lines
    path.write_text("\n".join(sorted_lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(sorted_lines):,} rules to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert PassWall data sources to plain Shadowrocket rule lists."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "resultant",
        help="Destination directory (default: factory/resultant)",
    )
    args = parser.parse_args()

    session = make_session()
    domains: set[str] = set()
    for url in CHINA_DOMAIN_URLS:
        domains.update(parse_dnsmasq_domains(download(session, url), url))

    ipv4 = parse_networks(download(session, CHINA_IPV4_URL), 4, CHINA_IPV4_URL)
    ipv6 = parse_networks(download(session, CHINA_IPV6_URL), 6, CHINA_IPV6_URL)

    counts = {"domains": len(domains), "ipv4": len(ipv4), "ipv6": len(ipv6)}
    for rule_type, minimum in MINIMUM_RULE_COUNTS.items():
        if counts[rule_type] < minimum:
            raise RuntimeError(
                f"Refusing to publish only {counts[rule_type]:,} {rule_type} rules; "
                f"expected at least {minimum:,}. The upstream source may be incomplete."
            )

    write_lines(args.output_dir / "passwall_china_domains.list", domains)
    write_lines(args.output_dir / "passwall_china_ipv4.list", ipv4)
    write_lines(args.output_dir / "passwall_china_ipv6.list", ipv6)

    sources = (*CHINA_DOMAIN_URLS, CHINA_IPV4_URL, CHINA_IPV6_URL)
    hosts = ", ".join(urlparse(url).netloc for url in sources)
    print(f"PassWall-like source conversion completed ({hosts}).")


if __name__ == "__main__":
    main()

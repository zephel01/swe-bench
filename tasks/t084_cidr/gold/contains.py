"""Membership test for an IPv4 address within a CIDR block."""

from mask import ip_to_int, network_range


def contains(cidr, ip):
    """Return whether ``ip`` falls within the ``cidr`` block (endpoints included)."""
    network, broadcast = network_range(cidr)
    value = ip_to_int(ip)
    return network <= value <= broadcast

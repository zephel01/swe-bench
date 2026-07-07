"""IPv4 address and CIDR block arithmetic."""


def ip_to_int(ip):
    """Convert a dotted-quad IPv4 string to a 32-bit integer."""
    a, b, c, d = (int(part) for part in ip.split("."))
    return (a << 24) | (b << 16) | (c << 8) | d


def network_range(cidr):
    """Return the ``(network, broadcast)`` integers for a CIDR block."""
    addr, bits = cidr.split("/")
    bits = int(bits)
    host_bits = 32 - bits
    base = ip_to_int(addr)
    mask = (0xFFFFFFFF << host_bits) & 0xFFFFFFFF
    network = base & mask
    broadcast = network + (2 ** host_bits) - 1
    return network, broadcast

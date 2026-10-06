import unittest

from factory.passwall_like import parse_dnsmasq_domains, parse_networks


class PassWallLikeParserTests(unittest.TestCase):
    def test_dnsmasq_domains_are_normalized_and_deduplicated(self):
        source = "\n".join(
            (
                "# comment",
                "server=/Example.CN/114.114.114.114",
                "server=/.example.cn/223.5.5.5",
                "server=/top/114.114.114.114",
            )
        )
        self.assertEqual(
            parse_dnsmasq_domains(source, "test"), {"example.cn", "top"}
        )

    def test_unexpected_dnsmasq_format_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_dnsmasq_domains("address=/example.cn/1.2.3.4", "test")

    def test_cidr_parser_validates_ip_version(self):
        self.assertEqual(
            parse_networks("1.0.1.0/24\n1.0.1.0/24\n", 4, "test"),
            ["1.0.1.0/24"],
        )
        with self.assertRaises(ValueError):
            parse_networks("2001:db8::/32", 4, "test")

    def test_cidr_parser_rejects_host_bits(self):
        with self.assertRaises(ValueError):
            parse_networks("192.0.2.1/24", 4, "test")


if __name__ == "__main__":
    unittest.main()

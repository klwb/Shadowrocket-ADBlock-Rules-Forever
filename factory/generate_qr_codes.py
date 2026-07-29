#!/usr/bin/env python3

from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_M


RAW_BASE_URL = (
    "https://raw.githubusercontent.com/klwb/"
    "Shadowrocket-ADBlock-Rules-Forever/release"
)

SUBSCRIPTION_FILES = (
    "sr_top500_banlist_ad.conf",
    "sr_top500_whitelist_ad.conf",
    "sr_top500_banlist.conf",
    "sr_top500_whitelist.conf",
    "sr_cnip_ad.conf",
    "sr_cnip.conf",
    "sr_direct_banad.conf",
    "sr_proxy_banad.conf",
    "sr_backcn.conf",
    "sr_backcn_ad.conf",
    "sr_ad_only.conf",
    "lazy.conf",
    "lazy_group.conf",
)


def main() -> None:
    repository_root = Path(__file__).resolve().parent.parent
    figure_directory = repository_root / "figure"
    figure_directory.mkdir(exist_ok=True)

    for filename in SUBSCRIPTION_FILES:
        subscription_url = f"{RAW_BASE_URL}/{filename}"
        qr_code = qrcode.QRCode(
            error_correction=ERROR_CORRECT_M,
            box_size=8,
            border=4,
        )
        qr_code.add_data(subscription_url)
        qr_code.make(fit=True)

        output_path = figure_directory / f"{Path(filename).stem}.png"
        qr_code.make_image(fill_color="black", back_color="white").save(output_path)
        print(f"{output_path.name}: {subscription_url}")


if __name__ == "__main__":
    main()

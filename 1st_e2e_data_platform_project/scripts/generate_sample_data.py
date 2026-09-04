#!/usr/bin/env python3
"""CLI utility to generate synthetic logistics data and upload to MinIO S3 landing layer."""
import argparse
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingestion.generator import LogisticsDataGenerator
from src.ingestion.s3_uploader import MinIOUploader
from src.quality.checks import DataQualityValidator


def main():
    parser = argparse.ArgumentParser(description="FastRoute Synthetic Data CLI Generator")
    parser.add_argument("--orders", type=int, default=100, help="Number of orders to generate")
    parser.add_argument("--pings", type=int, default=500, help="Number of telemetry pings to generate")
    parser.add_argument("--dirty-rate", type=float, default=0.05, help="Dirty records injection rate (0.0 - 1.0)")
    args = parser.parse_args()

    print(f"🚀 Generating {args.orders} orders and {args.pings} pings (dirty rate: {args.dirty_rate})...")
    generator = LogisticsDataGenerator(dirty_rate=args.dirty_rate)
    orders = generator.generate_orders(count=args.orders)
    pings = generator.generate_telemetry(count=args.pings)

    valid_orders, _, order_metrics = DataQualityValidator.validate_orders_batch(orders)
    valid_pings, _, ping_metrics = DataQualityValidator.validate_telemetry_batch(pings)

    print(f"✅ Validation: Orders {order_metrics['passed']}/{order_metrics['total']} passed, Pings {ping_metrics['passed']}/{ping_metrics['total']} passed")

    uploader = MinIOUploader()
    try:
        orders_s3 = uploader.upload_batch("orders", orders)
        pings_s3 = uploader.upload_batch("telemetry", pings)
        print(f"📦 Successfully uploaded to S3: {orders_s3} and {pings_s3}")
    except Exception as e:
        print(f"⚠️ S3 Upload Warning (MinIO offline?): {e}")


if __name__ == "__main__":
    main()

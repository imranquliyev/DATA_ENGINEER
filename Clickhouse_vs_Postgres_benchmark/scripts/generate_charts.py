#!/usr/bin/env python3
"""
Chart Visualization Generator for Analytical Query Benchmark
Creates publication-quality charts from summary_metrics.json and raw_timings.csv.
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Professional aesthetic theme configuration
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 11

def generate_charts():
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
    json_path = os.path.join(results_dir, "summary_metrics.json")
    
    if not os.path.exists(json_path):
        print(f"Metrics file {json_path} not found. Run benchmark first.")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    queries = data["queries"]
    concurrency_data = data.get("concurrency", [])

    q_names = [q["query_key"].replace("_", " ") for q in queries]
    pg_medians = [q["pg_median_ms"] for q in queries]
    ch_medians = [q["ch_median_ms"] for q in queries]
    speedups = [q["speedup_ratio"] for q in queries]
    
    pg_colds = [q["pg_cold_ms"] for q in queries]
    ch_colds = [q["ch_cold_ms"] for q in queries]

    x = np.arange(len(q_names))
    width = 0.35

    # -------------------------------------------------------------
    # Chart 1: Median Latency Comparison (Log Scale)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 6))
    rects1 = ax.bar(x - width/2, pg_medians, width, label='PostgreSQL 16', color='#336699', edgecolor='black', alpha=0.9)
    rects2 = ax.bar(x + width/2, ch_medians, width, label='ClickHouse', color='#FF9900', edgecolor='black', alpha=0.9)

    ax.set_ylabel('Median Latency (ms) - Log Scale', fontsize=12, fontweight='bold')
    ax.set_title('PostgreSQL vs ClickHouse: Median Query Latency (10M Rows)', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(q_names, rotation=30, ha='right', fontsize=10, fontweight='bold')
    ax.set_yscale('log')
    ax.legend(fontsize=11, loc='upper right', frameon=True)
    ax.grid(True, which="both", ls="--", alpha=0.5)

    # Add numeric labels on top of bars
    for rect in rects1:
        height = rect.get_height()
        ax.annotate(f'{height:.1f}ms',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, rotation=45)

    for rect in rects2:
        height = rect.get_height()
        ax.annotate(f'{height:.1f}ms',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, rotation=45)

    plt.tight_layout()
    chart1_path = os.path.join(results_dir, "chart_latency_bar.png")
    plt.savefig(chart1_path, dpi=300)
    plt.close()
    print(f"Generated {chart1_path}")

    # -------------------------------------------------------------
    # Chart 2: ClickHouse Speedup Ratio (Multiplier vs Postgres)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 5))
    colors = ['#2ca02c' if s >= 1.0 else '#d62728' for s in speedups]
    bars = ax.bar(q_names, speedups, color=colors, edgecolor='black', alpha=0.85, width=0.5)

    ax.axhline(1.0, color='red', linestyle='--', linewidth=1.5, label='Parity (1.0x)')
    ax.set_ylabel('Speedup Factor (ClickHouse / PostgreSQL)', fontsize=12, fontweight='bold')
    ax.set_title('ClickHouse Speedup Multiplier over PostgreSQL per Query', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticklabels(q_names, rotation=30, ha='right', fontsize=10, fontweight='bold')
    ax.grid(True, axis='y', ls="--", alpha=0.5)

    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}x',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.tight_layout()
    chart2_path = os.path.join(results_dir, "chart_speedup_bar.png")
    plt.savefig(chart2_path, dpi=300)
    plt.close()
    print(f"Generated {chart2_path}")

    # -------------------------------------------------------------
    # Chart 3: Cold vs Warm Cache Latency Comparison
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x_sub = np.arange(len(q_names))
    w_sub = 0.2

    ax.bar(x_sub - 1.5*w_sub, pg_colds, w_sub, label='Postgres Cold', color='#6baed6', edgecolor='black')
    ax.bar(x_sub - 0.5*w_sub, pg_medians, w_sub, label='Postgres Warm', color='#08519c', edgecolor='black')
    ax.bar(x_sub + 0.5*w_sub, ch_colds, w_sub, label='ClickHouse Cold', color='#fdae6b', edgecolor='black')
    ax.bar(x_sub + 1.5*w_sub, ch_medians, w_sub, label='ClickHouse Warm', color='#e6550d', edgecolor='black')

    ax.set_ylabel('Latency (ms) - Log Scale', fontsize=12, fontweight='bold')
    ax.set_title('Cold Cache vs Warm Cache Execution Latency', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x_sub)
    ax.set_xticklabels(q_names, rotation=30, ha='right', fontsize=10, fontweight='bold')
    ax.set_yscale('log')
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(True, which="both", ls="--", alpha=0.5)

    plt.tight_layout()
    chart3_path = os.path.join(results_dir, "chart_cold_vs_warm.png")
    plt.savefig(chart3_path, dpi=300)
    plt.close()
    print(f"Generated {chart3_path}")

    # -------------------------------------------------------------
    # Chart 4: Multi-client Concurrency Performance
    # -------------------------------------------------------------
    if concurrency_data:
        conc_levels = [c["concurrency"] for c in concurrency_data]
        pg_tps = [c["pg_throughput_rps"] for c in concurrency_data]
        ch_tps = [c["ch_throughput_rps"] for c in concurrency_data]

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(conc_levels, pg_tps, marker='o', linewidth=2.5, label='PostgreSQL 16', color='#336699')
        ax.plot(conc_levels, ch_tps, marker='s', linewidth=2.5, label='ClickHouse', color='#FF9900')

        ax.set_xlabel('Concurrent Clients', fontsize=12, fontweight='bold')
        ax.set_ylabel('Throughput (Requests / sec)', fontsize=12, fontweight='bold')
        ax.set_title('Multi-Client Concurrency Throughput Scaling', fontsize=14, fontweight='bold', pad=15)
        ax.set_xticks(conc_levels)
        ax.legend(fontsize=11)
        ax.grid(True, ls="--", alpha=0.5)

        plt.tight_layout()
        chart4_path = os.path.join(results_dir, "chart_concurrency.png")
        plt.savefig(chart4_path, dpi=300)
        plt.close()
        print(f"Generated {chart4_path}")

if __name__ == "__main__":
    generate_charts()

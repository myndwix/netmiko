#!/usr/bin/env python3
"""
Pull display command(s) from every Huawei switch in huawei_inventory.yaml over
SSH via netmiko, in parallel. Credentials and the commands to run are read
from a config file (hwtacacs_config.yaml by default) instead of being
prompted for or passed on the command line.

Examples:
    python show_hwtacacs.py
    python show_hwtacacs.py --save-dir output
    python show_hwtacacs.py --inventory hosts.yaml --workers 10
    python show_hwtacacs.py --config other_creds.yaml
"""
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException


def load_inventory(path):
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    devices = data.get("devices", [])
    if not devices:
        sys.exit(f"No devices found in {path}")
    return devices


def load_config(path):
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    username = data.get("username")
    password = data.get("password")
    show_commands = data.get("show_commands") or []
    config_commands = data.get("config_commands") or []
    if not username or not password:
        sys.exit(f"{path} must set both 'username' and 'password'")
    if not show_commands and not config_commands:
        sys.exit(f"{path} must set a non-empty 'show_commands' and/or 'config_commands' list")
    return username, password, show_commands, config_commands


def run_on_host(device_cfg, show_commands, config_commands, username, password):
    device = {
        "device_type": device_cfg.get("device_type", "huawei"),
        "host": device_cfg["host"],
        "username": device_cfg.get("username", username),
        "password": device_cfg.get("password", password),
    }
    host = device["host"]

    try:
        conn = ConnectHandler(**device)
    except NetmikoAuthenticationException:
        return host, None, "authentication failed"
    except NetmikoTimeoutException:
        return host, None, "connection timed out"
    except Exception as exc:
        return host, None, f"connection error: {exc}"

    outputs = {}
    try:
        for command in show_commands:
            try:
                outputs[command] = conn.send_command(command, read_timeout=60)
            except Exception as exc:
                outputs[command] = f"COMMAND ERROR: {exc}"

        if config_commands:
            label = "config: " + " / ".join(config_commands)
            try:
                outputs[label] = conn.send_config_set(config_commands, read_timeout=60)
            except Exception as exc:
                outputs[label] = f"COMMAND ERROR: {exc}"

        return host, outputs, None
    finally:
        conn.disconnect()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="hwtacacs_config.yaml",
        help="Path to YAML file with username/password/commands",
    )
    parser.add_argument(
        "--inventory", default="huawei_inventory.yaml", help="Path to inventory YAML file"
    )
    parser.add_argument(
        "--save-dir", help="Write each switch's output to <save-dir>/<host>.txt instead of stdout"
    )
    parser.add_argument(
        "--workers", type=int, default=5, help="Max concurrent SSH connections"
    )
    args = parser.parse_args()

    devices = load_inventory(args.inventory)
    username, password, show_commands, config_commands = load_config(args.config)

    save_dir = Path(args.save_dir) if args.save_dir else None
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(run_on_host, dev, show_commands, config_commands, username, password): dev["host"]
            for dev in devices
        }
        for future in as_completed(futures):
            host, outputs, error = future.result()
            results[host] = (outputs, error)

    for host in sorted(results):
        outputs, error = results[host]
        if error:
            print(f"\n=== {host} ===")
            print(f"ERROR: {error}")
            continue

        combined = "\n\n".join(
            f"---- {command} ----\n{output.strip()}" for command, output in outputs.items()
        )

        if save_dir:
            out_file = save_dir / f"{host}.txt"
            out_file.write_text(combined + "\n")
            print(f"{host}: saved to {out_file}")
        else:
            print(f"\n=== {host} ===")
            print(combined)


if __name__ == "__main__":
    main()

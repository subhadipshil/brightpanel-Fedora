"""BrightPanel CLI - Fast external monitor control for Fedora Linux."""

from __future__ import annotations
import sys
import os
import argparse
import json
import logging
import subprocess

from brightpanel import __version__
from brightpanel.core.detector import DisplayDetector, DisplayInfo
from brightpanel.core.vcp_manager import (
    VCPCode,
    normalize_input_code,
    get_input_name,
    DEFAULT_PRESETS
)
from brightpanel.core.i2c_queue import I2CCommandQueue
from brightpanel.core.doctor import SystemDoctor
from brightpanel.core.config import ConfigManager


def setup_logger(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(message)s" if not verbose else "[%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt)


def get_detector_and_queue(args: argparse.Namespace) -> tuple[DisplayDetector, I2CCommandQueue, list[DisplayInfo]]:
    mock_mode = args.mock or os.environ.get("MOCK_DDC", "0") in ("1", "true", "yes")
    detector = DisplayDetector()
    monitors = detector.detect(force_refresh=True, allow_mock=mock_mode)

    queue = I2CCommandQueue()
    queue.start()

    return detector, queue, monitors


def filter_monitors(monitors: list[DisplayInfo], monitor_arg: str | None) -> list[DisplayInfo]:
    if not monitor_arg or monitor_arg.lower() in ("all", "0"):
        return monitors

    # Try matching by display_num
    if monitor_arg.isdigit():
        num = int(monitor_arg)
        matches = [m for m in monitors if m.display_num == num]
        if matches:
            return matches

    # Try matching by model name or id or bus
    clean = monitor_arg.lower()
    matches = [
        m for m in monitors
        if clean in m.id.lower() or clean in m.model.lower() or clean in m.connector.lower()
    ]
    return matches or monitors


def cmd_list(args: argparse.Namespace) -> int:
    _, _, monitors = get_detector_and_queue(args)

    if args.json:
        print(json.dumps([m.to_dict() for m in monitors], indent=2))
        return 0

    if not monitors:
        print("\033[33mNo external DDC/CI monitors detected.\033[0m")
        print("Tip: Run 'brightpanel doctor' to diagnose Fedora I2C permissions, or use '--mock' for simulation.")
        return 1

    print("\033[1;36m========================================================================\033[0m")
    print("\033[1;36m                        Connected Displays                              \033[0m")
    print("\033[1;36m========================================================================\033[0m")
    print(f"{'#':<3} {'Model / Name':<28} {'Port':<12} {'Bus':<10} {'Bright':<8} {'Contrast'}")
    print("-" * 72)

    for m in monitors:
        bus = f"/dev/i2c-{m.bus_num}" if m.bus_num >= 0 else "N/A"
        print(
            f"{m.display_num:<3} {m.display_name[:26]:<28} {m.connector:<12} {bus:<10} "
            f"{m.current_brightness}%{'':<3} {m.current_contrast}%"
        )
    print("")
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    _, queue, monitors = get_detector_and_queue(args)
    targets = filter_monitors(monitors, args.monitor)

    if not targets:
        print("\033[31mNo matching monitors found.\033[0m", file=sys.stderr)
        return 1

    val = max(0, min(100, args.value))
    for m in targets:
        queue.set_brightness(m, val)
        if not args.quiet:
            print(f"Set brightness to {val}% on {m.display_name}")

    # Allow worker a fraction of a second to flush
    import time
    time.sleep(0.15)
    return 0


def cmd_inc_dec(args: argparse.Namespace, is_inc: bool = True) -> int:
    config = ConfigManager()
    step = args.step if args.step is not None else config.data.step_size

    _, queue, monitors = get_detector_and_queue(args)
    targets = filter_monitors(monitors, args.monitor)

    if not targets:
        print("\033[31mNo matching monitors found.\033[0m", file=sys.stderr)
        return 1

    for m in targets:
        curr = queue.get_cached_value(m.display_num, VCPCode.BRIGHTNESS, m.current_brightness)
        new_val = curr + step if is_inc else curr - step
        new_val = max(0, min(100, new_val))
        queue.set_brightness(m, new_val)
        if not args.quiet:
            print(f"Brightness: {curr}% -> {new_val}% on {m.display_name}")

    import time
    time.sleep(0.15)
    return 0


def cmd_contrast(args: argparse.Namespace) -> int:
    _, queue, monitors = get_detector_and_queue(args)
    targets = filter_monitors(monitors, args.monitor)

    if not targets:
        print("\033[31mNo matching monitors found.\033[0m", file=sys.stderr)
        return 1

    val = max(0, min(100, args.value))
    for m in targets:
        queue.set_contrast(m, val)
        if not args.quiet:
            print(f"Set contrast to {val}% on {m.display_name}")

    import time
    time.sleep(0.15)
    return 0


def cmd_volume(args: argparse.Namespace) -> int:
    _, queue, monitors = get_detector_and_queue(args)
    targets = filter_monitors(monitors, args.monitor)

    if not targets:
        print("\033[31mNo matching monitors found.\033[0m", file=sys.stderr)
        return 1

    val = max(0, min(100, args.value))
    for m in targets:
        queue.set_volume(m, val)
        if not args.quiet:
            print(f"Set volume to {val}% on {m.display_name}")

    import time
    time.sleep(0.15)
    return 0


def cmd_input(args: argparse.Namespace) -> int:
    code = normalize_input_code(args.source)
    if code is None:
        print(f"\033[31mUnknown input source: '{args.source}'.\033[0m", file=sys.stderr)
        print("Supported: hdmi1, hdmi2, hdmi3, dp1, dp2, usbc, type-c, dvi1, vga1, or hex code (e.g. 0x11)")
        return 1

    _, queue, monitors = get_detector_and_queue(args)
    targets = filter_monitors(monitors, args.monitor)

    if not targets:
        print("\033[31mNo matching monitors found.\033[0m", file=sys.stderr)
        return 1

    name = get_input_name(code)
    for m in targets:
        queue.set_input_source(m, code)
        if not args.quiet:
            print(f"Switched input source to {name} (0x{code:02X}) on {m.display_name}")

    import time
    time.sleep(0.2)
    return 0


def cmd_preset(args: argparse.Namespace) -> int:
    config = ConfigManager()
    preset = config.get_preset(args.name)
    if not preset:
        print(f"\033[31mUnknown preset '{args.name}'.\033[0m", file=sys.stderr)
        print(f"Available presets: {', '.join(config.data.presets.keys())}")
        return 1

    b = preset.get("brightness", 50)
    c = preset.get("contrast", 50)

    _, queue, monitors = get_detector_and_queue(args)
    targets = filter_monitors(monitors, args.monitor)

    for m in targets:
        queue.set_brightness(m, b)
        queue.set_contrast(m, c)
        if not args.quiet:
            print(f"Applied preset '{args.name}' (Brightness {b}%, Contrast {c}%) to {m.display_name}")

    import time
    time.sleep(0.2)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    doctor = SystemDoctor()
    if args.json:
        report = [item.to_dict() for item in doctor.run_all_checks()]
        print(json.dumps(report, indent=2))
        return 0

    print(doctor.generate_cli_report())
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    print("\033[1;36mConfiguring Fedora system permissions for DDC/CI monitor control...\033[0m")
    commands = [
        ("Loading i2c-dev kernel module", "sudo modprobe i2c-dev"),
        ("Configuring /etc/modules-load.d/i2c-dev.conf", "echo 'i2c-dev' | sudo tee /etc/modules-load.d/i2c-dev.conf"),
        ("Creating i2c user group", "sudo groupadd -f i2c"),
        ("Adding current user to i2c group", f"sudo usermod -aG i2c {os.environ.get('USER', 'subha')}"),
        ("Installing udev permissions rule", "echo 'KERNEL==\"i2c-[0-9]*\", GROUP=\"i2c\", MODE=\"0660\"' | sudo tee /etc/udev/rules.d/45-ddcutil-i2c.rules"),
        ("Reloading udev rules", "sudo udevadm control --reload-rules && sudo udevadm trigger"),
    ]

    for desc, cmd in commands:
        print(f"\n-> \033[1m{desc}\033[0m\n   Running: {cmd}")
        if not args.dry_run:
            try:
                res = subprocess.run(cmd, shell=True, check=False)
                if res.returncode != 0:
                    print(f"\033[33mWarning: command returned code {res.returncode}\033[0m")
            except Exception as e:
                print(f"\033[31mError running command: {e}\033[0m")

    print("\n\033[1;32mPermissions setup complete! Please log out and back in (or reboot) for group changes to activate.\033[0m")
    return 0


def cmd_daemon(args: argparse.Namespace) -> int:
    from brightpanel.daemon.service import BrightPanelDaemon
    print(f"\033[1;36mStarting BrightPanel D-Bus Daemon (v{__version__})...\033[0m")
    daemon = BrightPanelDaemon(mock_mode=args.mock)
    daemon.initialize()
    daemon.start_dbus_service()
    return 0


def build_parser() -> argparse.ArgumentParser:
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--mock", action="store_true", help="Simulate virtual displays without physical DDC/CI hardware")
    common_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress informational messages")
    common_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")

    parser = argparse.ArgumentParser(
        prog="brightpanel",
        parents=[common_parser],
        description="BrightPanel - Production-grade external monitor control suite for Fedora Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  brightpanel list                    List all connected external monitors
  brightpanel set 80                  Set brightness to 80% on all monitors
  brightpanel set 50 -m 1             Set brightness to 50% on monitor 1
  brightpanel inc 10                  Increase brightness by 10%
  brightpanel dec 10                  Decrease brightness by 10%
  brightpanel contrast 70             Set contrast to 70%
  brightpanel input dp1               Switch input source to DisplayPort 1
  brightpanel preset reading          Apply 'reading' preset (35% bright, 50% contrast)
  brightpanel doctor                  Run Fedora hardware & permissions audit
  brightpanel setup                   Configure Fedora i2c-dev & udev permissions
  brightpanel daemon --mock           Run D-Bus daemon in mock simulation mode
"""
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Sub-command to execute")

    # list
    p_list = subparsers.add_parser("list", parents=[common_parser], help="List connected monitors")
    p_list.add_argument("--json", action="store_true", help="Output in JSON format")

    # set
    p_set = subparsers.add_parser("set", parents=[common_parser], help="Set brightness (0-100)")
    p_set.add_argument("value", type=int, help="Brightness percentage (0-100)")
    p_set.add_argument("-m", "--monitor", type=str, default=None, help="Target monitor index, ID, or 'all'")

    # inc / up
    p_inc = subparsers.add_parser("inc", aliases=["up"], parents=[common_parser], help="Increase brightness by step (default 5%%)")
    p_inc.add_argument("step", type=int, nargs="?", default=None, help="Step percentage to increase")
    p_inc.add_argument("-m", "--monitor", type=str, default=None, help="Target monitor index, ID, or 'all'")

    # dec / down
    p_dec = subparsers.add_parser("dec", aliases=["down"], parents=[common_parser], help="Decrease brightness by step (default 5%%)")
    p_dec.add_argument("step", type=int, nargs="?", default=None, help="Step percentage to decrease")
    p_dec.add_argument("-m", "--monitor", type=str, default=None, help="Target monitor index, ID, or 'all'")

    # contrast
    p_cnt = subparsers.add_parser("contrast", parents=[common_parser], help="Set contrast (0-100)")
    p_cnt.add_argument("value", type=int, help="Contrast percentage (0-100)")
    p_cnt.add_argument("-m", "--monitor", type=str, default=None, help="Target monitor index, ID, or 'all'")

    # volume
    p_vol = subparsers.add_parser("volume", parents=[common_parser], help="Set audio speaker volume (0-100)")
    p_vol.add_argument("value", type=int, help="Volume percentage (0-100)")
    p_vol.add_argument("-m", "--monitor", type=str, default=None, help="Target monitor index, ID, or 'all'")

    # input
    p_inp = subparsers.add_parser("input", parents=[common_parser], help="Switch video input source (e.g. hdmi1, dp1, usbc)")
    p_inp.add_argument("source", type=str, help="Input source name or hex code (hdmi1, hdmi2, dp1, dp2, usbc, 0x11)")
    p_inp.add_argument("-m", "--monitor", type=str, default=None, help="Target monitor index, ID, or 'all'")

    # preset
    p_pre = subparsers.add_parser("preset", parents=[common_parser], help="Apply brightness/contrast preset")
    p_pre.add_argument("name", type=str, help="Preset name (daylight, office, coding, reading, night, minimal)")
    p_pre.add_argument("-m", "--monitor", type=str, default=None, help="Target monitor index, ID, or 'all'")

    # doctor
    p_doc = subparsers.add_parser("doctor", parents=[common_parser], help="Run Fedora system and permissions diagnosis")
    p_doc.add_argument("--json", action="store_true", help="Output diagnostic report in JSON")

    # setup
    p_setp = subparsers.add_parser("setup", parents=[common_parser], help="Configure Fedora i2c-dev and udev rules")
    p_setp.add_argument("--dry-run", action="store_true", help="Print setup commands without executing")

    # daemon
    p_dae = subparsers.add_parser("daemon", parents=[common_parser], help="Run background D-Bus service")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    setup_logger(args.verbose)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "list":
        return cmd_list(args)
    elif args.command == "set":
        return cmd_set(args)
    elif args.command in ("inc", "up"):
        return cmd_inc_dec(args, is_inc=True)
    elif args.command in ("dec", "down"):
        return cmd_inc_dec(args, is_inc=False)
    elif args.command == "contrast":
        return cmd_contrast(args)
    elif args.command == "volume":
        return cmd_volume(args)
    elif args.command == "input":
        return cmd_input(args)
    elif args.command == "preset":
        return cmd_preset(args)
    elif args.command == "doctor":
        return cmd_doctor(args)
    elif args.command == "setup":
        return cmd_setup(args)
    elif args.command == "daemon":
        return cmd_daemon(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())

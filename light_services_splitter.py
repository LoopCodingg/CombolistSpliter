import os
import sys
import threading
import time
from queue import Queue
from datetime import datetime
import shutil

try:
    #  full GUI window
    import tkinter as tk
    from tkinter import filedialog, messagebox
except Exception:  # pragma: no cover
    tk = None
    filedialog = None
    messagebox = None

# color output
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLOR_ENABLED = True
except Exception:  #no cover
    class _Dummy:
        RESET_ALL = ""
    class _Fore(_Dummy):
        RED = GREEN = YELLOW = CYAN = MAGENTA = BLUE = WHITE = ""
        LIGHTBLACK_EX = LIGHTWHITE_EX = LIGHTCYAN_EX = LIGHTBLUE_EX = ""
    class _Style(_Dummy):
        BRIGHT = DIM = NORMAL = ""
    Fore = _Fore()
    Style = _Style()
    COLOR_ENABLED = False


def print_header() -> None:
    title = "LIGHT SERVICES"
    sub = "COMBOLIST SPLITTER"
    width = shutil.get_terminal_size((60, 20)).columns
    line = (" " + sub + " ").center(width, "·")
    print()
    print(f"{Fore.YELLOW}{Style.BRIGHT}{title.center(width)}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{Style.BRIGHT}{line}{Style.RESET_ALL}\n")


class Spinner:
    def __init__(self, message: str = "Working") -> None:
        self.message = message
        self._running = False
        self._thread = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=0.2)
        # Ensure the spinner line is cleared
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()

    def _spin(self) -> None:
        sequence = ["⠋", "⠙", "⠸", "⠴", "⠦", "⠇"]
        i = 0
        while self._running:
            sys.stdout.write(f"\r{Fore.YELLOW}{sequence[i % len(sequence)]} {self.message}…{Style.RESET_ALL}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.08)


def select_file_via_dialog() -> str:
    if tk is None:
        return ""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    file_path = filedialog.askopenfilename(
        title="Select combolist (.txt)",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )
    root.destroy()
    return file_path or ""


def open_in_explorer(path: str) -> None:
    try:
        if os.path.isfile(path):
            os.startfile(os.path.dirname(path))  #  ignore
        else:
            os.startfile(path)  # ignore
    except Exception:
        pass


def read_lines(file_path: str) -> list:
    #
    encodings_to_try = ["utf-8", "cp1252", "latin-1"]
    for enc in encodings_to_try:
        try:
            with open(file_path, "r", encoding=enc, errors="strict") as f:
                return [line.rstrip("\n\r") for line in f]
        except Exception:
            continue
    #  replacement to avoid crash
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return [line.rstrip("\n\r") for line in f]


def sanitize_lines(lines: list) -> list:
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


def split_into_chunks(lines: list, chunk_size: int) -> list:
    return [lines[i : i + chunk_size] for i in range(0, len(lines), chunk_size)]


def write_chunk(file_dir: str, base_name: str, index: int, chunk: list, out_queue: Queue) -> None:
    file_name = f"{base_name}_part{index:02d}.txt"
    out_path = os.path.join(file_dir, file_name)
    try:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            for item in chunk:
                f.write(item + "\n")
        out_queue.put((True, out_path))
    except Exception as e:
        out_queue.put((False, f"Fehler beim Schreiben {out_path}: {e}"))


def main() -> None:
    print_header()
    print(f"{Fore.YELLOW}{Style.BRIGHT}Select your combolist (.txt){Style.RESET_ALL}")
    # Open dialog immediately. Fallback to manual input if Tk is unavailable.
    file_path = select_file_via_dialog()
    if not file_path and tk is None:
        print(f"{Fore.YELLOW}Tkinter not available. Enter the path manually.{Style.RESET_ALL}")
        user_input = input(f"{Fore.YELLOW}> Path: {Style.RESET_ALL}").strip().strip('"')
        file_path = user_input

    if not file_path:
        print(f"{Fore.YELLOW}Cancelled: No file selected.{Style.RESET_ALL}")
        return

    if not os.path.isfile(file_path):
        print(f"{Fore.YELLOW}Error: File not found:{Style.RESET_ALL} {file_path}")
        return

    spinner = Spinner("Reading lines")
    spinner.start()
    try:
        lines = read_lines(file_path)
    finally:
        spinner.stop()

    lines = sanitize_lines(lines)
    total = len(lines)
    if total == 0:
        print(f"{Fore.YELLOW}The file has no usable lines.{Style.RESET_ALL}")
        return

    print(f"{Fore.YELLOW}{Style.BRIGHT}Found lines:{Style.RESET_ALL} {total}")
    while True:
        chunk_raw = input(f"{Fore.YELLOW}> How many lines to include in output? (e.g., 1000): {Style.RESET_ALL}").strip()
        if not chunk_raw.isdigit():
            print(f"{Fore.YELLOW}Please enter a positive integer.{Style.RESET_ALL}")
            continue
        chunk_size = int(chunk_raw)
        if chunk_size <= 0:
            print(f"{Fore.YELLOW}Value must be greater than 0.{Style.RESET_ALL}")
            continue
        if chunk_size > total:
            print(f"{Fore.YELLOW}Requested count exceeds available lines ({total}). Using {total}.{Style.RESET_ALL}")
            chunk_size = total
        break

    # Create a single output 
    spinner = Spinner("Writing output")
    spinner.start()
    try:
        output_dir = os.getcwd()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"light_services_{chunk_size}_{timestamp}.txt"
        output_path = os.path.join(output_dir, output_name)
        subset = lines[:chunk_size]
        with open(output_path, "w", encoding="utf-8", newline="\n") as f:
            for item in subset:
                f.write(item + "\n")
    finally:
        spinner.stop()

    print(f"{Fore.YELLOW}{Style.BRIGHT}Created:{Style.RESET_ALL} {output_path}")

    # Offer to open the folder in Explorer
    print()
    open_choice = input(f"{Fore.YELLOW}Open output folder in Explorer? (Y/n): {Style.RESET_ALL}").strip().lower()
    if open_choice in ("", "y", "yes"):
        open_in_explorer(output_dir)

    print(f"\n{Fore.YELLOW}Done. Press Enter to exit…{Style.RESET_ALL}")
    try:
        input()
    except EOFError:
        pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")


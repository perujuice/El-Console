"""
Electricity Price Monitor for SE4 (Malmö, Sweden)
Displays current and daily electricity spot prices from elprisetjustnu.se
"""

import requests
from datetime import datetime, timedelta
import time
import sys
import os

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    ORANGE = '\033[38;5;208m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    DIM = '\033[2m'

# Clearing terminal for both Windows and Unix
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_price_color(price_kr):
    """Get color based on price threshold (in kr/kWh)"""
    if price_kr < 0.25:
        return Colors.GREEN
    elif price_kr < 0.55:
        return Colors.YELLOW
    elif price_kr < 0.85:
        return Colors.ORANGE
    else:
        return Colors.RED

def get_price_label(price_kr):
    """Get label for price level (in kr/kWh)"""
    if price_kr < 0.25:
        return "CHEAP"
    elif price_kr < 0.55:
        return "GOOD"
    elif price_kr < 0.85:
        return "EXPENSIVE"
    else:
        return "VERY EXPENSIVE"

def fetch_prices(date_str, region="SE4"):
    """Fetch electricity prices for a specific date.

    The data is fetched from elprisetjustnu.se API.

    date_str: should be YYYY-MM-DD (e.g. 2025-10-24).
    region: "SE4" for Malmö
    Returns list of price data or None on failure.
    """
    url = f"https://www.elprisetjustnu.se/api/v1/prices/{date_str}_{region}.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

def create_sparkline(prices, width=50):
    """Create a simple ASCII sparkline graph
    
    prices: list of float prices
    width: desired width of the sparkline (optional), default 50
    Returns a string representing the sparkline.
    """
    if not prices:
        return ""
    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price if max_price != min_price else 1

    # Sparkline characters
    chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']

    sparkline = ""
    for price in prices:
        normalized = (price - min_price) / price_range
        # use len(chars)-1 so normalized==1 maps to last index
        char_idx = int(normalized * (len(chars) - 1))
        char_idx = max(0, min(char_idx, len(chars) - 1))
        sparkline += chars[char_idx]

    if width and len(sparkline) > width:
        # downsample
        step = len(sparkline) / width
        compact = ""
        i = 0.0
        for _ in range(width):
            compact += sparkline[int(i)]
            i += step
        return compact
    elif width and len(sparkline) < width:
        # pad
        return sparkline.ljust(width, ' ')
    return sparkline

def _print_boxed_price(spot_price, price_label, price_color, min_inner=40):
    """ Print a boxed price with dynamic width based on content

    spot_price: float, the spot price in kr/kWh
    price_label: string, the label for the price level
    price_color: ANSI color code string for the price
    min_inner: minimum inner width of the box (optional), default 40
    
    """
    # Build plain content so we can measure visual width
    plain_content = f"  {spot_price:.4f} kr/kWh  ({price_label})"

    # Ensure a minimum width for aesthetics, but grow for longer labels
    inner_width = max(min_inner, len(plain_content) + 2)  # +2 for a little breathing room

    # Top border (colored)
    top = f"  {price_color}{Colors.BOLD}┏{'━' * inner_width}┓{Colors.RESET}"

    # Center the plain content within the inner width (this is the visual content)
    centered_plain = plain_content.center(inner_width)

    # Insert ANSI color codes around the numeric price and the label while preserving
    # the exact plain-text width (ANSI codes don't affect visual width).
    # Color the numeric price bold + price_color, and color the label with price_color.
    colored_numeric = f"{price_color}{Colors.BOLD}{spot_price:.4f}{Colors.RESET}"
    # Put the label colored but not bold (keeps parentheses visible)
    colored_label = f"({price_color}{price_label}{Colors.RESET})"

    # Replace only the first occurrences to avoid accidental multiple replacements
    colored_inner = centered_plain.replace(f"{spot_price:.4f}", colored_numeric, 1)
    colored_inner = colored_inner.replace(f"({price_label})", colored_label, 1)

    # Middle line: draw left border (colored), then the content, then right border (reapply color)
    middle = f"  {price_color}{Colors.BOLD}┃{Colors.RESET}{colored_inner}{price_color}{Colors.BOLD}┃{Colors.RESET}"

    # Bottom border (colored)
    bottom = f"  {price_color}{Colors.BOLD}┗{'━' * inner_width}┛{Colors.RESET}"

    print(top)
    print(middle)
    print(bottom)


def display_prices(prices_today, prices_tomorrow=None, provider_markup=0.0713):
    """Display current price and daily overview
    
    prices_today: list of price data for today
    prices_tomorrow: list of price data for tomorrow (optional), default None
    provider_markup: fixed markup in kr/kWh to add to spot price, default 0.0713 (which is my provider's rate)

    returns: None, prints to terminal
    """
    clear_screen()

    if not prices_today:
        print(f"{Colors.RED}Could not fetch electricity prices. Check internet connection.{Colors.RESET}")
        return

    now = datetime.now()
    current_hour = now.hour

    # Build a mapping hour -> price_data for robust display (handles any ordering or missing hours)
    price_by_hour = {}
    for p in prices_today:
        try:
            start = datetime.fromisoformat(p['time_start'])
            hour = start.hour
            price_by_hour[hour] = p
        except Exception:
            # skip malformed entries
            continue

    # Try to get current hour price_data
    current_price_data = price_by_hour.get(current_hour)
    if not current_price_data:
        # fallback: try to find an entry whose time_start hour equals now.hour (defensive)
        for p in prices_today:
            try:
                if datetime.fromisoformat(p['time_start']).hour == current_hour:
                    current_price_data = p
                    break
            except Exception:
                continue

    if not current_price_data:
        print(f"{Colors.RED}Could not find current price{Colors.RESET}")
        return

    spot_price = current_price_data['SEK_per_kWh']
    total_price = spot_price + provider_markup
    price_color = get_price_color(spot_price)
    price_label = get_price_label(spot_price)

    # Header
    print(f"\n{Colors.BOLD}{Colors.CYAN}⚡ ELECTRICITY PRICE MALMÖ (SE4) ⚡{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}\n")

    # Current time
    print(f"  {Colors.BOLD}{now.strftime('%H:%M:%S')}{Colors.RESET} - {now.strftime('%A %d %B %Y')}\n")

    # Current price - BIG display
    print(f"  {Colors.BOLD}RIGHT NOW:{Colors.RESET}")

    # Use the helper to print the boxed price (no reliance on label length)
    _print_boxed_price(spot_price, price_label, price_color)

    # With markup
    print(f"  {Colors.DIM}With markup (+{provider_markup:.4f} kr): {total_price:.4f} kr/kWh{Colors.RESET}\n")

    # Today's statistics
    # Collect prices in hour order for statistics & sparkline (missing hours skipped, if any)
    ordered_hours = sorted(price_by_hour.keys())
    today_prices = [price_by_hour[h]['SEK_per_kWh'] for h in ordered_hours]
    if today_prices:
        avg_today = sum(today_prices) / len(today_prices)
        min_today = min(today_prices)
        max_today = max(today_prices)
    else:
        avg_today = min_today = max_today = 0.0

    print(f"  {Colors.BOLD}TODAY:{Colors.RESET}")
    print(f"  Min: {Colors.GREEN}{min_today:.4f}{Colors.RESET} kr | ", end="")
    print(f"  Avg: {avg_today:.4f} kr | ", end="")
    print(f"  Max: {Colors.RED}{max_today:.4f}{Colors.RESET} kr\n")

    # Find best and worst hours (first occurrence)
    min_hour = max_hour = None
    for h in range(24):
        pd = price_by_hour.get(h)
        if not pd:
            continue
        v = pd['SEK_per_kWh']
        if v == min_today and min_hour is None:
            min_hour = h
        if v == max_today and max_hour is None:
            max_hour = h

    if min_hour is None:
        min_hour = 0
    if max_hour is None:
        max_hour = 0

    print(f"  Cheapest at {min_hour:02d}:00 ({Colors.GREEN}{min_today:.4f} kr{Colors.RESET})")
    print(f"  Most expensive at {max_hour:02d}:00 ({Colors.RED}{max_today:.4f} kr{Colors.RESET})\n")

    # --- HOURLY BREAKDOWN (perfectly aligned with color) ---
    print(f"  {Colors.BOLD}HOURLY BREAKDOWN:{Colors.RESET}")

    COL_WIDTH = 19
    SEP_PLAIN = " │ "  # plain separator for width calculations
    total_width = COL_WIDTH * 3 + len(SEP_PLAIN) * 2
    print(f"  {Colors.DIM}{'─' * total_width}{Colors.RESET}")
    print(
        f"  {Colors.BOLD}"
        f"{'Hour  Price(kr/kWh)'.ljust(COL_WIDTH)}{Colors.DIM}│{Colors.RESET} "
        f"{'Hour  Price(kr/kWh)'.ljust(COL_WIDTH)}{Colors.DIM}│{Colors.RESET} "
        f"{'Hour  Price(kr/kWh)'.ljust(COL_WIDTH)}{Colors.RESET}"
    )
    print(f"  {Colors.DIM}{'─' * total_width}{Colors.RESET}")

    # Map hours to prices
    price_by_hour = {}
    for p in prices_today:
        hour = datetime.fromisoformat(p['time_start']).hour
        price_by_hour[hour] = p["SEK_per_kWh"]

    # Helper: build one cell (plain padded, then colored)
    def build_cell(hour, price):
        if price is None:
            return "     --".ljust(COL_WIDTH)

        color = get_price_color(price)
        if hour == current_hour:
            hour_txt = f"{Colors.BOLD}[{hour:02d}]{Colors.RESET}"
        else:
            hour_txt = f" {hour:02d} "

        # Build plain text version for exact width
        plain = f"{hour_txt} {price:7.4f}"
        plain_no_ansi = f" {hour:02d}  {price:7.4f}"  # for padding
        padded = plain_no_ansi.ljust(COL_WIDTH)

        # Replace numeric part in padded string with colored version
        colored_price = f"{color}{price:7.4f}{Colors.RESET}"
        cell = padded.replace(f"{price:7.4f}", colored_price)
        # Replace hour with colored/bold version (doesn't affect width visually)
        cell = cell.replace(f" {hour:02d} ", hour_txt, 1)
        return cell

    # Print 8 rows (3 columns = 24 hours)
    for row in range(8):
        line = "  "
        for col in range(3):
            hour = row + col * 8
            price = price_by_hour.get(hour)
            cell = build_cell(hour, price)
            line += cell
            if col < 2:
                line += f"{Colors.DIM}│{Colors.RESET} "
        print(line)

    print(f"  {Colors.DIM}{'─' * total_width}{Colors.RESET}\n")

    # --- POLISHED SPARKLINE (2 chars per hour, 48 chars wide) ---
    try:
        hour_price_dict = {datetime.fromisoformat(p["time_start"]).hour: p["SEK_per_kWh"] for p in prices_today}

        levels = "▁▂▃▄▅▆▇█"
        sparkline_chars = ""

        min_price = min(hour_price_dict.values())
        max_price = max(hour_price_dict.values())

        # Stretch tiny ranges
        span = max_price - min_price
        if span < 0.05:
            min_price -= 0.02
            max_price += 0.02
            span = max_price - min_price

        for h in range(24):
            price = hour_price_dict.get(h, min_price)
            normalized = (price - min_price) / span
            idx = round(normalized * (len(levels)-1))
            idx = min(idx, len(levels)-1)
            char = levels[idx] * 2  # double width for 48-char sparkline
            color = get_price_color(price)
            if h == current_hour:
                sparkline_chars += f"{Colors.BOLD}{color}{char}{Colors.RESET}"
            else:
                sparkline_chars += f"{color}{char}{Colors.RESET}"

        print(f"  {sparkline_chars}")

        # Hour labels under correct blocks
        label_line = [" "] * 48
        for h in [0, 6, 12, 18, 23]:
            pos = h * 2
            hour_str = f"{h:02d}"
            if pos < 48:
                label_line[pos] = hour_str[0]
            if pos + 1 < 48:
                label_line[pos + 1] = hour_str[1]
        print("  " + "".join(label_line) + "\n")

    except Exception as e:
        print(f"{Colors.RED} Error drawing sparkline: {e}{Colors.RESET}")

    # Tomorrow's prices if available
    if prices_tomorrow:
        price_by_hour_t = {}
        for p in prices_tomorrow:
            try:
                h = datetime.fromisoformat(p['time_start']).hour
                price_by_hour_t[h] = p
            except Exception:
                continue
        tomorrow_prices = [price_by_hour_t[h]['SEK_per_kWh'] for h in sorted(price_by_hour_t.keys())]
        if tomorrow_prices:
            avg_tomorrow = sum(tomorrow_prices) / len(tomorrow_prices)
            min_tomorrow = min(tomorrow_prices)
            # find cheapest hour tomorrow
            min_hour_tomorrow = next((h for h, pd in price_by_hour_t.items() if pd['SEK_per_kWh'] == min_tomorrow), None)
            if min_hour_tomorrow is None:
                min_hour_tomorrow = 0
            print(f"  {Colors.BOLD}TOMORROW:{Colors.RESET}")
            print(f"  Min: {Colors.GREEN}{min_tomorrow:.4f}{Colors.RESET} kr | Avg: {avg_tomorrow:.4f} kr")
            print(f"  Cheapest at {min_hour_tomorrow:02d}:00\n")
        else:
            print(f"  {Colors.DIM}Tomorrow's prices not yet available{Colors.RESET}\n")
    else:
        print(f"  {Colors.DIM}Tomorrow's prices published around 13:00{Colors.RESET}\n")

    # Suggestions
    # TODO: improve logic here later, implement statistical approach
    if today_prices and spot_price < avg_today * 0.8: # Right now I am using 80% of average as threshold
        print(f"  {Colors.GREEN} GOOD TIME TO: Run dishwasher, Vacuum, play video games{Colors.RESET}")
    elif today_prices and spot_price > avg_today * 1.2: # And here just 20% over average.
        print(f"  {Colors.RED} AVOID: Energy-intensive appliances right now{Colors.RESET}")

    print(f"\n  {Colors.DIM}Source: elprisetjustnu.se | Data from ENTSO-E{Colors.RESET}")
    print(f"  {Colors.DIM}Updates every hour{Colors.RESET}\n")

def main():
    """Main loop"""
    print(f"{Colors.CYAN}Starting electricity price monitor...{Colors.RESET}")
    time.sleep(1)

    while True:
        try:
            # Get today's date in YYYY-MM-DD format (API expects this swedish format)
            today = datetime.now()
            today_str = today.strftime("%Y/%m-%d")

            # Get tomorrow's date
            tomorrow = today + timedelta(days=1)
            tomorrow_str = tomorrow.strftime("%Y/%m-%d")

            # Fetch prices
            prices_today = fetch_prices(today_str)
            prices_tomorrow = fetch_prices(tomorrow_str)
            
            print(prices_today[0])

            # Display
            display_prices(prices_today, prices_tomorrow)

            # Wait 60 seconds before refresh
            print(f"  {Colors.DIM}Updating in 60 seconds... (Ctrl+C to exit){Colors.RESET}")
            time.sleep(60)

        except KeyboardInterrupt:
            print(f"\n\n{Colors.CYAN}👋 Goodbye!{Colors.RESET}\n")
            sys.exit(0)
        except Exception as e:
            print(f"\n{Colors.RED} Error: {e}{Colors.RESET}")
            print(f"{Colors.DIM}Retrying in 30 seconds...{Colors.RESET}")
            time.sleep(30)

if __name__ == "__main__":
    main()

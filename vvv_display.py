import tkinter as tk
import requests
import time

# --- Configuration ---
TOKEN_ID = 'venice-token' # CoinGecko API ID for the token.
VS_CURRENCY = 'usd'   # Currency to display the price in.
HOLDING_AMOUNT = 2500 # Amount of the token you hold.
REFRESH_INTERVAL_MS = 60000 # Refresh interval in milliseconds (60 seconds).
WINDOW_TITLE = f"{TOKEN_ID.capitalize()} Price Monitor ({VS_CURRENCY.upper()})"
INITIAL_DELAY_MS = 100 # Small delay before the first API call

# --- API Function ---
def get_price(token_id, vs_currency):
    """
    Fetches the current price of a token from the CoinGecko API.

    Args:
        token_id (str): The CoinGecko API ID for the token.
        vs_currency (str): The currency to get the price in.

    Returns:
        float: The current price, or None if an error occurs.
    """
    url = f"https://api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': token_id,
        'vs_currencies': vs_currency
    }
    try:
        # Increased timeout slightly for potentially slower connections
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if token_id in data and vs_currency in data[token_id]:
            return data[token_id][vs_currency]
        else:
            if token_id not in data:
                 print(f"Error: Token ID '{token_id}' not found in CoinGecko API response.")
            elif vs_currency not in data.get(token_id, {}):
                 print(f"Error: Currency '{vs_currency}' not found for token '{token_id}' in API response.")
            else:
                 print(f"Error: Could not find price data for '{token_id}' in '{vs_currency}'.")
            print("Response data:", data)
            return None

    except requests.exceptions.Timeout:
        print(f"Error: Request to CoinGecko API timed out.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from CoinGecko API: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# --- GUI Update Function ---
def update_price_label():
    """
    Fetches the new price, calculates holding value, and updates the GUI labels.
    Schedules the next update.
    """
    # Ensure labels exist before trying to configure them
    if not price_label or not status_label or not holding_value_label: # Check new label too
         print("Error: GUI labels not ready.")
         # Schedule the next attempt anyway
         root.after(REFRESH_INTERVAL_MS, update_price_label)
         return

    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Fetching price for {TOKEN_ID}...")
    price = get_price(TOKEN_ID, VS_CURRENCY)

    if price is not None:
        # Calculate holding value
        total_value = price * HOLDING_AMOUNT

        # Format price and value strings
        try:
            price_str = f"${price:,.2f} {VS_CURRENCY.upper()}" # Show 2 decimal places
            value_str = f"Holding: ${total_value:,.2f}" # Format total value
        except (ValueError, TypeError):
             price_str = f"${price} {VS_CURRENCY.upper()}" # Fallback if formatting fails
             value_str = f"Holding: ${total_value}" # Fallback

        status_str = f"Last updated: {time.strftime('%H:%M:%S')}"

        # Update labels
        price_label.config(text=price_str)
        holding_value_label.config(text=value_str) # Update the new holding value label
        status_label.config(text=status_str, fg="#AAAAAA") # Reset status color on success
        print(f"Price updated: {price_str}")
        print(f"Holding value updated: {value_str}")

    else:
        # Update status to indicate error, keep last price/value if available
        if price_label.cget("text") == "Loading...":
             price_label.config(text="N/A") # Indicate not available if never loaded
             holding_value_label.config(text="Holding: N/A") # Also set holding value to N/A
        status_label.config(text=f"Update Error. Retrying...", fg="#FF6B6B") # Red color for error
        print(f"Failed to update price for {TOKEN_ID}.")

    # Schedule the next update using the configured interval
    root.after(REFRESH_INTERVAL_MS, update_price_label)

# --- GUI Setup ---
root = tk.Tk()
root.title(WINDOW_TITLE)
root.geometry("350x200") # Increased height slightly for the new label
root.configure(bg='#2E2E2E')

# Style options
label_font = ("Helvetica", 28, "bold")
holding_font = ("Helvetica", 14) # Font for the holding value
status_font = ("Helvetica", 10)
text_color = "#FFFFFF"
bg_color = "#2E2E2E"

# Token Name Label
token_name_label = tk.Label(
    root,
    text=TOKEN_ID.replace('-', ' ').capitalize(), # Replace hyphen for display
    font=("Helvetica", 16, "bold"),
    fg=text_color,
    bg=bg_color,
    pady=5
)
token_name_label.pack()

# Price Label - Initialize placeholder
price_label = tk.Label(
    root,
    text="Loading...",
    font=label_font,
    fg=text_color,
    bg=bg_color,
    pady=5 # Reduced padding slightly
)
price_label.pack()

# Holding Value Label - NEW LABEL
holding_value_label = tk.Label(
    root,
    text="Calculating...", # Initial text
    font=holding_font,
    fg=text_color, # White text
    bg=bg_color,
    pady=5
)
holding_value_label.pack()

# Status Label - Initialize placeholder
status_label = tk.Label(
    root,
    text="Initializing...",
    font=status_font,
    fg="#AAAAAA",
    bg=bg_color,
    pady=5
)
status_label.pack()

# --- Initial Load & Main Loop ---
# Schedule the *first* call to update_price_label shortly after mainloop starts
root.after(INITIAL_DELAY_MS, update_price_label)
root.mainloop()

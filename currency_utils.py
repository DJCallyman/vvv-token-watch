def format_currency(value, currency):
    """Format a numeric value as a currency string with appropriate symbol and decimal places."""
    if value is None:
        return "N/A"
    
    if currency.lower() == 'usd':
        return f"${value:,.2f}"
    elif currency.lower() == 'aud':
        return f"A${value:,.2f}"
    else:
        # Fallback for other currencies
        return f"{currency.upper()} {value:,.2f}"

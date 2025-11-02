import requests
import warnings
import urllib3
import logging
import json # Import json for potentially pretty-printing dicts/lists

# --- ANSI Color Codes ---
COLOR_RESET = "\033[0m"
COLOR_CYAN = "\033[96m"
COLOR_YELLOW = "\033[93m"
COLOR_GREEN = "\033[92m"
COLOR_MAGENTA = "\033[95m"
COLOR_BLUE = "\033[94m"
COLOR_RED = "\033[91m"
# -------------------------

# Suppress all warnings from urllib3 (Use with caution in production)
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

# Configure logging to output directly (useful for colors)
# Use print instead of logging inside display_models for direct color output
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Your actual API key - Replace with a secure method like environment variables
API_KEY = 'gqhvkz3l58GIcuJV88G2MiiWayN3BCpRanuO00oWMa' # Replace with your real key or load securely

def list_models():
    """Fetches the list of all models from the Venice AI API."""
    url = 'https://api.venice.ai/api/v1/models'
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }
    params = {
        'type': 'all'  # Fetch all model types
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15) # Added timeout
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred while fetching models: {http_err} - Response: {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        logging.error(f"Connection error occurred while fetching models: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        logging.error(f"Timeout error occurred while fetching models: {timeout_err}")
    except requests.exceptions.RequestException as err:
        logging.error(f"An error occurred while fetching models: {err}")
    return None

def get_model_types(models_response):
    """Extracts unique model types from the API response."""
    if not models_response or 'data' not in models_response:
        logging.warning("No model data found to extract types from.")
        return []
    model_types = set()
    for model in models_response['data']:
        model_types.add(model.get('type', 'Unknown'))
    return sorted(list(model_types))

def prompt_user_for_model_type(model_types):
    """Prompts the user to select a model type to display."""
    if not model_types:
        logging.warning("No model types available to choose from.")
        return None

    print("\nAvailable Model Types:")
    for i, model_type in enumerate(model_types):
        print(f"{COLOR_YELLOW}{i+1}{COLOR_RESET}. {model_type}") # Color option number
    all_option_number = len(model_types) + 1
    print(f"{COLOR_YELLOW}{all_option_number}{COLOR_RESET}. All")

    while True:
        try:
            choice_input = input(f"Enter the number for the model type (or {all_option_number} for All): ")
            choice = int(choice_input)
            if 1 <= choice <= len(model_types):
                return model_types[choice-1]
            elif choice == all_option_number:
                return "all"
            else:
                print(f"{COLOR_RED}Invalid choice number. Please try again.{COLOR_RESET}")
        except ValueError:
            print(f"{COLOR_RED}Invalid input. Please enter a number.{COLOR_RESET}")
        except EOFError:
            print("\nInput cancelled.")
            return None

def display_models(models, selected_model_type):
    """Displays details for models of the selected type with formatting."""
    # Using print directly for color control instead of logging here
    print(f"\n{COLOR_MAGENTA}--- Available Models (Type: '{selected_model_type}') ---{COLOR_RESET}")
    if not models or 'data' not in models:
        print(f"{COLOR_RED}Invalid or empty models response provided.{COLOR_RESET}")
        return

    found_models = False
    for model in models['data']:
        model_id = model.get('id', 'N/A')
        model_type = model.get('type', 'Unknown')

        # Filter based on selected type
        if selected_model_type == "all" or model_type == selected_model_type:
            found_models = True
            model_spec = model.get('model_spec', {})

            # --- Print formatted model info ---
            print(f"\n  {COLOR_CYAN}ID{COLOR_RESET}: {model_id}")
            print(f"  {COLOR_YELLOW}Type{COLOR_RESET}: {model_type}")

            if model_type == "text":
                available_context_tokens = model_spec.get('availableContextTokens', 'N/A')
                capabilities = model_spec.get('capabilities', {})
                constraints = model_spec.get('constraints', {})
                traits = model_spec.get('traits', [])
                print(f"    {COLOR_GREEN}Context Tokens{COLOR_RESET}: {available_context_tokens}")
                # Pretty print dictionary/list content if it exists
                if capabilities:
                    print(f"    {COLOR_GREEN}Capabilities{COLOR_RESET}: {json.dumps(capabilities, indent=6)}") # Indent JSON
                if constraints:
                    print(f"    {COLOR_GREEN}Constraints{COLOR_RESET}: {json.dumps(constraints, indent=6)}")
                if traits:
                     print(f"    {COLOR_GREEN}Traits{COLOR_RESET}: {', '.join(traits)}") # Join list

            elif model_type == "image":
                constraints = model_spec.get('constraints', {})
                traits = model_spec.get('traits', [])
                if constraints:
                    print(f"    {COLOR_GREEN}Constraints{COLOR_RESET}: {json.dumps(constraints, indent=6)}")
                if traits:
                     print(f"    {COLOR_GREEN}Traits{COLOR_RESET}: {', '.join(traits)}")

            elif model_type == "tts":
                 voices = model_spec.get('voices', [])
                 if voices:
                     print(f"    {COLOR_GREEN}Voices{COLOR_RESET}: {', '.join(voices)}")

            # Add other model types (embedding) if needed
            # --- End formatted model info ---

    if not found_models:
        print(f"{COLOR_YELLOW}No models found for the selected type: '{selected_model_type}'{COLOR_RESET}")
    print(f"\n{COLOR_MAGENTA}--- End of List ---{COLOR_RESET}") # Footer for clarity

# --- Main execution ---
if __name__ == "__main__":
    print("Fetching models from Venice AI...")
    models_response = list_models() # Use logging for this part

    if models_response:
        model_types = get_model_types(models_response)
        if model_types:
            selected_type = prompt_user_for_model_type(model_types) # Uses print for colors
            if selected_type:
                display_models(models_response, selected_type) # Uses print for colors
            else:
                print("No model type selected.") # Uses print
        else:
            print("Could not determine model types from the response.") # Uses print
    else:
        # Error already logged in list_models
        print("Failed to retrieve models. Please check logs above for errors.") # Uses print
      
# camunda/camunda_client.py
import requests
import json
import logging
import config # Import configuration

def get_next_state_from_camunda(current_state, input_symbol):
    """Calls the Camunda 7 REST API to evaluate the DMN and get the next state."""

    evaluate_url = config.CAMUNDA_DMN_EVAL_URL # Use C7 URL from config

    request_body = {
        "variables": {
            # C7 expects variable structure directly under 'variables'
            "currentState": {"value": current_state, "type": "String"},
            "inputSymbol": {"value": input_symbol, "type": "String"}
        }
    }
    # Standard headers for JSON
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    # --- Basic Authentication (Optional - Add if C7 security enabled) ---
    auth_tuple = None
    if config.CAMUNDA_BASIC_AUTH_USER and config.CAMUNDA_BASIC_AUTH_PASS:
        auth_tuple = (config.CAMUNDA_BASIC_AUTH_USER, config.CAMUNDA_BASIC_AUTH_PASS)
        logging.info("Attempting DMN evaluation with Basic Authentication.")
    else:
        logging.info("Attempting DMN evaluation without Authentication.")
    # --- End Basic Authentication ---

    logging.debug(f"C7 DMN Request URL: {evaluate_url}")
    logging.debug(f"C7 DMN Request: State='{current_state}', Symbol='{input_symbol}'")
    logging.debug(f"Request Body: {json.dumps(request_body)}")
    logging.debug(f"Request Headers: {headers}")
    logging.debug(f"Auth Tuple: {auth_tuple}")

    try:
        response = requests.post(
            evaluate_url,
            headers=headers,
            json=request_body, # Send data as JSON body
            auth=auth_tuple,   # Pass auth tuple if configured (will be None otherwise)
            timeout=15
        )
        response.raise_for_status() # Check for HTTP errors (4xx, 5xx)
        result = response.json()
        logging.debug(f"C7 DMN Response: {result}")

        # Camunda 7 evaluation response structure
        # Result is typically a list of matching rule outputs
        if not result or not isinstance(result, list) or len(result) == 0:
             if isinstance(result, dict) and 'message' in result:
                 raise RuntimeError(f"DMN Eval Error from Camunda: {result.get('message', 'Unknown error')}")
             raise RuntimeError(f"DMN Engine returned unexpected result format: {result}")

        # Assuming UNIQUE hit policy, get the first result's outputs
        first_result_outputs = result[0]
        # Output variable name is defined in the DMN output column ('nextState')
        next_state = first_result_outputs.get('nextState', {}).get('value')

        if next_state is None:
             raise RuntimeError(f"DMN result missing 'nextState' output variable in response: {first_result_outputs}")

        logging.info(f"C7 DMN Transition: {current_state} --({input_symbol})--> {next_state}")
        return next_state

    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection Error connecting to Camunda 7 at {config.CAMUNDA_BASE_URL}: {e}")
        raise ConnectionError(f"Cannot connect to Camunda 7. Is Camunda Platform Run started? Check URL in config.py.")
    except requests.exceptions.Timeout:
        logging.error(f"Connection timed out connecting to Camunda 7.")
        raise TimeoutError(f"Connection to Camunda 7 timed out ({evaluate_url}).")
    except requests.exceptions.HTTPError as e:
         status_code = e.response.status_code
         logging.error(f"Camunda HTTP Error: {status_code} {e.response.reason}")
         try: logging.error(f"Camunda Response Body: {e.response.text}")
         except Exception: pass

         # Specific C7 errors
         if status_code == 401: # Unauthorized (if basic auth was wrong/needed)
             error_msg = "Failed DMN evaluation: 401 Unauthorized. Check Basic Auth credentials in config.py if security is enabled in Camunda 7."
         elif status_code == 404: # Not Found
             error_msg = (f"Failed DMN evaluation: 404 Not Found. Verify DMN deployment key "
                          f"('{config.DMN_DECISION_KEY}') and API URL ('{evaluate_url}'). Check Cockpit for deployment.")
         else: # Other errors (like 500 internal server error)
             error_msg = f"Failed DMN evaluation: HTTP {status_code}. Check Camunda 7 logs (in terminal where start.bat runs) and deployment status."
         raise RuntimeError(error_msg) from e

    except Exception as e:
        logging.error(f"Unexpected error during Camunda 7 API call: {e}", exc_info=True)
        raise

    
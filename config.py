# config.py
import os

DEFAULT_REPORT_FILENAME = "resume_analysis_report.txt"

CAMUNDA_BASE_URL = "http://localhost:8080"
CAMUNDA_REST_CONTEXT = "/engine-rest"

DMN_DECISION_KEY = "resume-dfa-dynamic-skills"

C7_DMN_EVAL_PATH_TEMPLATE = "{base_context}/decision-definition/key/{key}/evaluate"

CAMUNDA_DMN_EVAL_URL = f"{CAMUNDA_BASE_URL}{C7_DMN_EVAL_PATH_TEMPLATE.format(base_context=CAMUNDA_REST_CONTEXT, key=DMN_DECISION_KEY)}"

CAMUNDA_BASIC_AUTH_USER = None
CAMUNDA_BASIC_AUTH_PASS = None

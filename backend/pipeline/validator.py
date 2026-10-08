from typing import Any, Dict, Tuple, Optional

MAX_ARGUMENT_LENGTH = 32768  # Prevent oversized input attacks

class SchemaValidator:
    """
    Schema Validator Layer:
    Validates tool invocation arguments against the JSON Schema defined in Tool Registry.
    Ensures required fields exist, data types match, unexpected arguments are rejected,
    null values are blocked, and enum constraints are respected.
    """
    @staticmethod
    def validate(schema: Dict[str, Any], params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not isinstance(params, dict):
            return False, f"INVALID_TOOL_ARGUMENTS: Expected parameters as JSON object (dict), got {type(params).__name__}"

        # 1. Check required parameters
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in params or params[field] is None:
                return False, f"INVALID_TOOL_ARGUMENTS: Missing required parameter '{field}'"

        # 2. Check properties and reject unexpected arguments
        properties = schema.get("properties", {})
        allow_additional = schema.get("additionalProperties", False)

        for key, val in params.items():
            if key not in properties:
                if not allow_additional:
                    return False, f"INVALID_TOOL_ARGUMENTS: Unexpected argument '{key}' not accepted by schema."
                continue

            prop_def = properties[key]
            expected_type = prop_def.get("type")

            # Check null value
            if val is None:
                return False, f"INVALID_TOOL_ARGUMENTS: Parameter '{key}' cannot be null."

            # Oversized string check
            if isinstance(val, str) and len(val) > MAX_ARGUMENT_LENGTH:
                return False, f"INVALID_TOOL_ARGUMENTS: Parameter '{key}' exceeds maximum length of {MAX_ARGUMENT_LENGTH} chars."

            if expected_type == "string":
                if not isinstance(val, str):
                    return False, f"INVALID_TOOL_ARGUMENTS: Parameter '{key}' must be a string, got {type(val).__name__}"
            elif expected_type == "integer":
                if not isinstance(val, int) or isinstance(val, bool):
                    return False, f"INVALID_TOOL_ARGUMENTS: Parameter '{key}' must be an integer, got {type(val).__name__}"
            elif expected_type == "number":
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                    return False, f"INVALID_TOOL_ARGUMENTS: Parameter '{key}' must be a number, got {type(val).__name__}"
            elif expected_type == "boolean":
                if not isinstance(val, bool):
                    return False, f"INVALID_TOOL_ARGUMENTS: Parameter '{key}' must be a boolean, got {type(val).__name__}"
            elif expected_type == "array":
                if not isinstance(val, list):
                    return False, f"INVALID_TOOL_ARGUMENTS: Parameter '{key}' must be an array (list), got {type(val).__name__}"
            elif expected_type == "object":
                if not isinstance(val, dict):
                    return False, f"INVALID_TOOL_ARGUMENTS: Parameter '{key}' must be an object (dict), got {type(val).__name__}"

            # Check enum constraint if present
            if "enum" in prop_def and val not in prop_def["enum"]:
                allowed = ", ".join([repr(x) for x in prop_def["enum"]])
                return False, f"INVALID_TOOL_ARGUMENTS: Parameter '{key}' value {repr(val)} is not permitted. Allowed values: [{allowed}]"

        return True, None

schema_validator = SchemaValidator()

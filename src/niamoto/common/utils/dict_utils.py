# src/niamoto/common/utils/dict_utils.py

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def get_nested_value(
    data_dict: Dict[str, Any], key_path: str, default: Optional[Any] = None
) -> Optional[Any]:
    """Retrieves a value from a nested dictionary using a dot-separated key path.

    Args:
        data_dict: The dictionary to search within.
        key_path: The dot-separated path to the desired value (e.g., 'level1.level2.key').
        default: The value to return if the key path is not found or invalid.

    Returns:
        The found value, or the default value if not found.
    """
    if not isinstance(data_dict, dict):
        logger.warning(
            f"Cannot access key path '{key_path}' on non-dict data: {type(data_dict)}"
        )
        return default

    keys = key_path.split(".")
    current_data = data_dict
    for key in keys:
        if isinstance(current_data, dict):
            current_data = current_data.get(key)
            if current_data is None:
                # logger.debug(f"Key '{key}' not found in path '{key_path}'")
                return default  # Key not found at this level
        else:
            logger.warning(
                f"Cannot access key '{key}' on non-dict element in path '{key_path}'"
            )
            return default  # Tried to access key on non-dict
    return current_data

class StateManager:
    """
    Singleton class for managing temporary application state.

    Categories:
        - bulk_update: Stores states for bulk subscription updates.
        - single_update: Stores states for single subscription updates.
        - other_values: Stores miscellaneous temporary data.

    Methods:
        - set_state(category, key, value): Set a value in a specific category.
        - get_state(category, key, default): Retrieve a value from a category.
        - delete_state(category, key): Delete a value from a category.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._state = {
                "bulk_update": {},  # Bulk subscription states
                "single_update": {},  # Single subscription states
                "other_values": {},  # Other boolean/integer values
            }
        return cls._instance

    def set_state(self, category, key, value):
        """Set a value in a specific category."""
        if category not in self._state:
            self._state[category] = {}
        self._state[category][key] = value

    def get_state(self, category, key, default=None):
        """Get a value from a specific category."""
        return self._state.get(category, {}).get(key, default)

    def delete_state(self, category, key):
        """Delete a specific value from a category."""
        if category in self._state and key in self._state[category]:
            del self._state[category][key]
            return True
        return False
    
    def has_state(self, category, key):
        """Check if a specific key exists in the given category."""
        return key in self._state.get(category, {})


    def clear_category(self, category):
        """Clear all values in a specific category."""
        if category in self._state:
            self._state[category].clear()

    def list_keys(self, category):
        """List all keys in a specific category."""
        return list(self._state.get(category, {}).keys())

if __name__ == "__main__":
    # Access the shared StateManager singleton
    state_manager = StateManager()

    userid, first_name = 123, "Demo"

    # Set a sample state for the user
    state_manager.set_state("other_values", userid, {"started": True, "name": first_name})

    # Retrieve state to use in a reply
    user_state = state_manager.get_state("other_values", userid)
    started = user_state.get("started", False)
    print(started)
"""Admin-controlled Python script executed for every user request.

This is intentionally the only script that the runner executes.
"""

import sys


def main() -> None:
    user_input = sys.stdin.read().strip()

    if not user_input:
        print("No input provided.")
        return

    # Example controlled behavior; replace with your business logic.
    print(f"Received: {user_input}")
    print(f"Uppercase: {user_input.upper()}")
    print(f"Length: {len(user_input)}")


if __name__ == "__main__":
    main()

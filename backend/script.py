"""Admin-controlled Python script executed for every user session.

Users interact with this script through a terminal-like browser UI,
but cannot view or modify this source from the app.
"""


def main() -> None:
    print("Connected to secure Python runner.")
    print("Type text and press Enter. Type 'exit' to end the session.")

    while True:
        try:
            user_input = input("python> ")
        except EOFError:
            break

        text = user_input.strip()
        if not text:
            print("(empty input)")
            continue

        if text.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        print(f"echo: {text}")
        print(f"upper: {text.upper()}")
        print(f"chars: {len(text)}")


if __name__ == "__main__":
    main()

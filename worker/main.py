import time

from app.db.init_db import init_db


def main() -> None:
    init_db()
    print("worker ready: async job hooks initialized; API streams query jobs and eval endpoints run targeted jobs")
    while True:
        time.sleep(30)


if __name__ == "__main__":
    main()

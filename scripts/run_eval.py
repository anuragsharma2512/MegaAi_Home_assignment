from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.eval.harness import EvaluationHarness


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        run = EvaluationHarness(db).run()
        print(run.id)
        print(run.summary)
    finally:
        db.close()


if __name__ == "__main__":
    main()

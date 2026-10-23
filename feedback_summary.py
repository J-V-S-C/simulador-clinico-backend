"""Print aggregate, anonymous post-simulation feedback from the configured database."""
from collections import Counter
from statistics import mean

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from config import Settings
from repositories.database import ExperienceFeedbackRow


def main():
    engine = create_engine(Settings().database_url)
    with Session(engine) as session:
        rows = session.scalars(select(ExperienceFeedbackRow)).all()
    print(f"Respostas: {len(rows)}")
    if not rows:
        return
    print(f"Gostaram: {sum(row.liked for row in rows)} / {len(rows)}")
    print(f"Clareza média: {mean(row.clarity for row in rows):.2f} / 5")
    print(f"Dificuldade média: {mean(row.difficulty for row in rows):.2f} / 5")
    print("Notas de clareza:", dict(sorted(Counter(row.clarity for row in rows).items())))
    print("Notas de dificuldade:", dict(sorted(Counter(row.difficulty for row in rows).items())))
    print("Comentários de melhoria (revisar antes de divulgar):")
    for row in rows:
        if row.improvement:
            print("-", row.improvement)


if __name__ == "__main__":
    main()

from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.db.database import get_engine
from src.db.models import Item, Evaluation
from src.services.hn_ingest import ingest_hackernews
from src.services.prefilter import prefilter_items
from src.services.evaluator import Evaluator
from src.workflows.build_digest import build_digest_for_persona
from src.services.telegram_delivery import build_combined_telegram_text
from src.services.telegram_delivery import (
    build_telegram_text_from_digest_json,
    send_telegram_message,
)
from src.services.dedup import ensure_item_embedding, rebuild_faiss_index_from_db, is_semantic_duplicate


def run_digest() -> dict:
    s = get_settings()
    inserted = ingest_hackernews(limit=30)

    engine = get_engine()

    # 1) Read recent items
    with Session(engine) as session:
        items = (
            session.query(Item)
            .order_by(Item.created_at.desc())
            .limit(100)
            .all()
        )

    # 2) Prefilter (cheap)
    prefiltered = prefilter_items(items)
    candidates = prefiltered[: s.eval_max_items]

    # 2b) Semantic dedup (embeddings + FAISS)
    with Session(engine) as session:
        for it in candidates:
            ensure_item_embedding(session, it)
        session.commit()
        rebuild_faiss_index_from_db(session)

    deduped = []
    with Session(engine) as session:
        for it in candidates:
            dup, near_id, sim = is_semantic_duplicate(session, it)
            if dup:
                print(f"Dedup drop: item {it.id} ~ {near_id} (sim={sim:.2f})")
                continue
            deduped.append(it)

    filtered = deduped

    # 3) Evaluate and store
    evaluator = Evaluator()
    created_evals = 0

    with Session(engine) as session:
        for it in filtered:

            if "GENAI_NEWS" in s.personas_enabled:
                exists = (
                    session.query(Evaluation)
                    .filter_by(item_id=it.id, persona="GENAI_NEWS")
                    .first()
                )
                if not exists:
                    ev = evaluator.eval_genai_news(it)
                    session.add(
                        Evaluation(
                            item_id=it.id,
                            persona="GENAI_NEWS",
                            decision=ev.decision,
                            score=ev.relevance_score,
                            payload_json=ev.model_dump(),
                        )
                    )
                    created_evals += 1

            if "PRODUCT_IDEAS" in s.personas_enabled:
                exists = (
                    session.query(Evaluation)
                    .filter_by(item_id=it.id, persona="PRODUCT_IDEAS")
                    .first()
                )
                if not exists:
                    ev = evaluator.eval_product_ideas(it)
                    session.add(
                        Evaluation(
                            item_id=it.id,
                            persona="PRODUCT_IDEAS",
                            decision=ev.decision,
                            score=ev.reusability_score,
                            payload_json=ev.model_dump(),
                        )
                    )
                    created_evals += 1

        session.commit()

    # 4) Build digests
    digests = [build_digest_for_persona(p) for p in s.personas_enabled]

    # 5) Telegram delivery
    

    try:
        msg = build_combined_telegram_text([d["json_path"] for d in digests])
        send_telegram_message(msg)
    except Exception as e:
        print(f"Telegram delivery failed: {e}")



    return {
        "hackernews_inserted": inserted,
        "items_considered": len(items),
        "items_after_prefilter": len(prefiltered),
        "items_after_dedup": len(filtered),
        "evaluations_created": created_evals,
        "digests": digests,
    }

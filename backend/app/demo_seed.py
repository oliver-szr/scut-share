"""Create an isolated, repeatable dataset for course demonstrations.

The default database lives under ``backend/.local/demo`` and is never the
development database. Use ``--reset`` to recreate that isolated dataset.
"""
from __future__ import annotations

import argparse
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config
from app.core.config import BACKEND_ROOT, Settings
from app.core.security import hash_password
from app.db.session import create_db_engine, create_session_factory
from app.models.borrow_request import BorrowRequest
from app.models.conversation import Conversation, Message
from app.models.gift_request import GiftRequest
from app.models.item import Item
from app.models.trade_intent import TradeIntent
from app.models.user import User

DEFAULT_ROOT = BACKEND_ROOT / ".local" / "demo"
PASSWORD = "Demo-only-password-123"


def migrate(database: Path) -> None:
    engine = create_db_engine(database)
    try:
        with engine.begin() as connection:
            config = Config(str(BACKEND_ROOT / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    finally:
        engine.dispose()


def seed(database: Path) -> None:
    database.parent.mkdir(parents=True, exist_ok=True)
    upload_dir = database.parent / "uploads"
    if database.exists():
        raise SystemExit(f"演示数据库已存在：{database}，如需重置请增加 --reset。")
    migrate(database)
    engine = create_db_engine(database)
    session_factory = create_session_factory(engine)
    now = datetime.now(UTC).replace(microsecond=0)
    with session_factory() as db:
        owner = User(nickname="演示物主", student_no="DEMO_OWNER", password_hash=hash_password(PASSWORD), campus="五山校区")
        buyer = User(nickname="演示买家", student_no="DEMO_BUYER", password_hash=hash_password(PASSWORD), campus="大学城校区")
        helper = User(nickname="演示同学", student_no="DEMO_HELPER", password_hash=hash_password(PASSWORD), campus="广州国际校区")
        db.add_all([owner, buyer, helper])
        db.flush()

        sale = Item(owner_id=owner.id, title="课程相机", description="适合课程拍摄和社团活动，成色良好。", category="数码配件", mode="sale", campus="五山校区", price_cents=12000)
        sale.set_interest_tags(["摄影", "数码"])
        borrow = Item(owner_id=owner.id, title="便携投影仪", description="班级活动可免费借用，请爱惜并按时归还。", category="数码配件", mode="borrow", campus="五山校区", borrow_note="请提前沟通借用时间。")
        borrow.set_interest_tags(["学习", "数码"])
        gift = Item(owner_id=buyer.id, title="闲置教材礼包", description="课程结束后免费转赠给有需要的同学。", category="教材资料", mode="gift", campus="大学城校区")
        gift.set_interest_tags(["学习", "阅读"])
        db.add_all([sale, borrow, gift])
        db.flush()

        trade = TradeIntent(item_id=sale.id, buyer_id=buyer.id, seller_id=owner.id, price_cents_snapshot=12000, status="completed", buyer_confirmed_at=now, seller_confirmed_at=now, completed_at=now)
        borrow_row = BorrowRequest(item_id=borrow.id, owner_id=owner.id, borrower_id=helper.id, requested_start_at=now - timedelta(days=5), expected_return_at=now - timedelta(days=1), status="completed", owner_handover_confirmed_at=now - timedelta(days=5), borrower_handover_confirmed_at=now - timedelta(days=5), owner_return_confirmed_at=now - timedelta(days=1), borrower_return_confirmed_at=now - timedelta(days=1), borrowed_at=now - timedelta(days=5), completed_at=now - timedelta(days=1))
        gift_row = GiftRequest(item_id=gift.id, owner_id=buyer.id, recipient_id=helper.id, note="教学楼一楼交接", status="completed", owner_confirmed_at=now, recipient_confirmed_at=now, completed_at=now)
        db.add_all([trade, borrow_row, gift_row])
        db.flush()

        sale_chat = Conversation(context_type="sale_item", item_id=sale.id, participant_a_id=owner.id, participant_b_id=buyer.id)
        borrow_chat = Conversation(context_type="borrow_request", item_id=borrow.id, borrow_request_id=borrow_row.id, participant_a_id=owner.id, participant_b_id=helper.id)
        db.add_all([sale_chat, borrow_chat])
        db.flush()
        db.add_all([
            Message(conversation_id=sale_chat.id, sender_id=buyer.id, content="你好，课程相机还在吗？"),
            Message(conversation_id=sale_chat.id, sender_id=owner.id, content="还在，教学楼附近可以当面交接。"),
            Message(conversation_id=borrow_chat.id, sender_id=helper.id, content="投影仪借用结束后我已按约归还。"),
        ])
        db.commit()
    engine.dispose()
    upload_dir.mkdir(parents=True, exist_ok=True)
    print(f"演示数据已创建：{database}")
    print(f"演示账户密码统一为：{PASSWORD}")


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化隔离的 SCUT Share 课程演示数据库")
    parser.add_argument("--database", type=Path, default=DEFAULT_ROOT / "demo.db")
    parser.add_argument("--reset", action="store_true", help="删除指定演示数据库及其 uploads 后重新创建")
    args = parser.parse_args()
    database = args.database.expanduser().resolve()
    if args.reset:
        if database == Settings().resolved_database_path or DEFAULT_ROOT not in database.parents:
            raise SystemExit("拒绝重置开发数据库或任意非 demo 路径，请使用 backend/.local/demo。")
        shutil.rmtree(database.parent, ignore_errors=True)
    seed(database)


if __name__ == "__main__":
    main()

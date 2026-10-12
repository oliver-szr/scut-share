"""Local developer-only admin grant/revoke by internal ID. No HTTP role mutation."""
import argparse
from pathlib import Path

from sqlalchemy import update

from app.core.config import Settings
from app.db.session import create_db_engine, create_session_factory
from app.models.user import User


def main():
    parser = argparse.ArgumentParser(description="本地授权/撤销管理员，只使用内部用户 ID")
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--revoke", action="store_true")
    parser.add_argument("--database", type=Path, help="可选：明确指定已有隔离库；默认使用项目配置")
    args = parser.parse_args()
    path = args.database or Settings().resolved_database_path
    if args.user_id < 1 or not path.is_file():
        parser.error("必须指定正整数内部 ID 和已有数据库；请先执行迁移。")
    engine = create_db_engine(path)
    try:
        with create_session_factory(engine)() as db:
            result = db.execute(update(User).where(User.id == args.user_id).values(is_admin=not args.revoke))
            if result.rowcount != 1:
                parser.error("该内部用户 ID 不存在。")
            db.commit()
        print(f"用户 #{args.user_id} 管理员权限已{'撤销' if args.revoke else '授予'}。")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.dependencies import AuthenticatedUser, DbSession, require_trusted_origin
from app.core.constants import ItemMode, ItemStatus
from app.db.session import begin_item_write
from app.models.item import Item
from app.models.trade_intent import TradeIntent
from app.schemas.trade import TradeIntentCreate, TradeListResponse, TradeResponse

router = APIRouter(tags=["trades"])
trusted_origin = [Depends(require_trusted_origin)]


def _options():
    return (selectinload(TradeIntent.item).selectinload(Item.images), selectinload(TradeIntent.buyer), selectinload(TradeIntent.seller))


def _serialize(trade: TradeIntent) -> TradeResponse:
    return TradeResponse(
        **{name: getattr(trade, name) for name in (
            "id", "item_id", "buyer_id", "seller_id", "price_cents_snapshot", "note", "status",
            "buyer_confirmed_at", "seller_confirmed_at", "created_at", "updated_at", "completed_at",
        )},
        item={"id": trade.item.id, "title": trade.item.title, "images": [
            {"id": image.id, "url": f"/api/items/images/{image.file_name}", "content_type": image.content_type}
            for image in trade.item.images
        ]},
        buyer={"id": trade.buyer.id, "nickname": trade.buyer.nickname},
        seller={"id": trade.seller.id, "nickname": trade.seller.nickname},
    )


def _get_trade(db, trade_id: int, user_id: int) -> TradeIntent:
    trade = db.scalar(select(TradeIntent).options(*_options()).where(
        TradeIntent.id == trade_id, or_(TradeIntent.buyer_id == user_id, TradeIntent.seller_id == user_id),
    ))
    if trade is None:
        raise HTTPException(status_code=404, detail="交易不存在或无权访问。")
    return trade


def _commit(db, trade_id: int, user_id: int) -> TradeResponse:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="交易状态已变化或已有有效申请，请刷新后重试。") from None
    db.expire_all()
    return _serialize(_get_trade(db, trade_id, user_id))


def _require_pending(trade: TradeIntent) -> None:
    if trade.status != "pending":
        raise HTTPException(status_code=409, detail="申请已处理，当前状态不允许此操作。")


@router.post("/items/{item_id}/trade-intents", response_model=TradeResponse, status_code=201, dependencies=trusted_origin)
def create_intent(item_id: int, payload: TradeIntentCreate, user: AuthenticatedUser, db: DbSession) -> TradeResponse:
    begin_item_write(db)
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="物品不存在。")
    if item.owner_id == user.id:
        raise HTTPException(status_code=409, detail="不能购买自己发布的物品。")
    if item.mode != ItemMode.SALE or item.status != ItemStatus.PUBLISHED or item.availability != "available":
        raise HTTPException(status_code=409, detail="仅正常在售且未预留的二手商品可以申请购买。")
    if db.scalar(select(TradeIntent.id).where(
        TradeIntent.item_id == item_id, TradeIntent.buyer_id == user.id, TradeIntent.status.in_(["pending", "reserved"]),
    ).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="你已有有效购买申请，请到我的交易查看。")
    trade = TradeIntent(item_id=item_id, buyer_id=user.id, seller_id=item.owner_id, price_cents_snapshot=item.price_cents, note=payload.note)
    db.add(trade)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="已有有效购买申请，请刷新后重试。") from None
    return _commit(db, trade.id, user.id)


@router.get("/trades/mine", response_model=TradeListResponse)
def my_trades(user: AuthenticatedUser, db: DbSession, role: Literal["buyer", "seller"] | None = None,
              page: int = Query(default=1, ge=1, le=10_000), page_size: int = Query(default=20, ge=1, le=50)) -> TradeListResponse:
    scope = (TradeIntent.buyer_id == user.id if role == "buyer" else TradeIntent.seller_id == user.id if role == "seller"
             else or_(TradeIntent.buyer_id == user.id, TradeIntent.seller_id == user.id))
    total = db.scalar(select(func.count()).select_from(TradeIntent).where(scope)) or 0
    trades = db.scalars(select(TradeIntent).options(*_options()).where(scope)
                        .order_by(TradeIntent.created_at.desc(), TradeIntent.id.desc())
                        .offset((page - 1) * page_size).limit(page_size)).all()
    return TradeListResponse(trades=[_serialize(trade) for trade in trades], total=total, page=page, page_size=page_size)


@router.post("/trades/{trade_id}/accept", response_model=TradeResponse, dependencies=trusted_origin)
def accept(trade_id: int, user: AuthenticatedUser, db: DbSession) -> TradeResponse:
    begin_item_write(db)
    trade = _get_trade(db, trade_id, user.id)
    if trade.seller_id != user.id:
        raise HTTPException(status_code=403, detail="只有卖家可以接受申请。")
    _require_pending(trade)
    if trade.item.mode != ItemMode.SALE or trade.item.status != ItemStatus.PUBLISHED or trade.item.availability != "available":
        raise HTTPException(status_code=409, detail="商品已不可预留，请刷新交易状态。")
    trade.status = "reserved"
    # Rejection and reservation commit together, so other buyers cannot slip in.
    db.execute(update(TradeIntent).where(
        TradeIntent.item_id == trade.item_id, TradeIntent.id != trade.id, TradeIntent.status == "pending",
    ).values(status="rejected", updated_at=datetime.now(UTC)))
    return _commit(db, trade.id, user.id)


@router.post("/trades/{trade_id}/reject", response_model=TradeResponse, dependencies=trusted_origin)
def reject(trade_id: int, user: AuthenticatedUser, db: DbSession) -> TradeResponse:
    begin_item_write(db)
    trade = _get_trade(db, trade_id, user.id)
    if trade.seller_id != user.id:
        raise HTTPException(status_code=403, detail="只有卖家可以拒绝申请。")
    _require_pending(trade)
    trade.status = "rejected"
    return _commit(db, trade.id, user.id)


@router.post("/trades/{trade_id}/cancel", response_model=TradeResponse, dependencies=trusted_origin)
def cancel(trade_id: int, user: AuthenticatedUser, db: DbSession) -> TradeResponse:
    begin_item_write(db)
    trade = _get_trade(db, trade_id, user.id)
    if trade.status == "pending":
        if trade.buyer_id != user.id:
            raise HTTPException(status_code=403, detail="卖家请使用拒绝申请，只有买家可以取消待处理申请。")
    elif trade.status == "reserved":
        if trade.buyer_confirmed_at is not None or trade.seller_confirmed_at is not None:
            raise HTTPException(status_code=409, detail="已有一方确认成交，不能单方面取消，请双方联系解决。可在交易记录提交举报请求人工处理。")
    elif trade.status != "canceled":
        raise HTTPException(status_code=409, detail="当前交易状态不能取消。")
    trade.status = "canceled"
    return _commit(db, trade.id, user.id)


@router.post("/trades/{trade_id}/confirm", response_model=TradeResponse, dependencies=trusted_origin)
def confirm(trade_id: int, user: AuthenticatedUser, db: DbSession) -> TradeResponse:
    begin_item_write(db)
    trade = _get_trade(db, trade_id, user.id)
    if trade.status not in ("reserved", "completed"):
        raise HTTPException(status_code=409, detail="仅已预留的交易可以确认成交。")
    if trade.status == "reserved":
        now = datetime.now(UTC)
        field = "buyer_confirmed_at" if trade.buyer_id == user.id else "seller_confirmed_at"
        if getattr(trade, field) is None:
            setattr(trade, field, now)
        if trade.buyer_confirmed_at is not None and trade.seller_confirmed_at is not None:
            trade.status, trade.completed_at = "completed", now
    return _commit(db, trade.id, user.id)

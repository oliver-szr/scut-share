from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.dependencies import AuthenticatedUser, DbSession, require_trusted_origin
from app.core.constants import ItemMode, ItemStatus
from app.db.session import begin_item_write
from app.models.gift_request import GiftRequest
from app.models.item import Item
from app.schemas.gift import GiftCreate, GiftList, GiftResponse

router = APIRouter(tags=["gifts"])
trusted_origin = [Depends(require_trusted_origin)]


def _get(db, gift_id, user_id):
    row = db.scalar(select(GiftRequest).options(selectinload(GiftRequest.item).selectinload(Item.images), selectinload(GiftRequest.owner), selectinload(GiftRequest.recipient))
                    .where(GiftRequest.id == gift_id, or_(GiftRequest.owner_id == user_id, GiftRequest.recipient_id == user_id)))
    if row is None:
        raise HTTPException(status_code=404, detail="转赠申请不存在或无权访问。")
    return row


def _serialize(row):
    return GiftResponse(**{name: getattr(row, name) for name in ("id", "item_id", "owner_id", "recipient_id", "note", "status", "owner_confirmed_at", "recipient_confirmed_at", "completed_at", "created_at", "updated_at")},
        item={"id": row.item_id, "title": row.item.title, "images": [{"id": image.id, "url": f"/api/items/images/{image.file_name}", "content_type": image.content_type} for image in row.item.images]},
        owner={"id": row.owner_id, "nickname": row.owner.nickname}, recipient={"id": row.recipient_id, "nickname": row.recipient.nickname})


def _commit(db, row, user_id):
    try:
        db.flush(); gift_id = row.id; db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="已有有效领取申请或物品已锁定，请刷新后重试。") from None
    db.expire_all()
    return _serialize(_get(db, gift_id, user_id))


@router.post("/items/{item_id}/gift-requests", response_model=GiftResponse, status_code=201, dependencies=trusted_origin)
def create(item_id: int, payload: GiftCreate, user: AuthenticatedUser, db: DbSession):
    begin_item_write(db)
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="物品不存在。")
    if item.owner_id == user.id:
        raise HTTPException(status_code=409, detail="不能申请领取自己的物品。")
    if item.mode != ItemMode.GIFT or item.status != ItemStatus.PUBLISHED or item.availability != "available":
        raise HTTPException(status_code=409, detail="只有正常发布且未锁定的免费转赠物品可以申请领取。")
    if db.scalar(select(GiftRequest.id).where(GiftRequest.item_id == item_id, GiftRequest.recipient_id == user.id, GiftRequest.status.in_(["pending", "approved"])).limit(1)):
        raise HTTPException(status_code=409, detail="你已有有效领取申请，请查看我的转赠。")
    row = GiftRequest(item_id=item_id, owner_id=item.owner_id, recipient_id=user.id, note=payload.note)
    db.add(row)
    return _commit(db, row, user.id)


@router.get("/gifts/mine", response_model=GiftList)
def mine(user: AuthenticatedUser, db: DbSession, role: Literal["owner", "recipient"] | None = None,
         page: int = Query(1, ge=1, le=10000), page_size: int = Query(20, ge=1, le=50)):
    scope = GiftRequest.owner_id == user.id if role == "owner" else GiftRequest.recipient_id == user.id if role == "recipient" else or_(GiftRequest.owner_id == user.id, GiftRequest.recipient_id == user.id)
    total = db.scalar(select(func.count()).select_from(GiftRequest).where(scope)) or 0
    ids = db.scalars(select(GiftRequest.id).where(scope).order_by(GiftRequest.created_at.desc(), GiftRequest.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return GiftList(gifts=[_serialize(_get(db, gift_id, user.id)) for gift_id in ids], total=total, page=page, page_size=page_size)


@router.post("/gifts/{gift_id}/{action}", response_model=GiftResponse, dependencies=trusted_origin)
def act(gift_id: int, action: Literal["approve", "reject", "cancel", "confirm"], user: AuthenticatedUser, db: DbSession):
    begin_item_write(db)
    row = _get(db, gift_id, user.id)
    if action in ("approve", "reject"):
        if row.owner_id != user.id:
            raise HTTPException(status_code=403, detail="只有物主可以审核领取申请。")
        if row.status != "pending":
            raise HTTPException(status_code=409, detail="申请已处理，不能再次审核。")
        if action == "approve":
            if row.item.mode != ItemMode.GIFT or row.item.status != ItemStatus.PUBLISHED or row.item.availability != "available":
                raise HTTPException(status_code=409, detail="物品已不可转赠。")
            row.status = "approved"
            db.execute(update(GiftRequest).where(GiftRequest.item_id == row.item_id, GiftRequest.id != row.id, GiftRequest.status == "pending").values(status="rejected", updated_at=datetime.now(UTC)))
        else:
            row.status = "rejected"
    elif action == "cancel":
        if row.status == "pending":
            if row.recipient_id != user.id:
                raise HTTPException(status_code=403, detail="物主请拒绝申请，只有申请人可取消待处理申请。")
        elif row.status == "approved":
            if row.owner_confirmed_at or row.recipient_confirmed_at:
                raise HTTPException(status_code=409, detail="已有一方确认交接，不能单方面取消。")
        elif row.status != "canceled":
            raise HTTPException(status_code=409, detail="当前转赠状态不能取消。")
        row.status = "canceled"
    else:
        if row.status not in ("approved", "completed"):
            raise HTTPException(status_code=409, detail="只有已同意的转赠可以确认交接。")
        if row.status == "approved":
            now = datetime.now(UTC)
            field = "owner_confirmed_at" if row.owner_id == user.id else "recipient_confirmed_at"
            if getattr(row, field) is None:
                setattr(row, field, now)
            if row.owner_confirmed_at and row.recipient_confirmed_at:
                row.status, row.completed_at = "completed", now
    return _commit(db, row, user.id)

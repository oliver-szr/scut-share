from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.dependencies import AuthenticatedUser, DbSession, require_trusted_origin
from app.core.constants import ItemMode, ItemStatus
from app.db.session import begin_item_write
from app.models.borrow_request import BorrowRequest
from app.models.item import Item
from app.schemas.borrow import BorrowListResponse, BorrowRequestCreate, BorrowResponse

router = APIRouter(tags=["borrows"])
trusted_origin = [Depends(require_trusted_origin)]


def _options():
    return (selectinload(BorrowRequest.item).selectinload(Item.images), selectinload(BorrowRequest.owner), selectinload(BorrowRequest.borrower))


def _serialize(borrow: BorrowRequest) -> BorrowResponse:
    return BorrowResponse(
        **{name: getattr(borrow, name) for name in (
            "id", "item_id", "owner_id", "borrower_id", "requested_start_at", "expected_return_at", "note", "status",
            "owner_handover_confirmed_at", "borrower_handover_confirmed_at", "owner_return_confirmed_at", "borrower_return_confirmed_at",
            "created_at", "updated_at", "borrowed_at", "completed_at",
        )},
        item={"id": borrow.item.id, "title": borrow.item.title, "images": [
            {"id": image.id, "url": f"/api/items/images/{image.file_name}", "content_type": image.content_type}
            for image in borrow.item.images
        ]},
        owner={"id": borrow.owner.id, "nickname": borrow.owner.nickname},
        borrower={"id": borrow.borrower.id, "nickname": borrow.borrower.nickname},
    )


def _get_borrow(db, borrow_id: int, user_id: int) -> BorrowRequest:
    borrow = db.scalar(select(BorrowRequest).options(*_options()).where(
        BorrowRequest.id == borrow_id, or_(BorrowRequest.owner_id == user_id, BorrowRequest.borrower_id == user_id),
    ))
    if borrow is None:
        raise HTTPException(status_code=404, detail="借用记录不存在或无权访问。")
    return borrow


def _commit(db, borrow_id: int, user_id: int) -> BorrowResponse:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="借用状态已变化或已有有效申请，请刷新后重试。") from None
    db.expire_all()
    return _serialize(_get_borrow(db, borrow_id, user_id))


def _require_pending(borrow: BorrowRequest) -> None:
    if borrow.status != "pending":
        raise HTTPException(status_code=409, detail="申请已处理，当前状态不允许此操作。")


@router.post("/items/{item_id}/borrow-requests", response_model=BorrowResponse, status_code=201, dependencies=trusted_origin)
def create_request(item_id: int, payload: BorrowRequestCreate, user: AuthenticatedUser, db: DbSession) -> BorrowResponse:
    begin_item_write(db)
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="物品不存在。")
    if item.owner_id == user.id:
        raise HTTPException(status_code=409, detail="不能申请自己发布的物品。")
    if item.mode != ItemMode.BORROW or item.status != ItemStatus.PUBLISHED or item.availability != "available":
        raise HTTPException(status_code=409, detail="仅正常发布且可借的免费借还物品可以申请。")
    if db.scalar(select(BorrowRequest.id).where(
        BorrowRequest.item_id == item_id, BorrowRequest.borrower_id == user.id,
        BorrowRequest.status.in_(["pending", "approved", "borrowed", "return_pending"]),
    ).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="你已有未结束的借用申请，请到我的借还查看。")
    borrow = BorrowRequest(item_id=item_id, owner_id=item.owner_id, borrower_id=user.id,
                           requested_start_at=payload.requested_start_at, expected_return_at=payload.expected_return_at, note=payload.note)
    db.add(borrow)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="已有有效借用申请，请刷新后重试。") from None
    return _commit(db, borrow.id, user.id)


@router.get("/borrows/mine", response_model=BorrowListResponse)
def my_borrows(user: AuthenticatedUser, db: DbSession, role: Literal["borrower", "owner"] | None = None,
               page: int = Query(default=1, ge=1, le=10_000), page_size: int = Query(default=20, ge=1, le=50)) -> BorrowListResponse:
    scope = (BorrowRequest.borrower_id == user.id if role == "borrower" else BorrowRequest.owner_id == user.id if role == "owner"
             else or_(BorrowRequest.borrower_id == user.id, BorrowRequest.owner_id == user.id))
    total = db.scalar(select(func.count()).select_from(BorrowRequest).where(scope)) or 0
    borrows = db.scalars(select(BorrowRequest).options(*_options()).where(scope)
                         .order_by(BorrowRequest.created_at.desc(), BorrowRequest.id.desc())
                         .offset((page - 1) * page_size).limit(page_size)).all()
    return BorrowListResponse(borrows=[_serialize(borrow) for borrow in borrows], total=total, page=page, page_size=page_size)


@router.post("/borrows/{borrow_id}/approve", response_model=BorrowResponse, dependencies=trusted_origin)
def approve(borrow_id: int, user: AuthenticatedUser, db: DbSession) -> BorrowResponse:
    begin_item_write(db)
    borrow = _get_borrow(db, borrow_id, user.id)
    if borrow.owner_id != user.id:
        raise HTTPException(status_code=403, detail="只有物主可以同意借用。")
    _require_pending(borrow)
    if borrow.item.mode != ItemMode.BORROW or borrow.item.status != ItemStatus.PUBLISHED or borrow.item.availability != "available":
        raise HTTPException(status_code=409, detail="物品已不可借，请刷新状态。")
    borrow.status = "approved"
    db.execute(update(BorrowRequest).where(
        BorrowRequest.item_id == borrow.item_id, BorrowRequest.id != borrow.id, BorrowRequest.status == "pending",
    ).values(status="rejected", updated_at=datetime.now(UTC)))
    return _commit(db, borrow.id, user.id)


@router.post("/borrows/{borrow_id}/reject", response_model=BorrowResponse, dependencies=trusted_origin)
def reject(borrow_id: int, user: AuthenticatedUser, db: DbSession) -> BorrowResponse:
    begin_item_write(db)
    borrow = _get_borrow(db, borrow_id, user.id)
    if borrow.owner_id != user.id:
        raise HTTPException(status_code=403, detail="只有物主可以拒绝借用。")
    _require_pending(borrow)
    borrow.status = "rejected"
    return _commit(db, borrow.id, user.id)


@router.post("/borrows/{borrow_id}/cancel", response_model=BorrowResponse, dependencies=trusted_origin)
def cancel(borrow_id: int, user: AuthenticatedUser, db: DbSession) -> BorrowResponse:
    begin_item_write(db)
    borrow = _get_borrow(db, borrow_id, user.id)
    if borrow.status == "pending":
        if borrow.borrower_id != user.id:
            raise HTTPException(status_code=403, detail="物主请使用拒绝申请，只有借用人可以取消待处理申请。")
    elif borrow.status == "approved":
        if borrow.owner_handover_confirmed_at is not None or borrow.borrower_handover_confirmed_at is not None:
            raise HTTPException(status_code=409, detail="已有一方确认交接，不能单方面取消，请双方联系解决。可在借还记录提交举报请求人工处理。")
    elif borrow.status != "canceled":
        raise HTTPException(status_code=409, detail="当前借用状态不能取消，请完成双方归还确认。")
    borrow.status = "canceled"
    return _commit(db, borrow.id, user.id)


@router.post("/borrows/{borrow_id}/confirm-handover", response_model=BorrowResponse, dependencies=trusted_origin)
def confirm_handover(borrow_id: int, user: AuthenticatedUser, db: DbSession) -> BorrowResponse:
    begin_item_write(db)
    borrow = _get_borrow(db, borrow_id, user.id)
    if borrow.status not in ("approved", "borrowed", "return_pending", "completed"):
        raise HTTPException(status_code=409, detail="仅已同意的借用可以确认交接。")
    if borrow.status == "approved":
        now = datetime.now(UTC)
        field = "owner_handover_confirmed_at" if borrow.owner_id == user.id else "borrower_handover_confirmed_at"
        if getattr(borrow, field) is None:
            setattr(borrow, field, now)
        if borrow.owner_handover_confirmed_at is not None and borrow.borrower_handover_confirmed_at is not None:
            borrow.status, borrow.borrowed_at = "borrowed", now
    return _commit(db, borrow.id, user.id)


@router.post("/borrows/{borrow_id}/confirm-return", response_model=BorrowResponse, dependencies=trusted_origin)
def confirm_return(borrow_id: int, user: AuthenticatedUser, db: DbSession) -> BorrowResponse:
    begin_item_write(db)
    borrow = _get_borrow(db, borrow_id, user.id)
    if borrow.status not in ("borrowed", "return_pending", "completed"):
        raise HTTPException(status_code=409, detail="双方确认借出后才能确认归还。")
    if borrow.status != "completed":
        now = datetime.now(UTC)
        field = "owner_return_confirmed_at" if borrow.owner_id == user.id else "borrower_return_confirmed_at"
        if getattr(borrow, field) is None:
            setattr(borrow, field, now)
        if borrow.owner_return_confirmed_at is not None and borrow.borrower_return_confirmed_at is not None:
            borrow.status, borrow.completed_at = "completed", now
        else:
            borrow.status = "return_pending"
    return _commit(db, borrow.id, user.id)

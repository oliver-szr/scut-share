import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.dependencies import AdminUser, AuthenticatedUser, DbSession, require_trusted_origin
from app.core.constants import ItemStatus
from app.db.session import begin_item_write
from app.models.borrow_request import BorrowRequest
from app.models.conversation import Conversation, Message
from app.models.item import Item
from app.models.report import Report, ReportAppeal
from app.models.trade_intent import TradeIntent
from app.schemas.report import AppealCreate, ReportCreate, ReportDetail, ReportList, ReportResponse, ReportStatus, ResolutionCreate

router = APIRouter(tags=["reports"])
trusted_origin = [Depends(require_trusted_origin)]


def _evidence(db, kind: str, target_id: int, user_id: int) -> dict:
    # Validate access first. A report captures only this selected object's limited
    # evidence; admin review never becomes a general private-record lookup API.
    if kind == "item":
        row = db.scalar(select(Item).where(Item.id == target_id, or_(Item.status == ItemStatus.PUBLISHED, Item.owner_id == user_id)))
        if row is not None:
            return {"item_id": row.id, "title": row.title, "description": row.description, "mode": row.mode.value, "owner": {"id": row.owner_id, "nickname": row.owner.nickname}}
    elif kind in ("trade", "borrow"):
        model = TradeIntent if kind == "trade" else BorrowRequest
        a, b = (model.seller_id, model.buyer_id) if kind == "trade" else (model.owner_id, model.borrower_id)
        row = db.scalar(select(model).where(model.id == target_id, or_(a == user_id, b == user_id)))
        if row is not None:
            evidence = {"record_id": row.id, "item_id": row.item_id, "title": row.item.title, "status": row.status, "note": row.note}
            if kind == "trade":
                evidence.update(price_cents_snapshot=row.price_cents_snapshot, seller_id=row.seller_id, buyer_id=row.buyer_id)
            else:
                evidence.update(owner_id=row.owner_id, borrower_id=row.borrower_id,
                                expected_return_at=row.expected_return_at.replace(tzinfo=UTC).isoformat())
            return evidence
    elif kind == "message":
        row = db.scalar(select(Message).join(Conversation, Message.conversation_id == Conversation.id).where(
            Message.id == target_id, or_(Conversation.participant_a_id == user_id, Conversation.participant_b_id == user_id)))
        if row is not None:
            return {"message_id": row.id, "conversation_id": row.conversation_id, "sender_id": row.sender_id,
                    "content": row.content, "created_at": row.created_at.replace(tzinfo=UTC).isoformat()}
    raise HTTPException(status_code=404, detail="举报对象不存在或无权访问。")


def _get(db, report_id: int, reporter_id: int | None = None) -> Report:
    query = select(Report).options(selectinload(Report.appeal)).where(Report.id == report_id)
    if reporter_id is not None:
        query = query.where(Report.reporter_id == reporter_id)
    row = db.scalar(query)
    if row is None:
        raise HTTPException(status_code=404, detail="举报不存在或无权访问。")
    return row


def _detail(row: Report) -> ReportDetail:
    return ReportDetail(**ReportResponse.model_validate(row).model_dump(), evidence=json.loads(row.evidence_json))


@router.post("/reports", response_model=ReportResponse, status_code=201, dependencies=trusted_origin)
def create_report(payload: ReportCreate, user: AuthenticatedUser, db: DbSession):
    begin_item_write(db)
    evidence = _evidence(db, payload.target_type, payload.target_id, user.id)
    row = Report(reporter_id=user.id, target_type=payload.target_type, target_id=payload.target_id,
                 reason=payload.reason, description=payload.description, evidence_json=json.dumps(evidence, ensure_ascii=False))
    db.add(row); db.commit()
    return ReportResponse.model_validate(_get(db, row.id, user.id))


def _list(db, filters, page, page_size) -> ReportList:
    total = db.scalar(select(func.count()).select_from(Report).where(*filters)) or 0
    rows = db.scalars(select(Report).options(selectinload(Report.appeal)).where(*filters)
                      .order_by(Report.created_at.desc(), Report.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return ReportList(reports=[ReportResponse.model_validate(row) for row in rows], total=total, page=page, page_size=page_size)


@router.get("/reports/mine", response_model=ReportList)
def mine(user: AuthenticatedUser, db: DbSession, page: int = Query(1, ge=1, le=10000), page_size: int = Query(20, ge=1, le=50)):
    return _list(db, [Report.reporter_id == user.id], page, page_size)


@router.get("/reports/{report_id}", response_model=ReportDetail)
def detail(report_id: int, user: AuthenticatedUser, db: DbSession):
    return _detail(_get(db, report_id, user.id))


@router.post("/reports/{report_id}/appeal", response_model=ReportResponse, dependencies=trusted_origin)
def appeal(report_id: int, payload: AppealCreate, user: AuthenticatedUser, db: DbSession):
    begin_item_write(db)
    row = _get(db, report_id, user.id)
    if row.status == "pending" or row.appeal is not None:
        raise HTTPException(status_code=409, detail="举报处理后只能提交一次复核申诉。")
    db.add(ReportAppeal(report_id=row.id, reason=payload.reason)); db.commit(); db.expire_all()
    return ReportResponse.model_validate(_get(db, report_id, user.id))


@router.get("/admin/reports", response_model=ReportList)
def admin_list(user: AdminUser, db: DbSession, status: ReportStatus | None = None, appeal_pending: bool = False,
               page: int = Query(1, ge=1, le=10000), page_size: int = Query(20, ge=1, le=50)):
    filters = [Report.status == status] if status else []
    if appeal_pending:
        filters.append(Report.appeal.has(ReportAppeal.status == "pending"))
    return _list(db, filters, page, page_size)


@router.get("/admin/reports/{report_id}", response_model=ReportDetail)
def admin_detail(report_id: int, user: AdminUser, db: DbSession):
    return _detail(_get(db, report_id))


@router.post("/admin/reports/{report_id}/resolve", response_model=ReportResponse, dependencies=trusted_origin)
def resolve(report_id: int, payload: ResolutionCreate, user: AdminUser, db: DbSession):
    begin_item_write(db)
    row = _get(db, report_id)
    if row.status != "pending":
        raise HTTPException(status_code=409, detail="举报已处理，请通过申诉复核流程记录后续结果。")
    row.status, row.resolution_note, row.reviewer_id, row.resolved_at = payload.status, payload.note, user.id, datetime.now(UTC)
    db.commit()
    return ReportResponse.model_validate(row)


@router.post("/admin/reports/{report_id}/appeal-review", response_model=ReportResponse, dependencies=trusted_origin)
def review(report_id: int, payload: ResolutionCreate, user: AdminUser, db: DbSession):
    begin_item_write(db)
    row = _get(db, report_id)
    if row.appeal is None or row.appeal.status != "pending":
        raise HTTPException(status_code=409, detail="没有待复核申诉。")
    row.appeal.status, row.appeal.decision, row.appeal.review_note = "reviewed", payload.status, payload.note
    row.appeal.reviewer_id, row.appeal.reviewed_at = user.id, datetime.now(UTC)
    db.commit()
    return ReportResponse.model_validate(row)

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.dependencies import AuthenticatedUser, DbSession, require_trusted_origin
from app.core.constants import ItemMode, ItemStatus
from app.db.session import begin_item_write
from app.models.borrow_request import BorrowRequest
from app.models.conversation import Conversation, Message
from app.models.item import Item
from app.models.trade_intent import TradeIntent
from app.schemas.conversation import ConversationCreate, ConversationListResponse, ConversationResponse, MessageCreate, MessageListResponse, MessageResponse

router = APIRouter(tags=["conversations"])
trusted_origin = [Depends(require_trusted_origin)]


def _scope(user_id):
    return or_(Conversation.participant_a_id == user_id, Conversation.participant_b_id == user_id)


def _options():
    return (selectinload(Conversation.item).selectinload(Item.images), selectinload(Conversation.participant_a), selectinload(Conversation.participant_b))


def _get_conversation(db, conversation_id: int, user_id: int) -> Conversation:
    conversation = db.scalar(select(Conversation).options(*_options()).where(Conversation.id == conversation_id, _scope(user_id)))
    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问。")
    return conversation


def _serialize(db, conversation: Conversation, user_id: int) -> ConversationResponse:
    other = conversation.participant_b if conversation.participant_a_id == user_id else conversation.participant_a
    last = db.scalar(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.id.desc()).limit(1))
    preview = MessageResponse.model_validate(last) if last is not None else None
    if preview is not None:
        preview.content = preview.content[:100]
    return ConversationResponse(
        id=conversation.id, context_type=conversation.context_type, item_id=conversation.item_id,
        borrow_request_id=conversation.borrow_request_id, other_user={"id": other.id, "nickname": other.nickname},
        item={"id": conversation.item.id, "title": conversation.item.title, "images": [
            {"id": image.id, "url": f"/api/items/images/{image.file_name}", "content_type": image.content_type}
            for image in conversation.item.images
        ]},
        last_message=preview, last_message_at=last.created_at if last is not None else None,
        created_at=conversation.created_at, updated_at=conversation.updated_at,
    )


def _sale_pair(db, item_id: int, owner_id: int, buyer_id: int):
    return db.scalar(select(Conversation).options(*_options()).where(
        Conversation.context_type == "sale_item", Conversation.item_id == item_id,
        Conversation.participant_a_id == owner_id, Conversation.participant_b_id == buyer_id,
    ))


def _create(db, user_id: int, **values) -> ConversationResponse:
    now = datetime.now(UTC)
    conversation = Conversation(**values, created_at=now, updated_at=now)
    db.add(conversation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="会话已存在或状态已变化，请刷新后重试。") from None
    return _serialize(db, _get_conversation(db, conversation.id, user_id), user_id)


@router.post("/items/{item_id}/conversations", response_model=ConversationResponse, dependencies=trusted_origin)
def sale_conversation(item_id: int, user: AuthenticatedUser, db: DbSession, payload: ConversationCreate | None = None) -> ConversationResponse:
    begin_item_write(db)
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="物品不存在。")
    if item.owner_id == user.id:
        raise HTTPException(status_code=409, detail="不能与自己创建咨询会话。")
    existing = _sale_pair(db, item_id, item.owner_id, user.id)
    if existing is not None:
        return _serialize(db, existing, user.id)
    if item.mode != ItemMode.SALE or item.status != ItemStatus.PUBLISHED or item.availability != "available":
        raise HTTPException(status_code=409, detail="当前商品不可新建咨询会话；已有会话可从我的消息继续访问。")
    return _create(db, user.id, context_type="sale_item", item_id=item_id, participant_a_id=item.owner_id, participant_b_id=user.id)


@router.post("/trades/{trade_id}/conversation", response_model=ConversationResponse, dependencies=trusted_origin)
def trade_conversation(trade_id: int, user: AuthenticatedUser, db: DbSession, payload: ConversationCreate | None = None) -> ConversationResponse:
    begin_item_write(db)
    trade = db.scalar(select(TradeIntent).where(TradeIntent.id == trade_id, or_(TradeIntent.buyer_id == user.id, TradeIntent.seller_id == user.id)))
    if trade is None:
        raise HTTPException(status_code=404, detail="交易不存在或无权访问。")
    existing = _sale_pair(db, trade.item_id, trade.seller_id, trade.buyer_id)
    if existing is not None:
        return _serialize(db, existing, user.id)
    item = trade.item
    if trade.status not in ("pending", "reserved") or item.mode != ItemMode.SALE or item.status != ItemStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="当前交易不能新建会话；已存在的聊天记录仍保留在我的消息中。")
    if item.availability != "available" and trade.status != "reserved":
        raise HTTPException(status_code=409, detail="商品已有其他预留，当前申请不能新建会话。")
    return _create(db, user.id, context_type="sale_item", item_id=trade.item_id, participant_a_id=trade.seller_id, participant_b_id=trade.buyer_id)


@router.post("/borrows/{borrow_id}/conversation", response_model=ConversationResponse, dependencies=trusted_origin)
def borrow_conversation(borrow_id: int, user: AuthenticatedUser, db: DbSession, payload: ConversationCreate | None = None) -> ConversationResponse:
    begin_item_write(db)
    borrow = db.scalar(select(BorrowRequest).where(BorrowRequest.id == borrow_id, or_(BorrowRequest.owner_id == user.id, BorrowRequest.borrower_id == user.id)))
    if borrow is None:
        raise HTTPException(status_code=404, detail="借用记录不存在或无权访问。")
    if borrow.status not in ("approved", "borrowed", "return_pending", "completed"):
        raise HTTPException(status_code=409, detail="借用申请需获物主同意后才开放聊天。")
    existing = db.scalar(select(Conversation).options(*_options()).where(Conversation.borrow_request_id == borrow_id, Conversation.context_type == "borrow_request"))
    if existing is not None:
        return _serialize(db, existing, user.id)
    return _create(db, user.id, context_type="borrow_request", item_id=borrow.item_id, borrow_request_id=borrow.id,
                   participant_a_id=borrow.owner_id, participant_b_id=borrow.borrower_id)


@router.get("/conversations", response_model=ConversationListResponse)
def my_conversations(user: AuthenticatedUser, db: DbSession, page: int = Query(default=1, ge=1, le=10_000), page_size: int = Query(default=20, ge=1, le=50)) -> ConversationListResponse:
    total = db.scalar(select(func.count()).select_from(Conversation).where(_scope(user.id))) or 0
    conversations = db.scalars(select(Conversation).options(*_options()).where(_scope(user.id))
                               .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
                               .offset((page - 1) * page_size).limit(page_size)).all()
    return ConversationListResponse(conversations=[_serialize(db, conversation, user.id) for conversation in conversations], total=total, page=page, page_size=page_size)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def conversation_detail(conversation_id: int, user: AuthenticatedUser, db: DbSession) -> ConversationResponse:
    return _serialize(db, _get_conversation(db, conversation_id, user.id), user.id)


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
def message_history(conversation_id: int, user: AuthenticatedUser, db: DbSession,
                    before_id: int | None = Query(default=None, gt=0), after_id: int | None = Query(default=None, ge=0),
                    limit: int = Query(default=50, ge=1, le=50)) -> MessageListResponse:
    _get_conversation(db, conversation_id, user.id)
    if before_id is not None and after_id is not None:
        raise HTTPException(status_code=422, detail="不能同时指定前后消息游标。")
    statement = select(Message).where(Message.conversation_id == conversation_id)
    if before_id is not None:
        statement = statement.where(Message.id < before_id)
    if after_id is not None:
        statement = statement.where(Message.id > after_id).order_by(Message.id.asc())
    else:
        statement = statement.order_by(Message.id.desc())
    rows = list(db.scalars(statement.limit(limit + 1)).all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    if after_id is None:
        rows.reverse()
    return MessageListResponse(messages=[MessageResponse.model_validate(row) for row in rows], has_more=has_more)


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=201, dependencies=trusted_origin)
def send_message(conversation_id: int, payload: MessageCreate, user: AuthenticatedUser, db: DbSession) -> MessageResponse:
    begin_item_write(db)
    conversation = _get_conversation(db, conversation_id, user.id)
    now = datetime.now(UTC)
    message = Message(conversation_id=conversation.id, sender_id=user.id, content=payload.content, created_at=now)
    db.add(message)
    conversation.updated_at = now
    db.commit()
    return MessageResponse.model_validate(message)

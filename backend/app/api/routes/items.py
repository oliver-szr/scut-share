import io
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.dependencies import AuthenticatedUser, DbSession, require_trusted_origin
from app.core.constants import Campus, InterestTag, ItemCategory, ItemMode, ItemStatus
from app.models.item import Item, ItemImage
from app.models.trade_intent import TradeIntent
from app.models.borrow_request import BorrowRequest
from app.models.gift_request import GiftRequest
from app.db.session import begin_item_write
from app.schemas.item import ItemCreate, ItemFields, ItemImageResponse, ItemListResponse, ItemResponse, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])
trusted_origin = [Depends(require_trusted_origin)]
MAX_PAGE_SIZE = 50
ALLOWED_IMAGE_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def _query_options():
    return (selectinload(Item.owner), selectinload(Item.images))


def _image_url(image: ItemImage) -> str:
    return f"/api/items/images/{image.file_name}"


def _serialize(item: Item) -> ItemResponse:
    return ItemResponse(
        id=item.id,
        owner_id=item.owner_id,
        title=item.title,
        description=item.description,
        category=item.category,
        mode=item.mode,
        campus=item.campus,
        price_cents=item.price_cents,
        borrow_note=item.borrow_note,
        status=item.status,
        availability=item.availability,
        interest_tags=item.interest_tags,
        images=[ItemImageResponse(id=image.id, url=_image_url(image), content_type=image.content_type) for image in item.images],
        owner={"id": item.owner.id, "nickname": item.owner.nickname},
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _get_item(db, item_id: int, *, owner_id: int | None = None, public: bool = False) -> Item:
    statement = select(Item).options(*_query_options()).where(Item.id == item_id)
    if public:
        statement = statement.where(Item.status == ItemStatus.PUBLISHED)
    if owner_id is not None:
        statement = statement.where(Item.owner_id == owner_id)
    item = db.scalar(statement)
    if item is None:
        raise HTTPException(status_code=404, detail="物品不存在或无权访问。")
    return item


@router.get("/images/{file_name}", include_in_schema=False)
def get_image(file_name: str, request: Request) -> FileResponse:
    if Path(file_name).name != file_name or Path(file_name).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=404, detail="图片不存在。")
    path = request.app.state.settings.resolved_upload_dir / file_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="图片不存在。")
    return FileResponse(path)


@router.get("", response_model=ItemListResponse)
def list_items(
    db: DbSession,
    q: str | None = Query(default=None, max_length=100),
    mode: ItemMode | None = None,
    category: ItemCategory | None = None,
    campus: Campus | None = None,
    min_price_cents: int | None = Query(default=None, ge=1, le=100_000_000),
    max_price_cents: int | None = Query(default=None, ge=1, le=100_000_000),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE),
) -> ItemListResponse:
    if min_price_cents is not None and max_price_cents is not None and min_price_cents > max_price_cents:
        raise HTTPException(status_code=422, detail="最低价格不能高于最高价格。")
    filters = [Item.status == ItemStatus.PUBLISHED]
    if q and q.strip():
        keyword = q.strip()
        filters.append(or_(Item.title.ilike(f"%{keyword}%"), Item.description.ilike(f"%{keyword}%")))
    if mode is not None:
        filters.append(Item.mode == mode)
    if category is not None:
        filters.append(Item.category == category)
    if campus is not None:
        filters.append(Item.campus == campus)
    if min_price_cents is not None:
        filters.append(Item.price_cents >= min_price_cents)
    if max_price_cents is not None:
        filters.append(Item.price_cents <= max_price_cents)
    total = db.scalar(select(func.count()).select_from(Item).where(*filters)) or 0
    items = db.scalars(
        select(Item).options(*_query_options()).where(*filters)
        .order_by(Item.created_at.desc(), Item.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return ItemListResponse(items=[_serialize(item) for item in items], total=total, page=page, page_size=page_size)


@router.get("/mine", response_model=ItemListResponse)
def list_my_items(user: AuthenticatedUser, db: DbSession, page: int = Query(default=1, ge=1, le=10_000), page_size: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE)) -> ItemListResponse:
    filters = [Item.owner_id == user.id]
    total = db.scalar(select(func.count()).select_from(Item).where(*filters)) or 0
    items = db.scalars(
        select(Item).options(*_query_options()).where(*filters)
        .order_by(Item.created_at.desc(), Item.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return ItemListResponse(items=[_serialize(item) for item in items], total=total, page=page, page_size=page_size)


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: DbSession) -> ItemResponse:
    return _serialize(_get_item(db, item_id, public=True))


@router.post("", response_model=ItemResponse, status_code=201, dependencies=trusted_origin)
def create_item(payload: ItemCreate, user: AuthenticatedUser, db: DbSession) -> ItemResponse:
    item = Item(
        owner_id=user.id, title=payload.title.strip(), description=payload.description.strip(),
        category=payload.category, mode=payload.mode, campus=payload.campus,
        price_cents=payload.price_cents, borrow_note=payload.borrow_note.strip() if payload.borrow_note else None,
    )
    item.set_interest_tags([tag.value for tag in payload.interest_tags])
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize(_get_item(db, item.id, owner_id=user.id))


@router.patch("/{item_id}", response_model=ItemResponse, dependencies=trusted_origin)
def update_item(item_id: int, payload: ItemUpdate, user: AuthenticatedUser, db: DbSession) -> ItemResponse:
    begin_item_write(db)
    item = _get_item(db, item_id, owner_id=user.id)
    values = {
        "title": item.title, "description": item.description, "category": item.category,
        "mode": item.mode, "campus": item.campus, "price_cents": item.price_cents,
        "borrow_note": item.borrow_note, "interest_tags": [InterestTag(value) for value in item.interest_tags if value in {tag.value for tag in InterestTag}],
    }
    values.update(payload.model_dump(exclude_unset=True))
    if values.get("mode") in (ItemMode.BORROW, ItemMode.GIFT) and "price_cents" not in payload.model_fields_set:
        values["price_cents"] = None
    if values.get("mode") in (ItemMode.SALE, ItemMode.GIFT) and "borrow_note" not in payload.model_fields_set:
        values["borrow_note"] = None
    if "title" in values and isinstance(values["title"], str): values["title"] = values["title"].strip()
    if "description" in values and isinstance(values["description"], str): values["description"] = values["description"].strip()
    if "borrow_note" in values and isinstance(values["borrow_note"], str): values["borrow_note"] = values["borrow_note"].strip()
    try:
        validated = ItemFields.model_validate(values)
    except ValidationError:
        raise HTTPException(status_code=422, detail="物品信息不符合要求。") from None
    if validated.mode != item.mode or validated.price_cents != item.price_cents:
        _ensure_no_trade(db, item_id)
        _ensure_no_borrow(db, item_id)
        _ensure_no_gift(db, item_id)
    item.title, item.description, item.category, item.mode, item.campus = validated.title, validated.description, validated.category, validated.mode, validated.campus
    item.price_cents, item.borrow_note = validated.price_cents, validated.borrow_note
    item.set_interest_tags([tag.value for tag in validated.interest_tags])
    db.commit()
    return _serialize(_get_item(db, item.id, owner_id=user.id))


@router.delete("/{item_id}", response_model=ItemResponse, dependencies=trusted_origin)
def withdraw_item(item_id: int, user: AuthenticatedUser, db: DbSession) -> ItemResponse:
    begin_item_write(db)
    item = _get_item(db, item_id, owner_id=user.id)
    _ensure_no_trade(db, item_id)
    _ensure_no_borrow(db, item_id)
    _ensure_no_gift(db, item_id)
    item.status = ItemStatus.WITHDRAWN
    db.commit()
    return _serialize(_get_item(db, item.id, owner_id=user.id))


def _ensure_no_trade(db, item_id: int) -> None:
    if db.scalar(select(TradeIntent.id).where(
        TradeIntent.item_id == item_id, TradeIntent.status.in_(["pending", "reserved", "completed"]),
    ).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="物品有待处理、已预留或已完成交易，不能改价、切换方式或下架；请先处理有效交易。")


def _ensure_no_borrow(db, item_id: int) -> None:
    if db.scalar(select(BorrowRequest.id).where(
        BorrowRequest.item_id == item_id, BorrowRequest.status.in_(["pending", "approved", "borrowed", "return_pending"]),
    ).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="物品有未结束的借用申请，不能切换方式或下架；请先处理申请或完成归还。")


def _ensure_no_gift(db, item_id: int) -> None:
    if db.scalar(select(GiftRequest.id).where(GiftRequest.item_id == item_id, GiftRequest.status.in_(["pending", "approved", "completed"])).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="物品有有效领取申请或已赠送，不能切换方式或下架。")


@router.post("/{item_id}/images", response_model=ItemResponse, dependencies=trusted_origin)
def upload_image(item_id: int, user: AuthenticatedUser, db: DbSession, request: Request, file: UploadFile = File(...)) -> ItemResponse:
    item = _get_item(db, item_id, owner_id=user.id)
    if len(item.images) >= 3:
        raise HTTPException(status_code=409, detail="每件物品最多上传 3 张图片。")
    max_bytes = request.app.state.settings.max_image_bytes
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="图片大小不能超过 5MB。")
    try:
        image = Image.open(io.BytesIO(data))
        image.verify()
        image_format = image.format
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=415, detail="仅支持 JPEG、PNG 或 WebP 图片。") from None
    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise HTTPException(status_code=415, detail="仅支持 JPEG、PNG 或 WebP 图片。")
    suffix = ".jpg" if image_format == "JPEG" else f".{image_format.lower()}"
    file_name = f"{secrets.token_urlsafe(24)}{suffix}"
    upload_dir = request.app.state.settings.resolved_upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / file_name
    try:
        path.write_bytes(data)
        db.add(ItemImage(item_id=item.id, file_name=file_name, content_type=ALLOWED_IMAGE_FORMATS[image_format]))
        db.commit()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    # The relationship was loaded by the ownership check before the insert.
    # Expire it so the response includes the newly committed image.
    db.expire(item, ["images"])
    return _serialize(_get_item(db, item.id, owner_id=user.id))


@router.delete("/{item_id}/images/{image_id}", response_model=ItemResponse, dependencies=trusted_origin)
def delete_image(item_id: int, image_id: int, user: AuthenticatedUser, db: DbSession, request: Request) -> ItemResponse:
    item = _get_item(db, item_id, owner_id=user.id)
    image = next((candidate for candidate in item.images if candidate.id == image_id), None)
    if image is None:
        raise HTTPException(status_code=404, detail="图片不存在或无权访问。")
    path = request.app.state.settings.resolved_upload_dir / image.file_name
    try:
        original_bytes = path.read_bytes() if path.is_file() else None
        # Remove the file before committing the row deletion. If the commit fails,
        # restore the bytes so the database and controlled directory stay aligned.
        path.unlink(missing_ok=True)
    except OSError:
        raise HTTPException(status_code=503, detail="图片暂时无法删除，请稍后重试。") from None
    db.delete(image)
    try:
        db.commit()
    except Exception:
        db.rollback()
        if original_bytes is not None and not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(original_bytes)
        raise
    db.expire(item, ["images"])
    return _serialize(_get_item(db, item.id, owner_id=user.id))

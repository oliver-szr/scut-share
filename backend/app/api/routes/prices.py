import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.api.dependencies import DbSession
from app.core.constants import ItemMode, ItemStatus, Campus
from app.models.item import Item

router = APIRouter(tags=["prices"])
DISCLAIMER = "仅供参考，展示的是当前挂牌价，不代表实际成交价或公允价格。"


class PriceSample(BaseModel):
    id: int
    title: str
    campus: Campus
    price_cents: int


class PriceReference(BaseModel):
    items: list[PriceSample]
    sample_count: int
    min_price_cents: int | None
    max_price_cents: int | None
    disclaimer: str


@router.get("/items/{item_id}/price-reference", response_model=PriceReference)
def reference(item_id: int, db: DbSession, same_campus: bool = False):
    item = db.scalar(select(Item).where(Item.id == item_id, Item.status == ItemStatus.PUBLISHED))
    if item is None:
        raise HTTPException(status_code=404, detail="物品不存在。")
    if item.mode != ItemMode.SALE:
        raise HTTPException(status_code=409, detail="挂牌价格参考仅支持二手出售商品。")
    # Literal words / adjacent Chinese characters; this is not brand/model or
    # condition matching. A bounded set avoids a large OR expression.
    tokens = []
    for word in re.findall(r"[a-z0-9]{2,}|[\u4e00-\u9fff]{2,}", item.title.lower()):
        tokens.extend([word] if word.isascii() else [word[i:i + 2] for i in range(len(word) - 1)])
    tokens = list(dict.fromkeys(token for token in tokens if token not in {"二手", "出售", "闲置", "转让", "课程", "测试", "共享"}))[:12]
    rows = []
    if tokens:
        filters = [Item.id != item_id, Item.mode == ItemMode.SALE, Item.status == ItemStatus.PUBLISHED,
                   Item.category == item.category, Item.trade_state.is_(None), Item.price_cents > 0,
                   or_(*(func.lower(Item.title).contains(token, autoescape=True) for token in tokens))]
        if same_campus:
            filters.append(Item.campus == item.campus)
        rows = db.scalars(select(Item).where(*filters).order_by(Item.created_at.desc(), Item.id.desc()).limit(8)).all()
    prices = [row.price_cents for row in rows]
    enough = len(prices) >= 3
    return PriceReference(items=[PriceSample(id=row.id, title=row.title, campus=row.campus, price_cents=row.price_cents) for row in rows],
                          sample_count=len(rows), min_price_cents=min(prices) if enough else None,
                          max_price_cents=max(prices) if enough else None, disclaimer=DISCLAIMER)

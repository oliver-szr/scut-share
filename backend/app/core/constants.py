from enum import Enum


class Campus(str, Enum):
    WUSHAN = "五山校区"
    UNIVERSITY_TOWN = "大学城校区"
    INTERNATIONAL = "广州国际校区"


class ItemMode(str, Enum):
    SALE = "sale"
    BORROW = "borrow"
    GIFT = "gift"


class ItemStatus(str, Enum):
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class ItemCategory(str, Enum):
    TEXTBOOK = "教材资料"
    DIGITAL = "数码配件"
    LIVING = "生活用品"
    OUTDOOR = "运动户外"
    HOBBY = "兴趣娱乐"
    OTHER = "其他"


class InterestTag(str, Enum):
    PHOTOGRAPHY = "摄影"
    READING = "阅读"
    DIGITAL = "数码"
    SPORTS = "运动"
    MUSIC = "音乐"
    BOARD_GAME = "桌游"
    STUDY = "学习"
    OTHER = "其他"

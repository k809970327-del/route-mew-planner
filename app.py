from __future__ import annotations

import base64
import json
import math
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from difflib import SequenceMatcher, get_close_matches
from itertools import combinations
from pathlib import Path
from typing import Iterable

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st


ROAD_FACTOR = 1.4
DEFAULT_SPEED_KMH = 35
DEFAULT_STOP_MINUTES = 25
MATCH_THRESHOLD = 0.58
HIGH_SPREAD_REGION_COUNT = 4
PENDING_FILE = Path(__file__).with_name("pending_store_list.json")
HERO_IMAGE = Path(__file__).with_name("assets") / "korean_route_hero.png"
if not HERO_IMAGE.exists():
    HERO_IMAGE = Path(__file__).with_name("korean_route_hero.png")
HOME_NAME = "出發/返回點"
HOME_ADDRESS = "台北市萬華區艋舺大道297號"
HOME_LAT = 25.0322
HOME_LON = 121.4939


STORE_DATA = [
    # 台北市量販
    {"name": "重慶店", "brand": "家樂福量販", "address": "台北市大同區重慶北路二段171號", "lat": 25.0609, "lon": 121.5136, "region": "台北西區"},
    {"name": "桂林店", "brand": "家樂福量販", "address": "台北市萬華區桂林路1號", "lat": 25.0378, "lon": 121.5062, "region": "台北西區"},
    {"name": "內湖店", "brand": "家樂福量販", "address": "台北市內湖區民善街88號", "lat": 25.0606, "lon": 121.5754, "region": "台北東區"},
    {"name": "北投店", "brand": "家樂福量販", "address": "台北市北投區中和街366號", "lat": 25.1411, "lon": 121.5007, "region": "台北北區"},
    {"name": "天母店", "brand": "家樂福量販", "address": "台北市士林區德行西路47號", "lat": 25.1057, "lon": 121.5229, "region": "台北北區"},
    # 台北市超市
    {"name": "大安臨江店", "brand": "家樂福超市", "address": "台北市大安區臨江街87號", "lat": 25.0300, "lon": 121.5545, "region": "台北東區"},
    {"name": "信義莊敬店", "brand": "家樂福超市", "address": "台北市信義區莊敬路325巷", "lat": 25.0284, "lon": 121.5665, "region": "台北東區"},
    {"name": "松山健康店", "brand": "家樂福超市", "address": "台北市松山區健康路156號", "lat": 25.0536, "lon": 121.5581, "region": "台北東區"},
    {"name": "民生社區店", "brand": "家樂福超市", "address": "台北市松山區民生東路五段", "lat": 25.0591, "lon": 121.5624, "region": "台北東區"},
    {"name": "南港中信店", "brand": "家樂福超市", "address": "台北市南港區經貿二路186號", "lat": 25.0584, "lon": 121.6155, "region": "台北東區"},
    {"name": "南港研究院店", "brand": "家樂福超市", "address": "台北市南港區研究院路二段", "lat": 25.0470, "lon": 121.6162, "region": "台北東區"},
    {"name": "文山木柵店", "brand": "家樂福超市", "address": "台北市文山區木柵路三段", "lat": 24.9887, "lon": 121.5665, "region": "台北南區"},
    {"name": "文山興隆店", "brand": "家樂福超市", "address": "台北市文山區興隆路三段", "lat": 24.9990, "lon": 121.5573, "region": "台北南區"},
    {"name": "中山錦州店", "brand": "家樂福超市", "address": "台北市中山區錦州街", "lat": 25.0606, "lon": 121.5311, "region": "台北中區"},
    {"name": "中山農安店", "brand": "家樂福超市", "address": "台北市中山區農安街", "lat": 25.0648, "lon": 121.5269, "region": "台北中區"},
    {"name": "中正濟南店", "brand": "家樂福超市", "address": "台北市中正區濟南路二段", "lat": 25.0406, "lon": 121.5301, "region": "台北中區"},
    {"name": "大同民權店", "brand": "家樂福超市", "address": "台北市大同區民權西路", "lat": 25.0630, "lon": 121.5130, "region": "台北西區"},
    {"name": "士林中正店", "brand": "家樂福超市", "address": "台北市士林區中正路", "lat": 25.0942, "lon": 121.5194, "region": "台北北區"},
    {"name": "北投石牌店", "brand": "家樂福超市", "address": "台北市北投區石牌路二段", "lat": 25.1162, "lon": 121.5172, "region": "台北北區"},
    # 新北量販
    {"name": "淡新店", "brand": "家樂福量販", "address": "新北市淡水區中山北路二段383號", "lat": 25.1855, "lon": 121.4441, "region": "新北北海岸區"},
    {"name": "重新店", "brand": "家樂福量販", "address": "新北市三重區重新路五段654號", "lat": 25.0456, "lon": 121.4681, "region": "新北西區"},
    {"name": "蘆洲店", "brand": "家樂福量販", "address": "新北市三重區五華街282號", "lat": 25.0870, "lon": 121.4890, "region": "新北西區"},
    {"name": "板橋店", "brand": "家樂福量販", "address": "新北市板橋區三民路二段31號", "lat": 25.0170, "lon": 121.4798, "region": "新北西南區"},
    {"name": "中和店", "brand": "家樂福量販", "address": "新北市中和區中山路二段295號", "lat": 25.0028, "lon": 121.4973, "region": "新北西南區"},
    {"name": "新店店", "brand": "家樂福量販", "address": "新北市新店區中興路三段1號", "lat": 24.9769, "lon": 121.5461, "region": "新北南區"},
    {"name": "土城店", "brand": "家樂福量販", "address": "新北市土城區青雲路152號", "lat": 24.9827, "lon": 121.4596, "region": "新北西南區"},
    {"name": "樹林店", "brand": "家樂福量販", "address": "新北市樹林區大安路118號", "lat": 24.9942, "lon": 121.4217, "region": "新北西南區"},
    {"name": "林口店", "brand": "家樂福量販", "address": "新北市林口區文化二路一段559號B1", "lat": 25.0790, "lon": 121.3730, "region": "新北西區"},
    {"name": "汐科店", "brand": "家樂福量販", "address": "新北市汐止區新台五路一段99號B1", "lat": 25.0618, "lon": 121.6475, "region": "新北東北區"},
    # 新北超市
    {"name": "三重集美店", "brand": "家樂福超市", "address": "新北市三重區集美街", "lat": 25.0535, "lon": 121.4882, "region": "新北西區"},
    {"name": "三重自強店", "brand": "家樂福超市", "address": "新北市三重區自強路", "lat": 25.0692, "lon": 121.4897, "region": "新北西區"},
    {"name": "蘆洲長榮店", "brand": "家樂福超市", "address": "新北市蘆洲區長榮路", "lat": 25.0835, "lon": 121.4611, "region": "新北西區"},
    {"name": "新莊中平店", "brand": "家樂福超市", "address": "新北市新莊區中平路", "lat": 25.0495, "lon": 121.4448, "region": "新北西區"},
    {"name": "新莊民安店", "brand": "家樂福超市", "address": "新北市新莊區民安路", "lat": 25.0211, "lon": 121.4260, "region": "新北西區"},
    {"name": "泰山明志店", "brand": "家樂福超市", "address": "新北市泰山區明志路", "lat": 25.0551, "lon": 121.4313, "region": "新北西區"},
    {"name": "五股成泰店", "brand": "家樂福超市", "address": "新北市五股區成泰路", "lat": 25.0845, "lon": 121.4382, "region": "新北西區"},
    {"name": "板橋文化店", "brand": "家樂福超市", "address": "新北市板橋區文化路一段", "lat": 25.0236, "lon": 121.4669, "region": "新北西南區"},
    {"name": "板橋國光店", "brand": "家樂福超市", "address": "新北市板橋區國光路", "lat": 25.0178, "lon": 121.4563, "region": "新北西南區"},
    {"name": "板橋溪崑店", "brand": "家樂福超市", "address": "新北市板橋區溪崑二街", "lat": 24.9894, "lon": 121.4310, "region": "新北西南區"},
    {"name": "中和莒光店", "brand": "家樂福超市", "address": "新北市中和區莒光路", "lat": 25.0005, "lon": 121.4722, "region": "新北西南區"},
    {"name": "中和景平店", "brand": "家樂福超市", "address": "新北市中和區景平路", "lat": 24.9938, "lon": 121.5098, "region": "新北西南區"},
    {"name": "永和中正店", "brand": "家樂福超市", "address": "新北市永和區中正路", "lat": 25.0138, "lon": 121.5150, "region": "新北西南區"},
    {"name": "土城學府店", "brand": "家樂福超市", "address": "新北市土城區學府路一段", "lat": 24.9886, "lon": 121.4532, "region": "新北西南區"},
    {"name": "樹林中山店", "brand": "家樂福超市", "address": "新北市樹林區中山路一段", "lat": 24.9913, "lon": 121.4259, "region": "新北西南區"},
    {"name": "鶯歌建國店", "brand": "家樂福超市", "address": "新北市鶯歌區建國路", "lat": 24.9532, "lon": 121.3506, "region": "新北西南區"},
    {"name": "三峽北大店", "brand": "家樂福超市", "address": "新北市三峽區大學路", "lat": 24.9439, "lon": 121.3736, "region": "新北西南區"},
    {"name": "新店安康店", "brand": "家樂福超市", "address": "新北市新店區安康路二段", "lat": 24.9580, "lon": 121.5118, "region": "新北南區"},
    {"name": "新店安康二店", "brand": "家樂福超市", "address": "新北市新店區安德街45號", "lat": 24.9610, "lon": 121.5092, "region": "新北南區"},
    {"name": "新店北新店", "brand": "家樂福超市", "address": "新北市新店區北新路", "lat": 24.9745, "lon": 121.5431, "region": "新北南區"},
    {"name": "汐止明峰店", "brand": "家樂福超市", "address": "新北市汐止區明峰街117號B1", "lat": 25.0692, "lon": 121.6300, "region": "新北東北區"},
    {"name": "汐止樟樹店", "brand": "家樂福超市", "address": "新北市汐止區樟樹一路", "lat": 25.0640, "lon": 121.6401, "region": "新北東北區"},
    {"name": "瑞芳明燈店", "brand": "家樂福超市", "address": "新北市瑞芳區明燈路三段", "lat": 25.1086, "lon": 121.8055, "region": "新北東北區"},
    {"name": "淡水中山北店", "brand": "家樂福超市", "address": "新北市淡水區中山北路", "lat": 25.1781, "lon": 121.4434, "region": "新北北海岸區"},
    {"name": "淡水新市店", "brand": "家樂福超市", "address": "新北市淡水區新市一路", "lat": 25.1869, "lon": 121.4386, "region": "新北北海岸區"},
    # 基隆
    {"name": "基隆七堵店", "brand": "家樂福量販", "address": "基隆市七堵區明德一路", "lat": 25.0984, "lon": 121.7140, "region": "基隆區"},
    {"name": "基隆安樂店", "brand": "家樂福超市", "address": "基隆市安樂區安樂路二段", "lat": 25.1216, "lon": 121.7240, "region": "基隆區"},
    {"name": "基隆信義店", "brand": "家樂福超市", "address": "基隆市信義區深溪路", "lat": 25.1324, "lon": 121.7823, "region": "基隆區"},
    {"name": "基隆仁愛店", "brand": "家樂福超市", "address": "基隆市仁愛區愛三路", "lat": 25.1286, "lon": 121.7420, "region": "基隆區"},
]


EXCLUDED_DISTRICTS = {"基隆市", "汐止區", "淡水區", "林口區", "深坑區"}

DISTRICT_CENTERS = {
    "北投區": (25.1324, 121.5025),
    "士林區": (25.0950, 121.5246),
    "大同區": (25.0634, 121.5130),
    "中正區": (25.0324, 121.5196),
    "萬華區": (25.0337, 121.4977),
    "大安區": (25.0268, 121.5430),
    "中山區": (25.0643, 121.5335),
    "松山區": (25.0497, 121.5770),
    "信義區": (25.0330, 121.5666),
    "內湖區": (25.0695, 121.5898),
    "南港區": (25.0554, 121.6070),
    "文山區": (24.9898, 121.5705),
    "深坑區": (25.0024, 121.6157),
    "新店區": (24.9676, 121.5415),
    "土城區": (24.9722, 121.4437),
    "永和區": (25.0098, 121.5137),
    "中和區": (24.9993, 121.4980),
    "板橋區": (25.0114, 121.4638),
    "樹林區": (24.9907, 121.4206),
    "三峽區": (24.9343, 121.3693),
    "蘆洲區": (25.0849, 121.4706),
    "三重區": (25.0628, 121.4885),
    "新莊區": (25.0360, 121.4500),
    "林口區": (25.0775, 121.3917),
    "五股區": (25.0840, 121.4380),
    "泰山區": (25.0587, 121.4329),
}

REGION_BY_DISTRICT = {
    "北投區": "台北北區",
    "士林區": "台北北區",
    "大同區": "台北西區",
    "中正區": "台北中區",
    "萬華區": "台北西區",
    "大安區": "台北東區",
    "中山區": "台北中區",
    "松山區": "台北東區",
    "信義區": "台北東區",
    "內湖區": "台北東區",
    "南港區": "台北東區",
    "文山區": "台北南區",
    "深坑區": "新北東南區",
    "新店區": "新北南區",
    "土城區": "新北西南區",
    "永和區": "新北西南區",
    "中和區": "新北西南區",
    "板橋區": "新北西南區",
    "樹林區": "新北西南區",
    "三峽區": "新北西南區",
    "蘆洲區": "新北西區",
    "三重區": "新北西區",
    "新莊區": "新北西區",
    "林口區": "新北西區",
    "五股區": "新北西區",
    "泰山區": "新北西區",
}

OFFICIAL_MARKET_ROWS = [
    ("北投公館店", "台北市北投區公舘路198號"),
    ("北投致遠一店", "台北市北投區致遠一路二段19、21、23號"),
    ("北投光明店", "台北市北投區光明路220號1F"),
    ("北投明德店", "台北市北投區明德路161號B1樓"),
    ("士林雨聲店", "台北市士林區雨聲街52號、52-1號、52巷1號"),
    ("士林格致店", "台北市士林區格致路7號"),
    ("士林德行東店", "台北市士林區德行東路230號"),
    ("士林社中店", "台北市士林區社中街222號1樓"),
    ("士林華齡店", "台北市士林區華齡街175號"),
    ("台北太原店", "台北市大同區太原路155、157號"),
    ("台北重慶北店", "台北市大同區重慶北路1段73號B1"),
    ("台北酒泉店", "台北市大同區酒泉街105號"),
    ("台北同安店", "台北市中正區同安街71號"),
    ("台北羅斯福店", "台北市中正區羅斯福路3段285號B1"),
    ("台北大理店", "台北市萬華區大理街114號1樓"),
    ("台北長沙店", "台北市萬華區長沙街2段93號B1"),
    ("萬華西藏店", "台北市萬華區西藏路125巷13-15號"),
    ("台北萬大店", "台北市萬華區萬大路486巷48號1樓"),
    ("台北仁愛店", "台北市大安區仁愛路4段50-99, 50-100號B1"),
    ("台北仁愛二店", "台北市大安區仁愛路四段408號B1"),
    ("大安敦化南店", "台北市大安區敦化南路二段48號"),
    ("大安和平東店", "台北市大安區和平東路一段145號"),
    ("台北新生南店", "台北市大安區新生南路3段2號B1"),
    ("台北師大店", "台北市大安區師大路129號1樓"),
    ("台北信義店", "台北市大安區信義路4段296號B1"),
    ("台北四維店", "台北市大安區四維路198巷35號"),
    ("台北延吉店", "台北市大安區延吉街250號B1"),
    ("台北忠孝東店", "台北市大安區忠孝東路4段71號B1"),
    ("台北忠孝東二店", "台北市大安區忠孝東路3段218號B1"),
    ("台北農安店", "台北市中山區農安街257、259號"),
    ("台北農安二店", "台北市中山區農安街26、26-1號"),
    ("台北林森北店", "台北市中山區林森北路413號B1"),
    ("台北長安東店", "台北市中山區長安東路2段63、63-1、63-2號"),
    ("台北北安店", "台北市中山區北安路595巷11號, 13號"),
    ("台北八德店", "台北市松山區八德路4段83號"),
    ("台北光復店", "台北市松山區光復北路198號"),
    ("台北敦化北店", "台北市松山區敦化北路199巷5號"),
    ("台北松德店", "台北市信義區松德路99號B1"),
    ("內湖民權東店", "台北市內湖區民權東路6段296巷42-3號B1"),
    ("內湖成功二店", "台北市內湖區成功路2段320巷19號"),
    ("內湖康樂店", "台北市內湖區康樂街150號"),
    ("台北中坡南店", "台北市南港區中坡南路3號"),
    ("南港成福店", "台北市南港區成福路183號"),
    ("南港東明店", "台北市南港區東明街99號1樓"),
    ("南港舊莊店", "台北市南港區舊莊街一段196號"),
    ("文山木新店", "台北市文山區木新路二段158-1號"),
    ("文山景隆店", "台北市文山區景隆街36巷2號"),
    ("文山萬慶店", "台北市文山區萬慶街27號"),
    ("台北木柵店", "台北市文山區木柵路4段153號"),
    ("深坑北深店", "新北市深坑區北深路三段151號"),
    ("新店民族店", "新北市新店區民族路71號B1"),
    ("新店如意店", "新北市新店區如意街95、97號"),
    ("新店安康二店", "新北市新店區安康路二段136巷59號"),
    ("新店安康店", "新北市新店區安康路2段196號B1"),
    ("新店安祥店", "新北市新店區安祥路85-89號"),
    ("新店新坡一店", "新北市新店區新坡一街75號B1"),
    ("新店溪園店", "新北市新店區溪園路399號"),
    ("土城立德店", "新北市土城區立德路105號"),
    ("土城金城店", "新北市土城區金城路三段202-6號"),
    ("土城學府店", "新北市土城區學府路1段157, 161號"),
    ("永和仁愛店", "新北市永和區仁愛路152號B1"),
    ("永和竹林店", "新北市永和區竹林路60號"),
    ("中和中山店", "新北市中和區員山路489~497號1樓"),
    ("中和復興店", "新北市中和區復興路268號"),
    ("中和圓通店", "新北市中和區圓通路274號"),
    ("中和興南店", "新北市中和區興南路一段20號B1"),
    ("中和民治店", "新北市中和區民治街120號"),
    ("中和壽德店", "新北市中和區壽德街20號1樓"),
    ("板橋忠孝店", "新北市板橋區忠孝路237號"),
    ("板橋四維店", "新北市板橋區四維路247、249、251、253號"),
    ("板橋大觀店", "新北市板橋區大觀路3段236號1樓之14、1樓之15"),
    ("板橋金門二店", "新北市板橋區金門街153、155、159號"),
    ("樹林復興店", "新北市樹林區復興路198號"),
    ("樹林太順店", "新北市樹林區太順街64、66、68號"),
    ("樹林學成店", "新北市樹林區學成路536號"),
    ("三峽中山店", "新北市三峽區中山路171號"),
    ("三峽光明店", "新北市三峽區光明路71號"),
    ("三峽大學店", "新北市三峽區大學路119、121、123號1樓"),
    ("蘆洲三民店", "新北市蘆洲區三民路54號"),
    ("蘆洲中興店", "新北市蘆洲區中興街34、36號"),
    ("蘆洲長安二店", "新北市蘆洲區長安街387號1樓"),
    ("蘆洲長榮店", "新北市蘆洲區長榮路386號"),
    ("三重中正北店", "新北市三重區中正北路67、69號"),
    ("三重五華店", "新北市三重區五華街110巷1-4號"),
    ("三重仁愛二店", "新北市三重區仁愛街81號"),
    ("三重永福店", "新北市三重區永福街245、247、249號"),
    ("三重重陽店", "新北市三重區重陽路1段41號"),
    ("三重溪尾店", "新北市三重區溪尾街125號1樓"),
    ("新莊化成店", "新北市新莊區化成路193號"),
    ("新莊中平店", "新北市新莊區中平路377巷18、20號"),
    ("新莊中信店", "新北市新莊區中信街72號"),
    ("新莊昌隆店", "新北市新莊區昌隆街69、75、83號"),
    ("新莊公園一店", "新北市新莊區公園一路110號"),
    ("新莊後港一店", "新北市新莊區後港一路122-126號"),
    ("新莊富國店", "新北市新莊區富國路2號B1"),
    ("新莊龍安店", "新北市新莊區龍安路75號"),
    ("林口仁愛店", "新北市林口區仁愛路二段89號"),
    ("林口文化一店", "新北市林口區文化三路一段319、321、323、325號1樓"),
    ("林口文化三店", "新北市林口區文化三路一段543號"),
    ("五股成泰店", "新北市五股區成泰路一段235號之4"),
    ("五股西雲店", "新北市五股區西雲路169-1、171、171-1號"),
    ("五股明德店", "新北市五股區明德路12巷5號"),
    ("泰山明志店", "新北市泰山區明志路二段95-97號"),
]

STORE_ALIASES = {
    "台北西藏店": "萬華西藏店",
    "西藏店": "萬華西藏店",
}


def district_from_address(address: str) -> str:
    match = re.search(r"(台北市|新北市)([^市縣]+?區)", address)
    if not match:
        return ""
    return match.group(2)


def pseudo_geocode(address: str, sequence: int) -> tuple[float, float]:
    district = district_from_address(address)
    lat, lon = DISTRICT_CENTERS.get(district, (25.04, 121.52))
    offset_x = ((sequence % 7) - 3) * 0.0022
    offset_y = (((sequence // 7) % 7) - 3) * 0.0022
    return round(lat + offset_y, 6), round(lon + offset_x, 6)


def should_include_market(address: str) -> bool:
    return not any(excluded in address for excluded in EXCLUDED_DISTRICTS)


def build_market_store_data() -> list[dict]:
    stores = []
    for sequence, (name, address) in enumerate(OFFICIAL_MARKET_ROWS):
        if not should_include_market(address):
            continue
        district = district_from_address(address)
        lat, lon = pseudo_geocode(address, sequence)
        stores.append(
            {
                "name": name,
                "brand": "家樂福超市",
                "address": address,
                "lat": lat,
                "lon": lon,
                "region": REGION_BY_DISTRICT.get(district, "未分區"),
            }
        )
    return stores


STORE_DATA = build_market_store_data()


@dataclass(frozen=True)
class Leg:
    origin: str
    destination: str
    km: float
    minutes: int
    source: str


def normalize_name(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"家樂福|carrefour|market|超市|量販|店|門市|\s+", "", text, flags=re.I)
    text = text.replace("臺", "台")
    return text


def clean_input_line(value: str) -> str:
    text = value.strip()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^\s*\d+\s*[\.\)、:：-]\s*", "", text)
    text = re.sub(r"\d{1,2}:\d{2}\s*[-~－到至]\s*\d{1,2}:\d{2}", "", text)
    text = re.sub(r"[\|｜].*$", "", text)
    text = re.sub(r"^(門市|騎乘|導航|地址|備註)\s*[:：].*$", "", text)
    return text.strip(" -　,，、。")


def extract_task_tags(value: str) -> tuple[bool, bool, bool]:
    text = value.strip()
    is_urgent = "急件" in text or "緊急" in text or "優先" in text
    has_return_pickup = "收退貨" in text
    has_temp_photo = "臨時交辦" in text or "拍照" in text
    return is_urgent, has_return_pickup, has_temp_photo


def clean_return_item(value: str) -> str:
    text = value.strip()
    text = re.sub(r"^\s*\d+\s*[\.\)、:：-]\s*", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^[\|｜,，、。:：\s]+", "", text)
    text = re.sub(r"^(收退貨|退貨|收貨|品項|退貨品項)\s*[:：]?\s*", "", text)
    text = re.sub(r"(、|,|，)?\s*(急件|臨時交辦.*|拍照).*$", "", text)
    text = re.sub(r"^(門市|騎乘|導航|地址|備註)\s*[:：].*$", "", text)
    return text.strip(" -　,，、。")


def extract_return_item(value: str) -> str:
    text = value.strip()
    patterns = [
        r"(?:收退貨|退貨品項|退貨|收貨|品項)\s*[:：]\s*(.+)$",
        r"[|｜]\s*(?:收退貨|退貨品項|退貨|收貨|品項)\s*[:：]?\s*(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return clean_return_item(match.group(1))
    return ""


def append_return_item(row: pd.Series, item_text: str) -> None:
    clean_item = clean_return_item(item_text)
    if not clean_item:
        return
    existing_items = [
        item.strip()
        for item in str(row.get("退貨品項", "")).split("、")
        if item.strip()
    ]
    if clean_item not in existing_items:
        existing_items.append(clean_item)
    row["退貨品項"] = "、".join(existing_items)
    row["收退貨"] = True
    row["任務"] = task_note(
        bool(row.get("急件", False)),
        True,
        bool(row.get("臨時交辦(拍照)", False)),
        row["退貨品項"],
    )


def task_note(is_urgent: bool, has_return_pickup: bool, has_temp_photo: bool, return_item: str = "") -> str:
    tasks = []
    if is_urgent:
        tasks.append("急件")
    if has_return_pickup:
        item_text = clean_return_item(return_item)
        tasks.append(f"收退貨：{item_text}" if item_text else "收退貨")
    if has_temp_photo:
        tasks.append("臨時交辦(拍照)")
    return "、".join(tasks)


def format_store_entry(
    name: str,
    is_urgent: bool,
    has_return_pickup: bool,
    has_temp_photo: bool,
    return_item: str = "",
) -> str:
    note = task_note(is_urgent, has_return_pickup, has_temp_photo, return_item)
    return f"{name}｜{note}" if note else name


def row_to_store_entry(row: pd.Series) -> str:
    return format_store_entry(
        str(row["name"]),
        bool(row.get("急件", False)),
        bool(row.get("收退貨", False)),
        bool(row.get("臨時交辦(拍照)", False)),
        str(row.get("退貨品項", "")),
    )


def load_pending_entries() -> list[str]:
    session_entries = st.session_state.get("pending_entries_cache")
    if isinstance(session_entries, list):
        return [str(entry).strip() for entry in session_entries if str(entry).strip()]
    if not PENDING_FILE.exists():
        return []
    try:
        payload = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        return []
    clean_entries = [str(entry).strip() for entry in entries if str(entry).strip()]
    st.session_state["pending_entries_cache"] = clean_entries
    return clean_entries


def save_pending_entries(entries: list[str]) -> None:
    clean_entries = []
    seen = set()
    for entry in entries:
        clean = str(entry).strip()
        if clean and clean not in seen:
            clean_entries.append(clean)
            seen.add(clean)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "entries": clean_entries,
    }
    st.session_state["pending_entries_cache"] = clean_entries
    try:
        PENDING_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def clear_pending_entries() -> None:
    save_pending_entries([])


def names_with_tasks(stores: pd.DataFrame) -> str:
    values = []
    for _, row in stores.iterrows():
        note = row.get("任務", "")
        values.append(f'{row["name"]}（{note}）' if note else row["name"])
    return "、".join(values)


def display_store_plan(stores: pd.DataFrame) -> pd.DataFrame:
    return stores[["name", "任務", "region", "address"]].rename(
        columns={
            "name": "門市",
            "region": "分區",
            "address": "地址",
        }
    )


def is_noise_line(value: str) -> bool:
    text = value.strip()
    if not text:
        return True
    return bool(
        re.search(r"https?://", text)
        or re.match(r"^(門市|騎乘|導航)\s*[:：]", text)
        or re.match(r"^今日.*路線$", text)
        or re.match(r"^路線\s*[A-ZＡ-Ｚ]", text, flags=re.I)
        or re.match(r"^[\d.,\s/kmKM分鐘約：:]+$", text)
    )


def best_store_match(raw_line: str, stores: pd.DataFrame) -> tuple[int | None, float, str]:
    cleaned = clean_input_line(raw_line)
    if is_noise_line(raw_line) or not cleaned:
        return None, 0.0, cleaned

    normalized_line = normalize_name(cleaned)
    if not normalized_line:
        return None, 0.0, cleaned

    alias_map = {normalize_name(alias): normalize_name(target) for alias, target in STORE_ALIASES.items()}
    normalized_target = alias_map.get(normalized_line)
    if normalized_target:
        alias_hit = stores[stores["normalized_name"] == normalized_target]
        if not alias_hit.empty:
            return int(alias_hit.index[0]), 0.99, cleaned

    substring_matches = []
    for idx, row in stores.iterrows():
        store_key = row.normalized_name
        if store_key and (store_key in normalized_line or normalized_line in store_key):
            score = 0.98 if store_key in normalized_line else 0.88
            substring_matches.append((idx, score, len(store_key)))
    if substring_matches:
        idx, score, _ = max(substring_matches, key=lambda item: (item[1], item[2]))
        return idx, score, cleaned

    normalized_map = {row.normalized_name: idx for idx, row in stores.iterrows()}
    candidates = get_close_matches(normalized_line, list(normalized_map), n=1, cutoff=MATCH_THRESHOLD)
    if not candidates:
        return None, 0.0, cleaned

    best_key = candidates[0]
    return normalized_map[best_key], SequenceMatcher(None, normalized_line, best_key).ratio(), cleaned


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimate_leg(origin: pd.Series, dest: pd.Series, speed_kmh: float) -> Leg:
    straight_km = haversine_km(origin.lat, origin.lon, dest.lat, dest.lon)
    road_km = straight_km * ROAD_FACTOR
    minutes = max(3, math.ceil(road_km / speed_kmh * 60))
    return Leg(origin["name"], dest["name"], road_km, minutes, "離線估算")


def home_row() -> pd.Series:
    return pd.Series(
        {
            "name": HOME_NAME,
            "brand": "起訖點",
            "address": HOME_ADDRESS,
            "lat": HOME_LAT,
            "lon": HOME_LON,
            "region": "萬華出發",
            "任務": "",
        }
    )


def google_leg(origin: pd.Series, dest: pd.Series, api_key: str, fallback_speed_kmh: float) -> Leg:
    if not api_key:
        return estimate_leg(origin, dest, fallback_speed_kmh)

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": f"{origin.lat},{origin.lon}",
        "destinations": f"{dest.lat},{dest.lon}",
        "mode": "driving",
        "language": "zh-TW",
        "key": api_key,
    }
    try:
        response = requests.get(url, params=params, timeout=8)
        response.raise_for_status()
        payload = response.json()
        element = payload["rows"][0]["elements"][0]
        if element.get("status") == "OK":
            return Leg(
                origin["name"],
                dest["name"],
                element["distance"]["value"] / 1000,
                math.ceil(element["duration"]["value"] / 60),
                "Google API",
            )
    except Exception:
        pass
    return estimate_leg(origin, dest, fallback_speed_kmh)


def round_trip_legs(route: pd.DataFrame, api_key: str, speed_kmh: float) -> list[Leg]:
    if route.empty:
        return []
    origin = home_row()
    legs = [google_leg(origin, route.iloc[0], api_key, speed_kmh)]
    for idx in range(1, len(route)):
        legs.append(google_leg(route.iloc[idx - 1], route.iloc[idx], api_key, speed_kmh))
    legs.append(google_leg(route.iloc[-1], origin, api_key, speed_kmh))
    return legs


def visit_only_legs(round_trip: list[Leg]) -> list[Leg]:
    if len(round_trip) <= 2:
        return []
    return round_trip[1:-1]


def match_input_lines(lines: Iterable[str], stores: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    matched_rows = []
    misses = []
    seen_idx = set()
    last_matched_row: pd.Series | None = None

    for raw in lines:
        original = raw.strip()
        if not original or is_noise_line(original):
            continue

        idx, score, cleaned = best_store_match(original, stores)
        if idx is None:
            if last_matched_row is not None:
                return_item = clean_return_item(original)
                if return_item:
                    append_return_item(last_matched_row, return_item)
                    continue
            misses.append({"輸入": original, "原因": "找不到相近門市"})
            continue

        if idx in seen_idx:
            last_matched_row = None
            continue
        seen_idx.add(idx)
        is_urgent, has_return_pickup, has_temp_photo = extract_task_tags(original)
        return_item = extract_return_item(original)
        item = stores.loc[idx].copy()
        item["input_name"] = cleaned or original
        item["match_score"] = score
        item["急件"] = is_urgent
        item["收退貨"] = has_return_pickup or bool(return_item)
        item["臨時交辦(拍照)"] = has_temp_photo
        item["退貨品項"] = return_item
        item["任務"] = task_note(is_urgent, item["收退貨"], has_temp_photo, return_item)
        matched_rows.append(item)
        last_matched_row = item

    if not matched_rows:
        return pd.DataFrame(), misses
    return pd.DataFrame(matched_rows).reset_index(drop=True), misses


def nearest_neighbor_route(stores: pd.DataFrame, api_key: str, speed_kmh: float) -> tuple[pd.DataFrame, list[Leg]]:
    if len(stores) <= 1:
        return stores.copy().reset_index(drop=True), []

    remaining = stores.copy().reset_index(drop=True)
    origin = home_row()
    start_idx = min(
        remaining.index,
        key=lambda idx: haversine_km(origin.lat, origin.lon, remaining.loc[idx].lat, remaining.loc[idx].lon),
    )
    route_rows = [remaining.loc[start_idx]]
    remaining = remaining.drop(index=start_idx).reset_index(drop=True)
    legs: list[Leg] = []

    while not remaining.empty:
        current = route_rows[-1]
        candidates = [
            (idx, haversine_km(current.lat, current.lon, row.lat, row.lon))
            for idx, row in remaining.iterrows()
        ]
        next_idx = min(candidates, key=lambda item: item[1])[0]
        nxt = remaining.loc[next_idx]
        legs.append(google_leg(current, nxt, api_key, speed_kmh))
        route_rows.append(nxt)
        remaining = remaining.drop(index=next_idx).reset_index(drop=True)

    return pd.DataFrame(route_rows).reset_index(drop=True), legs


def compact_route_score(stores: pd.DataFrame, speed_kmh: float) -> tuple[float, pd.DataFrame, list[Leg]]:
    route, legs = nearest_neighbor_route(stores, "", speed_kmh)
    total_km = sum(leg.km for leg in legs)
    region_penalty = max(0, route["region"].nunique() - 1) * 8
    priority_bonus = sum(task_priority_score(row) for _, row in route.iterrows()) * 12
    return total_km + region_penalty - priority_bonus, route, legs


def task_priority_score(row: pd.Series) -> int:
    score = 0
    if bool(row.get("急件", False)):
        score += 3
    if bool(row.get("收退貨", False)):
        score += 2
    if bool(row.get("臨時交辦(拍照)", False)):
        score += 1
    return score


def average_distance_to_group(row: pd.Series, group: pd.DataFrame) -> float:
    others = group[group["name"] != row["name"]]
    if others.empty:
        return 0
    return sum(haversine_km(row.lat, row.lon, other.lat, other.lon) for _, other in others.iterrows()) / len(others)


def recommend_stores_by_count(matched: pd.DataFrame, count: int, speed_kmh: float) -> tuple[pd.DataFrame, list[Leg], str]:
    count = max(1, min(count, len(matched)))
    indexed = matched.reset_index(drop=True)

    if count == len(indexed):
        route, legs = nearest_neighbor_route(indexed, "", speed_kmh)
        return route, legs, "全部都跑"

    if count == 1:
        chosen_idx = max(
            indexed.index,
            key=lambda idx: (
                task_priority_score(indexed.loc[idx]),
                -average_distance_to_group(indexed.loc[idx], indexed),
            ),
        )
        chosen = indexed.loc[[chosen_idx]]
        reason = "跑 1 家，優先選急件/任務權重最高且較順路的店"
        return chosen.reset_index(drop=True), [], reason

    best_score = float("inf")
    best_route = pd.DataFrame()
    best_legs: list[Leg] = []
    best_reason = ""

    candidate_indexes = indexed.index.tolist()
    if math.comb(len(candidate_indexes), count) > 20000:
        candidate_indexes = []
        for _, group in indexed.groupby("region"):
            if len(group) >= count:
                candidate_indexes.extend(group.index.tolist())
        if len(candidate_indexes) < count:
            candidate_indexes = indexed.index.tolist()

    all_combos = combinations(candidate_indexes, count)
    for combo in all_combos:
        subset = indexed.loc[list(combo)].reset_index(drop=True)
        score, route, legs = compact_route_score(subset, speed_kmh)
        if score < best_score:
            best_score = score
            best_route = route
            best_legs = legs
            regions = "、".join(route["region"].drop_duplicates().tolist())
            best_reason = f"跑 {count} 家，挑距離最集中組合（{regions}）"

    return best_route, best_legs, best_reason


def build_timeline(route: pd.DataFrame, legs: list[Leg], start_at: time, stop_minutes: int) -> pd.DataFrame:
    cursor = datetime.combine(datetime.today(), start_at)
    rows = []
    for order, (_, row) in enumerate(route.reset_index(drop=True).iterrows()):
        if order < len(legs):
            cursor += timedelta(minutes=legs[order].minutes)
        arrive = cursor
        leave = arrive + timedelta(minutes=stop_minutes)
        rows.append(
            {
                "順序": order + 1,
                "門市": row["name"],
                "型態": row["brand"],
                "分區": row["region"],
                "地址": row["address"],
                "任務": row.get("任務", ""),
                "抵達": arrive.strftime("%H:%M"),
                "離開": leave.strftime("%H:%M"),
                "座標": f'{row["lat"]:.5f}, {row["lon"]:.5f}',
            }
        )
        cursor = leave
    return pd.DataFrame(rows)


def route_distance_summary(legs: list[Leg]) -> tuple[float, int]:
    return round(sum(leg.km for leg in legs), 1), sum(leg.minutes for leg in legs)


def google_maps_url(route: pd.DataFrame) -> str:
    if route.empty:
        return ""
    base = "https://www.google.com/maps/dir/?api=1&travelmode=driving"
    origin = HOME_ADDRESS
    destination = HOME_ADDRESS
    waypoints = "|".join(row["address"] for _, row in route.iterrows())
    params = {
        "origin": origin,
        "destination": destination,
    }
    if waypoints:
        params["waypoints"] = waypoints
    return base + "&" + urllib.parse.urlencode(params, safe="|,")


def line_text(title: str, timeline: pd.DataFrame, legs: list[Leg], maps_url: str) -> str:
    distance_km, ride_minutes = route_distance_summary(legs)
    lines = [
        f"{title}",
        f"門市：{len(timeline)} 家",
        f"騎乘：約 {distance_km} km / {ride_minutes} 分鐘",
        "",
    ]
    for _, row in timeline.iterrows():
        task_part = f'｜{row["任務"]}' if row.get("任務") else ""
        lines.append(f'{row["順序"]}. {row["門市"]}{task_part}｜{row["抵達"]}-{row["離開"]}')
        lines.append(f'   {row["地址"]}')
    lines.extend(["", f"導航：{maps_url}"])
    return "\n".join(lines)


def region_summary(matched: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for region, group in matched.groupby("region", sort=False):
        rows.append(
            {
                "分區": region,
                "家數": len(group),
                "門市": names_with_tasks(group),
            }
        )
    return pd.DataFrame(rows).sort_values(["家數", "分區"], ascending=[False, True]).reset_index(drop=True)


def today_memo_text(summary: pd.DataFrame) -> str:
    main_region = summary.iloc[0]["分區"]
    main_stores = summary.iloc[0]["門市"]
    postponed = summary.iloc[1:]
    if postponed.empty:
        return f"今天集中在 {main_region}，可先照這條線跑：{main_stores}。"

    postponed_regions = "、".join(postponed["分區"].tolist())
    return (
        f"今天清單太散，涵蓋了 {len(summary)} 個區域。"
        f"建議先跑家數最多或任務較急的 {main_region}（{main_stores}），"
        f"其餘 {postponed_regions} 可留到下次併線。"
    )


def render_map(route: pd.DataFrame) -> None:
    if route.empty:
        return
    map_data = route.copy()
    map_data["order_label"] = map_data.index + 1
    st.pydeck_chart(
        pdk.Deck(
            map_style=None,
            initial_view_state=pdk.ViewState(
                latitude=float(map_data.lat.mean()),
                longitude=float(map_data.lon.mean()),
                zoom=10.5,
                pitch=0,
            ),
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=map_data,
                    get_position="[lon, lat]",
                    get_radius=120,
                    get_fill_color=[0, 114, 178, 190],
                    pickable=True,
                ),
                pdk.Layer(
                    "PathLayer",
                    data=[{"path": map_data[["lon", "lat"]].values.tolist()}],
                    get_path="path",
                    width_scale=20,
                    width_min_pixels=3,
                    get_color=[213, 94, 0],
                ),
            ],
            tooltip={"text": "{order_label}. {name}\n{address}"},
        )
    )


def top_anchor() -> None:
    st.markdown('<div id="route-input-top"></div>', unsafe_allow_html=True)


def image_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def inject_app_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --planner-bg: #bfe8e5;
            --planner-panel: #ffffff;
            --planner-soft: #fff8dc;
            --planner-ink: #21576a;
            --planner-muted: #6b887c;
            --planner-coral: #f07b9b;
            --planner-coral-dark: #db5f80;
            --planner-blue: #72cbd1;
            --planner-green: #b9d96d;
            --planner-lilac: #a984d6;
            --planner-oat: #ffe6a6;
            --planner-orange: #f59b22;
            --planner-line: #ffffff;
        }

        .stApp {
            background:
                radial-gradient(circle, rgba(216, 239, 188, 0.85) 0 7px, transparent 8px),
                radial-gradient(circle, rgba(142, 216, 214, 0.72) 0 7px, transparent 8px),
                linear-gradient(180deg, #bfe8e5 0%, #bfe8e5 48%, #b9d96d 48%, #b9d96d 100%);
            background-size: 46px 46px, 46px 46px, auto;
            background-position: 0 0, 23px 23px, 0 0;
            color: var(--planner-ink);
        }

        html, body, [class*="css"] {
            font-family: "Inter", "Noto Sans TC", "Microsoft JhengHei", sans-serif;
        }

        section[data-testid="stSidebar"] {
            background: rgba(255, 248, 220, 0.94);
            border-right: 4px solid rgba(245, 155, 34, 0.48);
        }

        section[data-testid="stSidebar"] [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.88);
            border: 2px solid rgba(245, 155, 34, 0.25);
            border-radius: 24px;
            padding: 0.6rem 0.75rem;
        }

        .block-container {
            padding-top: 1.5rem;
            max-width: 1280px;
        }

        .planner-hero {
            position: relative;
            background:
                linear-gradient(180deg, rgba(255, 248, 220, 0.94), rgba(255, 248, 220, 0.86));
            border: 5px solid rgba(255, 255, 255, 0.92);
            border-radius: 42px;
            padding: 1.55rem 1.65rem;
            box-shadow: 0 18px 0 rgba(142, 120, 76, 0.18), 0 26px 52px rgba(58, 96, 91, 0.18);
            margin: 0.4rem 0 1.2rem 0;
            overflow: hidden;
        }

        .planner-hero::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                radial-gradient(circle, rgba(216, 239, 188, 0.38) 0 7px, transparent 8px),
                linear-gradient(120deg, rgba(255,255,255,0.48), transparent 42%);
            background-size: 42px 42px, auto;
            pointer-events: none;
        }

        .planner-hero::after {
            content: "";
            position: absolute;
            right: 1.25rem;
            bottom: 1.1rem;
            width: 220px;
            height: 12px;
            background: linear-gradient(90deg, var(--planner-orange), var(--planner-coral), var(--planner-blue), var(--planner-green));
            border-radius: 999px;
            opacity: 0.78;
        }

        .planner-hero > * {
            position: relative;
            z-index: 1;
        }

        .planner-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .planner-brand {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            font-weight: 900;
            color: var(--planner-ink);
            letter-spacing: 0.01em;
        }

        .planner-logo {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            display: grid;
            place-items: center;
            background: #f59b22;
            color: #fff;
            font-size: 1.2rem;
            box-shadow: 0 6px 0 rgba(178, 108, 28, 0.28);
        }

        .planner-menu {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            justify-content: flex-end;
            background: rgba(255, 255, 255, 0.54);
            border: 3px solid rgba(255,255,255,0.78);
            border-radius: 999px;
            padding: 0.28rem;
        }

        .planner-menu a {
            display: inline-flex;
            align-items: center;
            text-decoration: none;
            color: #21576a;
            background: #fff8dc;
            border: 2px solid rgba(245, 155, 34, 0.22);
            border-radius: 999px;
            padding: 0.5rem 0.82rem;
            font-weight: 800;
            font-size: 0.88rem;
        }

        .planner-menu a:hover {
            color: #ffffff;
            border-color: rgba(255, 255, 255, 0.75);
            background: var(--planner-orange);
        }

        .planner-hero-grid {
            display: grid;
            grid-template-columns: minmax(0, 0.95fr) minmax(330px, 0.72fr);
            gap: 1.2rem;
            align-items: end;
        }

        .planner-visual-stack {
            display: grid;
            gap: 0.82rem;
            position: relative;
        }

        .cat-stage {
            position: absolute;
            display: none;
            top: -28px;
            right: 8px;
            width: 172px;
            height: 162px;
            z-index: 4;
            animation: catFloat 2.8s ease-in-out infinite;
            pointer-events: none;
        }

        .cat-sticker {
            position: absolute;
            left: 21px;
            top: 17px;
            width: 120px;
            height: 118px;
            background: rgba(255, 255, 255, 0.72);
            border: 5px solid #ffffff;
            border-radius: 44% 44% 48% 48%;
            filter: drop-shadow(0 7px 0 rgba(194, 93, 123, 0.18));
            z-index: 1;
        }

        .cat-body {
            position: absolute;
            left: 50px;
            top: 84px;
            width: 70px;
            height: 54px;
            background: #fffdfd;
            border: 4px solid #b84f77;
            border-radius: 42px 42px 32px 32px;
            z-index: 3;
        }

        .cat-head {
            position: absolute;
            left: 32px;
            top: 24px;
            width: 104px;
            height: 86px;
            background: #fffdfd;
            border: 4px solid #b84f77;
            border-radius: 48% 48% 44% 44%;
            z-index: 4;
        }

        .cat-head::before,
        .cat-head::after {
            content: "";
            position: absolute;
            top: -18px;
            width: 34px;
            height: 38px;
            background:
                radial-gradient(circle at 55% 62%, #ffc4d3 0 12px, transparent 13px),
                #fffdfd;
            border-left: 4px solid #b84f77;
            border-top: 4px solid #b84f77;
            transform: rotate(45deg);
            border-radius: 9px 0 0 0;
        }

        .cat-head::before {
            left: 9px;
        }

        .cat-head::after {
            right: 9px;
        }

        .cat-eye {
            position: absolute;
            top: 56px;
            width: 25px;
            height: 31px;
            background:
                radial-gradient(circle at 35% 28%, #ffffff 0 5px, transparent 6px),
                radial-gradient(circle at 63% 62%, rgba(255,255,255,0.72) 0 3px, transparent 4px),
                #bd3f70;
            border-radius: 50%;
            animation: catBlink 4.2s infinite;
            z-index: 5;
        }

        .cat-eye.left {
            left: 54px;
        }

        .cat-eye.right {
            left: 93px;
        }

        .cat-nose {
            position: absolute;
            left: 82px;
            top: 84px;
            width: 8px;
            height: 6px;
            background: #f07b9b;
            border-radius: 50%;
            z-index: 5;
        }

        .cat-mouth {
            position: absolute;
            left: 77px;
            top: 88px;
            width: 19px;
            height: 10px;
            border-bottom: 3px solid #7c3452;
            border-radius: 0 0 18px 18px;
            z-index: 5;
        }

        .cat-blush {
            position: absolute;
            top: 84px;
            width: 18px;
            height: 10px;
            background: rgba(255, 165, 190, 0.72);
            border-radius: 50%;
            z-index: 5;
        }

        .cat-blush.left {
            left: 43px;
        }

        .cat-blush.right {
            left: 111px;
        }

        .cat-whisker {
            position: absolute;
            top: 83px;
            width: 25px;
            height: 2px;
            background: #b84f77;
            z-index: 5;
        }

        .cat-whisker.left.one { left: 25px; transform: rotate(9deg); }
        .cat-whisker.left.two { left: 24px; top: 92px; transform: rotate(-7deg); }
        .cat-whisker.right.one { left: 122px; transform: rotate(-9deg); }
        .cat-whisker.right.two { left: 123px; top: 92px; transform: rotate(7deg); }

        .cat-arm {
            position: absolute;
            top: 111px;
            width: 20px;
            height: 33px;
            background: #fffdfd;
            border: 4px solid #b84f77;
            border-top: 0;
            border-radius: 0 0 18px 18px;
            z-index: 4;
        }

        .cat-arm.left {
            left: 54px;
            transform: rotate(9deg);
        }

        .cat-arm.right {
            left: 96px;
            transform: rotate(-9deg);
        }

        .cat-tail {
            position: absolute;
            right: 8px;
            top: 86px;
            width: 56px;
            height: 44px;
            border: 9px solid #b84f77;
            border-left: 0;
            border-bottom: 0;
            border-radius: 0 38px 0 0;
            transform-origin: 4px 40px;
            animation: tailWag 1.15s ease-in-out infinite alternate;
            z-index: 2;
        }

        .cat-paw {
            position: absolute;
            top: 128px;
            width: 30px;
            height: 22px;
            background:
                radial-gradient(circle at 34% 55%, #ffc4d3 0 4px, transparent 5px),
                radial-gradient(circle at 63% 55%, #ffc4d3 0 4px, transparent 5px),
                #fffdfd;
            border: 4px solid #b84f77;
            border-radius: 999px;
            z-index: 5;
        }

        .cat-paw.one {
            left: 42px;
        }

        .cat-paw.two {
            left: 96px;
        }

        .cat-star {
            position: absolute;
            width: 28px;
            height: 28px;
            background: #fff4a8;
            clip-path: polygon(50% 0%, 62% 34%, 98% 35%, 69% 56%, 79% 91%, 50% 70%, 21% 91%, 31% 56%, 2% 35%, 38% 34%);
            filter: drop-shadow(0 0 0 #b84f77) drop-shadow(0 3px 0 rgba(184,79,119,0.26));
            animation: starTwinkle 1.8s ease-in-out infinite alternate;
            z-index: 0;
        }

        .cat-star.one {
            left: 3px;
            top: 18px;
            transform: rotate(-12deg);
        }

        .cat-star.two {
            right: 0;
            top: 20px;
            width: 22px;
            height: 22px;
            animation-delay: 0.35s;
        }

        .cat-star.three {
            left: 14px;
            bottom: 18px;
            width: 20px;
            height: 20px;
            animation-delay: 0.7s;
        }

        .cat-shadow {
            position: absolute;
            left: 37px;
            bottom: 2px;
            width: 96px;
            height: 17px;
            background: rgba(184, 79, 119, 0.18);
            border-radius: 50%;
            filter: blur(1px);
            animation: shadowPulse 2.8s ease-in-out infinite;
        }

        @keyframes catFloat {
            0%, 100% { transform: translateY(0) rotate(-1deg); }
            50% { transform: translateY(-9px) rotate(1deg); }
        }

        @keyframes tailWag {
            from { transform: rotate(-9deg); }
            to { transform: rotate(13deg); }
        }

        @keyframes catBlink {
            0%, 46%, 54%, 100% { transform: scaleY(1); }
            50% { transform: scaleY(0.16); }
        }

        @keyframes shadowPulse {
            0%, 100% { transform: scaleX(1); opacity: 0.15; }
            50% { transform: scaleX(0.82); opacity: 0.09; }
        }

        @keyframes starTwinkle {
            from { transform: scale(0.92) rotate(-8deg); opacity: 0.78; }
            to { transform: scale(1.08) rotate(9deg); opacity: 1; }
        }

        .planner-hero-image {
            width: 100%;
            aspect-ratio: 1.67;
            object-fit: cover;
            display: block;
            border-radius: 38px;
            border: 5px solid rgba(255, 255, 255, 0.92);
            box-shadow: 0 14px 0 rgba(142, 120, 76, 0.18), 0 24px 46px rgba(58, 96, 91, 0.18);
            background: #fff8dc;
        }

        .planner-hero-panel {
            background: rgba(255, 248, 220, 0.92);
            border: 4px solid rgba(255, 255, 255, 0.86);
            border-radius: 34px;
            padding: 1rem;
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.8),
                0 10px 0 rgba(142, 120, 76, 0.15);
        }

        .planner-panel-number {
            font-size: 2.45rem;
            line-height: 1;
            font-weight: 900;
            color: var(--planner-orange);
            margin-bottom: 0.25rem;
        }

        .planner-panel-copy {
            color: #475569;
            font-weight: 800;
            line-height: 1.45;
        }

        .planner-mini-list {
            margin-top: 0.8rem;
            display: grid;
            gap: 0.42rem;
        }

        .planner-mini-row {
            display: flex;
            justify-content: space-between;
            gap: 0.7rem;
            padding: 0.48rem 0.58rem;
            background: rgba(248, 242, 238, 0.82);
            border: 2px solid rgba(255, 255, 255, 0.92);
            border-radius: 999px;
            color: #21576a;
            font-size: 0.84rem;
            font-weight: 800;
        }

        .planner-mini-row span:last-child {
            color: var(--planner-coral-dark);
            text-align: right;
        }

        .planner-kicker {
            color: var(--planner-orange);
            font-weight: 800;
            font-size: 0.88rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
        }

        .planner-title {
            font-size: clamp(1.75rem, 3vw, 2.75rem);
            line-height: 1.12;
            font-weight: 900;
            letter-spacing: 0;
            color: var(--planner-ink);
            margin: 0 0 0.55rem 0;
        }

        .planner-subtitle {
            color: #4b5563;
            font-size: 1.02rem;
            line-height: 1.65;
            margin-bottom: 0.9rem;
        }

        .planner-pills {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
        }

        .planner-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            background: rgba(255, 255, 255, 0.82);
            border: 2px solid rgba(255, 255, 255, 0.92);
            border-radius: 999px;
            padding: 0.45rem 0.72rem;
            color: #21576a;
            font-size: 0.9rem;
            font-weight: 700;
        }

        .planner-card {
            background: rgba(255, 248, 220, 0.94);
            border: 4px solid rgba(255, 255, 255, 0.88);
            border-radius: 34px;
            padding: 1rem;
            box-shadow: 0 10px 0 rgba(142, 120, 76, 0.13);
            min-height: 104px;
        }

        .planner-card-label {
            color: var(--planner-muted);
            font-size: 0.86rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
            letter-spacing: 0.04em;
        }

        .planner-card-value {
            color: var(--planner-ink);
            font-size: 1.65rem;
            line-height: 1.1;
            font-weight: 900;
            margin-bottom: 0.4rem;
        }

        .planner-card-note {
            color: #64748b;
            font-size: 0.86rem;
            line-height: 1.45;
        }

        .planner-menu-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
            margin: 0.4rem 0 1.1rem 0;
        }

        .planner-action {
            position: relative;
            background:
                linear-gradient(180deg, rgba(255,248,220,0.97), rgba(255,255,255,0.90));
            border: 4px solid rgba(255, 255, 255, 0.86);
            border-radius: 34px;
            padding: 1.08rem;
            box-shadow: 0 10px 0 rgba(142, 120, 76, 0.13);
            min-height: 132px;
            overflow: hidden;
            transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
        }

        .planner-action::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 5px;
            background: linear-gradient(90deg, var(--planner-orange), var(--planner-coral), var(--planner-blue), var(--planner-green));
        }

        .planner-action:hover {
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.98);
            box-shadow: 0 13px 0 rgba(142, 120, 76, 0.15);
        }

        .planner-action-icon {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            display: grid;
            place-items: center;
            color: #fff;
            font-size: 1.05rem;
            font-weight: 900;
            margin-bottom: 0.7rem;
        }

        .planner-action:nth-child(1) .planner-action-icon { background: #f59b22; }
        .planner-action:nth-child(2) .planner-action-icon { background: #72cbd1; }
        .planner-action:nth-child(3) .planner-action-icon { background: #a984d6; }
        .planner-action:nth-child(4) .planner-action-icon { background: #f07b9b; }

        .planner-action-title {
            color: var(--planner-ink);
            font-size: 1rem;
            font-weight: 900;
            margin-bottom: 0.35rem;
        }

        .planner-action-copy {
            color: #64748b;
            font-size: 0.88rem;
            line-height: 1.5;
        }

        .planner-section-title {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            margin: 1.15rem 0 0.55rem 0;
        }

        .planner-section-dot {
            width: 10px;
            height: 28px;
            border-radius: 999px;
            background: linear-gradient(180deg, var(--planner-orange), var(--planner-coral), var(--planner-blue));
        }

        .planner-section-title h3 {
            margin: 0;
            font-size: 1.28rem;
            font-weight: 900;
            color: #303642;
        }

        .planner-section-title span {
            color: var(--planner-muted);
            font-size: 0.92rem;
            font-weight: 700;
        }

        div[data-testid="stExpander"] {
            background: rgba(255, 248, 220, 0.92);
            border: 4px solid rgba(255, 255, 255, 0.86);
            border-radius: 34px;
            box-shadow: 0 10px 0 rgba(142, 120, 76, 0.12);
            overflow: hidden;
        }

        div[data-testid="stAlert"] {
            border-radius: 13px;
            border-width: 1px;
            box-shadow: 0 10px 26px rgba(41, 52, 66, 0.07);
        }

        .stButton > button,
        .stDownloadButton > button,
        .stLinkButton > a {
            border-radius: 999px !important;
            font-weight: 800 !important;
            border: 3px solid rgba(255, 255, 255, 0.84) !important;
            box-shadow: 0 6px 0 rgba(142, 120, 76, 0.14);
        }

        .stButton > button[kind="primary"],
        button[kind="primary"] {
            background: var(--planner-orange) !important;
            border-color: rgba(255, 255, 255, 0.9) !important;
        }

        textarea,
        input,
        div[data-baseweb="select"] > div {
            border-radius: 24px !important;
        }

        textarea {
            background: rgba(255, 255, 255, 0.92) !important;
            border: 4px solid rgba(255, 255, 255, 0.86) !important;
            box-shadow: 0 8px 0 rgba(142, 120, 76, 0.12);
        }

        div[role="radiogroup"] {
            background: rgba(255, 248, 220, 0.88);
            border: 4px solid rgba(255, 255, 255, 0.84);
            border-radius: 28px;
            padding: 0.7rem 0.85rem;
            box-shadow: 0 8px 0 rgba(142, 120, 76, 0.10);
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stDataEditor"] {
            border-radius: 28px;
            overflow: hidden;
            box-shadow: 0 10px 0 rgba(142, 120, 76, 0.10);
        }

        h2, h3 {
            letter-spacing: 0;
        }

        @media (max-width: 900px) {
            .planner-topbar,
            .planner-hero-grid {
                display: block;
            }

            .planner-menu,
            .planner-visual-stack {
                margin-top: 0.9rem;
            }

            .planner-menu-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 768px) {
            .block-container {
                padding: 0.65rem 0.65rem 2rem 0.65rem;
            }

            .planner-hero {
                border-radius: 26px;
                padding: 0.85rem;
                box-shadow: 0 8px 0 rgba(142, 120, 76, 0.12);
            }

            .planner-title {
                font-size: 1.72rem;
                line-height: 1.22;
            }

            .planner-subtitle {
                font-size: 0.92rem;
            }

            .planner-menu {
                border-radius: 22px;
                justify-content: flex-start;
            }

            .planner-menu a {
                flex: 1 1 calc(50% - 0.5rem);
                justify-content: center;
                min-width: 0;
                padding: 0.5rem 0.35rem;
                text-align: center;
            }

            .planner-hero-image {
                border-radius: 24px;
                border-width: 3px;
                box-shadow: 0 7px 0 rgba(142, 120, 76, 0.12);
            }

            .planner-hero-panel,
            .planner-card,
            .planner-action,
            div[data-testid="stExpander"] {
                border-radius: 24px;
            }

            div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap;
                gap: 0.72rem;
            }

            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                flex: 1 1 100% !important;
                width: 100% !important;
                min-width: 100% !important;
            }

            .stButton > button,
            .stDownloadButton > button,
            .stLinkButton > a {
                width: 100% !important;
                min-height: 44px;
            }

            div[data-testid="stDataFrame"],
            div[data-testid="stDataEditor"] {
                max-width: calc(100vw - 1.3rem);
                overflow-x: auto;
            }
        }

        @media (max-width: 560px) {
            .planner-menu-grid {
                grid-template-columns: 1fr;
            }

            .planner-pills {
                display: grid;
                grid-template-columns: 1fr;
            }

            .planner-pill {
                width: 100%;
                justify-content: center;
                text-align: center;
            }

            .planner-hero::after {
                width: 120px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_hero_legacy(store_count: int, pending_count: int) -> None:
    hero_image = image_data_uri(HERO_IMAGE)
    image_html = f'<img class="planner-hero-image" src="{hero_image}" alt="韓系柔和路線插圖" />' if hero_image else ""
    st.markdown(
        f"""
        <div class="planner-hero">
            <div class="planner-topbar">
                <div class="planner-brand">
                    <div class="planner-logo">R</div>
                    <div>Route Mew</div>
                </div>
                <div class="planner-menu">
                    <a href="#route-input-top">今日清單</a>
                    <a href="#store-picker">門市挑選</a>
                    <a href="#route-result">路線結果</a>
                    <a href="#line-copy">LINE 文字</a>
                </div>
            </div>
            <div class="planner-hero-grid">
                <div>
                    <div class="planner-kicker">cute daily route planner</div>
                    <div class="planner-title">今天跑哪幾家，喵一下排好</div>
                    <div class="planner-subtitle">
                        貼上或勾選門市後，自動整理任務、拆分區域、排出順路行程，最後產生可轉傳的 LINE 文字。
                    </div>
                    <div class="planner-pills">
                        <span class="planner-pill">固定出發與返回：{HOME_ADDRESS}</span>
                        <span class="planner-pill">內建門市：{store_count} 家</span>
                        <span class="planner-pill">未完成記憶：{pending_count} 家</span>
                    </div>
                </div>
                <div class="planner-visual-stack">
                    <div class="cat-stage" aria-hidden="true">
                        <div class="cat-shadow"></div>
                        <div class="cat-star one"></div>
                        <div class="cat-star two"></div>
                        <div class="cat-star three"></div>
                        <div class="cat-sticker"></div>
                        <div class="cat-tail"></div>
                        <div class="cat-body"></div>
                        <div class="cat-head"></div>
                        <div class="cat-eye left"></div>
                        <div class="cat-eye right"></div>
                        <div class="cat-blush left"></div>
                        <div class="cat-blush right"></div>
                        <div class="cat-whisker left one"></div>
                        <div class="cat-whisker left two"></div>
                        <div class="cat-whisker right one"></div>
                        <div class="cat-whisker right two"></div>
                        <div class="cat-nose"></div>
                        <div class="cat-mouth"></div>
                        <div class="cat-arm left"></div>
                        <div class="cat-arm right"></div>
                        <div class="cat-paw one"></div>
                        <div class="cat-paw two"></div>
                    </div>
                    {image_html}
                    <div class="planner-hero-panel">
                        <div class="planner-panel-number">{pending_count}</div>
                        <div class="planner-panel-copy">家未完成會自動記得，下次打開不用重選。</div>
                        <div class="planner-mini-list">
                            <div class="planner-mini-row"><span>Start</span><span>艋舺大道 297 號</span></div>
                            <div class="planner-mini-row"><span>Plan</span><span>自動分區排序</span></div>
                            <div class="planner-mini-row"><span>Share</span><span>LINE 文字</span></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero(store_count: int, pending_count: int) -> None:
    hero_image = image_data_uri(HERO_IMAGE)
    image_html = (
        f'<img class="planner-hero-image" src="{hero_image}" alt="可愛貓咪路線規劃" />'
        if hero_image
        else ""
    )
    st.markdown(
        f"""
        <div class="planner-hero">
            <div class="planner-topbar">
                <div class="planner-brand">
                    <div class="planner-logo">R</div>
                    <div>Route Mew</div>
                </div>
                <div class="planner-menu">
                    <a href="#route-input-top">今日清單</a>
                    <a href="#store-picker">門市挑選</a>
                    <a href="#route-result">路線結果</a>
                    <a href="#line-copy">LINE 文字</a>
                </div>
            </div>
            <div class="planner-hero-grid">
                <div class="planner-hero-copy">
                    <div class="planner-eyebrow">CUTE DAILY ROUTE PLANNER</div>
                    <h1>今天跑哪幾家，喵一下排好</h1>
                    <p>貼上或勾選門市後，自動整理任務、拆分區域、排出順路行程，最後產生可轉傳的 LINE 文字。</p>
                    <div class="planner-chip-row">
                        <span>固定出發與返回：台北市萬華區艋舺大道297號</span>
                        <span>內建門市：{store_count} 家</span>
                        <span>未完成記憶：{pending_count} 家</span>
                    </div>
                </div>
                <div class="planner-hero-visual">
                    {image_html}
                    <div class="planner-hero-panel">
                        <div class="planner-panel-number">{pending_count}</div>
                        <div class="planner-panel-copy">今天還有 {pending_count} 家待安排，選好門市後就能立即規劃。</div>
                        <div class="planner-mini-list">
                            <div class="planner-mini-row"><span>Start</span><span>艋舺大道 297 號</span></div>
                            <div class="planner-mini-row"><span>Plan</span><span>自動排序路線</span></div>
                            <div class="planner-mini-row"><span>Share</span><span>LINE 文字</span></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_action_menu() -> None:
    st.markdown(
        """
        <div class="planner-menu-grid">
            <div class="planner-action">
                <div class="planner-action-icon">1</div>
                <div class="planner-action-title">貼上今日清單</div>
                <div class="planner-action-copy">直接貼 LINE 或手打店名，系統會自動抓門市與任務。</div>
            </div>
            <div class="planner-action">
                <div class="planner-action-icon">2</div>
                <div class="planner-action-title">勾選門市任務</div>
                <div class="planner-action-copy">收退貨、拍照、急件可直接勾，會帶到清單與摘要。</div>
            </div>
            <div class="planner-action">
                <div class="planner-action-icon">3</div>
                <div class="planner-action-title">自動排最順路</div>
                <div class="planner-action-copy">從艋舺大道出發並返回，保留距離與時間估算。</div>
            </div>
            <div class="planner-action">
                <div class="planner-action-icon">4</div>
                <div class="planner-action-title">複製 LINE 文字</div>
                <div class="planner-action-copy">整理好的順序、地址、導航連結可以直接轉傳。</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="planner-section-title">
            <div class="planner-section-dot"></div>
            <div>
                <h3>{title}</h3>
                <span>{subtitle}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="planner-card">
            <div class="planner-card-label">{label}</div>
            <div class="planner-card-value">{value}</div>
            <div class="planner-card-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def back_to_top_link() -> None:
    st.markdown(
        """
        <a href="#route-input-top" style="
            display: inline-block;
            margin: 0.25rem 0 0.75rem 0;
            padding: 0.45rem 0.75rem;
            border-radius: 0.5rem;
            border: 1px solid #d0d7de;
            background: #ffffff;
            color: #1f2937;
            text-decoration: none;
            font-size: 0.92rem;
        ">回到上方輸入清單</a>
        """,
        unsafe_allow_html=True,
    )


def add_store_entries_to_input(entries: list[str]) -> None:
    current = st.session_state.get("today_store_list", "")
    lines = [line.strip() for line in current.splitlines() if line.strip()]
    by_name: dict[str, str] = {}
    order: list[str] = []

    for line in lines:
        name = clean_input_line(line)
        if not name:
            continue
        if name not in by_name:
            order.append(name)
        by_name[name] = line

    changed = False
    for entry in entries:
        name = clean_input_line(entry)
        if not name:
            continue
        if name not in by_name:
            order.append(name)
            changed = True
        if by_name.get(name) != entry:
            by_name[name] = entry
            changed = True

    if not changed:
        return

    st.session_state["today_store_list"] = "\n".join(by_name[name] for name in order)
    st.session_state["show_plan"] = False


def sync_store_picker_to_input() -> None:
    editor_state = st.session_state.get("store_picker", {})
    edited_rows = editor_state.get("edited_rows", {}) if isinstance(editor_state, dict) else {}
    base_rows = st.session_state.get("store_picker_rows", [])
    entries = []
    for raw_idx, changes in edited_rows.items():
        try:
            idx = int(raw_idx)
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= len(base_rows):
            continue
        row = dict(base_rows[idx])
        row.update(changes)
        is_selected = bool(row.get("急件")) or bool(row.get("收退貨")) or bool(row.get("臨時交辦(拍照)"))
        if is_selected:
            entries.append(
                format_store_entry(
                    row["name"],
                    bool(row.get("急件", False)),
                    bool(row.get("收退貨", False)),
                    bool(row.get("臨時交辦(拍照)", False)),
                )
            )
    if entries:
        add_store_entries_to_input(entries)


def clear_today_store_list() -> None:
    st.session_state["today_store_list"] = ""
    st.session_state["show_plan"] = False


def stop_planning() -> None:
    st.session_state["show_plan"] = False


def configured_google_api_key() -> str:
    try:
        return str(st.secrets.get("GOOGLE_DISTANCE_MATRIX_API_KEY", "")).strip()
    except Exception:
        return ""


def load_pending_to_input() -> None:
    pending = load_pending_entries()
    if pending:
        st.session_state["today_store_list"] = "\n".join(pending)
        st.session_state["show_plan"] = False


def save_current_text_as_pending() -> None:
    current = st.session_state.get("today_store_list", "")
    entries = [line.strip() for line in current.splitlines() if line.strip()]
    save_pending_entries(entries)


def clear_pending_memory() -> None:
    clear_pending_entries()


def mark_route_done_and_save_remaining(matched_records: list[dict], planned_names: list[str]) -> None:
    done_names = set(planned_names)
    remaining_entries = [
        row_to_store_entry(pd.Series(record))
        for record in matched_records
        if record.get("name") not in done_names
    ]
    save_pending_entries(remaining_entries)
    st.session_state["today_store_list"] = "\n".join(remaining_entries)
    st.session_state["show_plan"] = False


def save_matched_as_pending(matched_records: list[dict]) -> None:
    entries = [row_to_store_entry(pd.Series(record)) for record in matched_records]
    save_pending_entries(entries)


def save_unfinished_from_status(status_records: list[dict]) -> None:
    remaining_entries = [
        format_store_entry(
            str(record["門市"]),
            "急件" in str(record.get("任務", "")),
            "收退貨" in str(record.get("任務", "")),
            "臨時交辦" in str(record.get("任務", "")) or "拍照" in str(record.get("任務", "")),
            extract_return_item(str(record.get("任務", ""))),
        )
        for record in status_records
        if not bool(record.get("已完成", False))
    ]
    save_pending_entries(remaining_entries)
    st.session_state["today_store_list"] = "\n".join(remaining_entries)
    st.session_state["show_plan"] = False


def start_planning() -> None:
    st.session_state["show_plan"] = True


def main() -> None:
    st.set_page_config(page_title="跑店小幫手", page_icon="🛵", layout="wide")
    inject_app_style()
    top_anchor()

    stores = pd.DataFrame(STORE_DATA)
    stores["normalized_name"] = stores["name"].map(normalize_name)

    pending_entries = load_pending_entries()
    render_hero(len(stores), len(pending_entries))
    render_action_menu()

    with st.sidebar:
        st.header("路線參數")
        start_at = st.time_input("第一家預計抵達時間", value=time(9, 30))
        stop_minutes = st.number_input("每店停留分鐘", min_value=5, max_value=180, value=DEFAULT_STOP_MINUTES, step=5)
        speed_kmh = st.number_input("機車平均時速 km/h", min_value=10, max_value=80, value=DEFAULT_SPEED_KMH, step=5)
        cloud_api_key = configured_google_api_key()
        manual_api_key = st.text_input("Google Distance Matrix API Key（可空白）", type="password")
        api_key = manual_api_key or cloud_api_key
        if cloud_api_key:
            st.caption("已載入 Streamlit Cloud Secret。")
        st.divider()
        st.metric("內建雙北超市", f"{len(stores)} 家")
        st.download_button(
            "下載內建門市 CSV",
            stores.drop(columns=["normalized_name"]).to_csv(index=False).encode("utf-8-sig"),
            file_name="carrefour_north_taiwan_stores.csv",
            mime="text/csv",
        )

    sample = "北投公館店\n士林雨聲店\n中和復興店\n板橋四維店\n新店安康二店"
    if "today_store_list" not in st.session_state:
        pending_entries = load_pending_entries()
        st.session_state["today_store_list"] = "\n".join(pending_entries) if pending_entries else sample
    if "show_plan" not in st.session_state:
        st.session_state["show_plan"] = False

    with st.sidebar:
        st.divider()
        st.header("未完成記憶")
        st.metric("下次自動帶入", f"{len(pending_entries)} 家")
        if pending_entries:
            st.caption("目前記憶：")
            st.code("\n".join(pending_entries), language="text")
        st.button("載入未完成", disabled=not pending_entries, on_click=load_pending_to_input, width="stretch")
        st.button("把目前輸入存成未完成", on_click=save_current_text_as_pending, width="stretch")
        st.button("清空未完成記憶", on_click=clear_pending_memory, width="stretch")

    input_cols = st.columns([1, 0.18])
    with input_cols[0]:
        section_title("今日清單", "貼 LINE 訊息或從下方門市表勾選任務")
        raw_text = st.text_area(
        "貼上今日巡店清單（可一行一店，也可直接貼 LINE 訊息）",
        key="today_store_list",
        height=180,
        help="支援 LINE 文字，也支援店名下一行放退貨品項，例如：北投明德店 下一行 規精19入。",
        )
    with input_cols[1]:
        st.write("")
        st.write("")
        st.button("清空清單", on_click=clear_today_store_list, width="stretch")

    st.button("開始規劃今日路線", type="primary", on_click=start_planning)

    if not st.session_state.get("show_plan"):
        st.markdown('<div id="store-picker"></div>', unsafe_allow_html=True)
        with st.expander("查看內建門市資料"):
            back_to_top_link()
            st.caption("先用分區或店名縮小範圍；勾選任務欄位後，店家會自動帶到上方輸入框。")
            store_view = stores.drop(columns=["normalized_name"]).reset_index(drop=True)
            filter_cols = st.columns([0.28, 0.72])
            with filter_cols[0]:
                selected_region_filter = st.selectbox(
                    "分區篩選",
                    options=["全部", *sorted(store_view["region"].drop_duplicates().tolist())],
                    key="store_region_filter",
                )
            with filter_cols[1]:
                store_search = st.text_input(
                    "搜尋店名或地址",
                    placeholder="例如：萬華、西藏、板橋",
                    key="store_search_text",
                )
            filtered_store_view = store_view.copy()
            if selected_region_filter != "全部":
                filtered_store_view = filtered_store_view[filtered_store_view["region"] == selected_region_filter]
            if store_search.strip():
                keyword = store_search.strip()
                filtered_store_view = filtered_store_view[
                    filtered_store_view["name"].str.contains(keyword, case=False, na=False)
                    | filtered_store_view["address"].str.contains(keyword, case=False, na=False)
                ]
            st.caption(f"目前顯示 {len(filtered_store_view)} 家")
            picker_view = filtered_store_view.reset_index(drop=True).copy()
            picker_view.insert(0, "急件", False)
            picker_view.insert(1, "收退貨", False)
            picker_view.insert(2, "臨時交辦(拍照)", False)
            st.session_state["store_picker_rows"] = picker_view.to_dict("records")
            st.data_editor(
                picker_view,
                width="stretch",
                hide_index=True,
                disabled=["name", "brand", "address", "lat", "lon", "region"],
                column_config={
                    "急件": st.column_config.CheckboxColumn("急件"),
                    "收退貨": st.column_config.CheckboxColumn("收退貨"),
                    "臨時交辦(拍照)": st.column_config.CheckboxColumn("臨時交辦(拍照)"),
                },
                key="store_picker",
                on_change=sync_store_picker_to_input,
            )
            st.info("勾選後若上方清單尚未更新，請再點一下頁面空白處或切換欄位，Streamlit 會自動重跑同步。")
            back_to_top_link()
        return

    st.markdown('<div id="route-result"></div>', unsafe_allow_html=True)
    lines = raw_text.splitlines()
    matched, misses = match_input_lines(lines, stores)
    if matched.empty:
        st.error("沒有比對到任何門市，請確認貼上的店名。")
        if misses:
            st.dataframe(pd.DataFrame(misses), width="stretch", hide_index=True)
        return

    plan_action_cols = st.columns([0.25, 0.75])
    with plan_action_cols[0]:
        st.button("返回修改清單/選店", on_click=stop_planning, width="stretch")
    with plan_action_cols[1]:
        st.caption("修改清單後再按一次「開始規劃今日路線」，系統會重新計算最順路線。")

    section_title("比對結果", "確認今天清單有抓到正確門市與任務")
    st.dataframe(
        matched[["input_name", "name", "任務", "brand", "region", "address", "match_score"]],
        width="stretch",
        hide_index=True,
    )
    if misses:
        st.warning("以下輸入沒有比對到，請手動確認：")
        st.dataframe(pd.DataFrame(misses), width="stretch", hide_index=True)

    regions = matched["region"].drop_duplicates().tolist()
    region_counts = matched["region"].value_counts().to_dict()
    spread_summary = region_summary(matched)
    region_count = len(spread_summary)
    if region_count >= HIGH_SPREAD_REGION_COUNT:
        st.error(f"防呆提醒：今日清單涵蓋了 {region_count} 個區域，路線太散，建議直接拆線。")
    elif region_count >= 2:
        st.warning(f"跨區提醒：今日清單涵蓋了 {region_count} 個區域，建議先確認是否要拆路線。")
    else:
        st.success("今日清單集中在單一區域，可以直接排路線。")

    with st.expander("跨區摘要與今日備忘", expanded=region_count >= 2):
        st.dataframe(spread_summary, width="stretch", hide_index=True)
        st.caption("給自己看的備忘：")
        st.code(today_memo_text(spread_summary), language="text")

    max_recommend_count = min(8, len(matched))
    recommend_count = st.radio(
        "今天最多想跑幾家",
        options=list(range(1, max_recommend_count + 1)),
        format_func=lambda value: f"跑 {value} 家",
        horizontal=True,
        help="選一個數字，程式會從待辦清單挑出急件優先、距離最順的組合。",
    )
    recommended_route, _recommended_visit_legs, recommend_reason = recommend_stores_by_count(
        matched,
        int(recommend_count),
        float(speed_kmh),
    )
    recommended_names = names_with_tasks(recommended_route)
    recommended_round_legs = round_trip_legs(recommended_route, "", float(speed_kmh))
    recommended_km, recommended_minutes = route_distance_summary(recommended_round_legs)
    st.success(f"建議今天跑：{recommended_names}")
    st.caption(f"{recommend_reason}；從 {HOME_ADDRESS} 出發並返回，預估騎乘 {recommended_km} km / {recommended_minutes} 分鐘。")
    st.dataframe(
        display_store_plan(recommended_route),
        width="stretch",
        hide_index=True,
    )

    route_options = [f"路線 {chr(65 + idx)}：{region}（{region_counts[region]} 家）" for idx, region in enumerate(regions)]
    selected = st.radio(
        "今日跑法（下方時程表會依這裡產生）",
        options=[f"使用自動建議（跑 {recommend_count} 家）", "硬著頭皮全跑（跨區自動排序）", *route_options],
        horizontal=False,
    )

    if selected.startswith("使用自動建議"):
        planning_df = recommended_route.copy()
        title = f"自動建議：跑 {recommend_count} 家"
    elif selected.startswith("路線"):
        region = selected.split("：", 1)[1].split("（", 1)[0]
        planning_df = matched[matched["region"] == region].copy()
        title = selected
    else:
        planning_df = matched.copy()
        title = "今日全跑路線"

    st.info(f"目前套用：{title}｜{names_with_tasks(planning_df)}")
    st.dataframe(
        display_store_plan(planning_df),
        width="stretch",
        hide_index=True,
    )
    remaining_count = max(0, len(matched) - len(planning_df))
    memory_cols = st.columns([0.34, 0.33, 0.33])
    with memory_cols[0]:
        st.button(
            f"這條已跑完，剩下 {remaining_count} 家存下次",
            on_click=mark_route_done_and_save_remaining,
            args=(matched.to_dict("records"), planning_df["name"].tolist()),
            width="stretch",
        )
    with memory_cols[1]:
        st.button(
            "全部先存成未完成",
            on_click=save_matched_as_pending,
            args=(matched.to_dict("records"),),
            width="stretch",
        )
    with memory_cols[2]:
        st.button("清空未完成記憶", on_click=clear_pending_memory, width="stretch")

    route, _visit_legs = nearest_neighbor_route(planning_df, api_key, float(speed_kmh))
    legs = round_trip_legs(route, api_key, float(speed_kmh))
    timeline = build_timeline(route, legs, start_at, int(stop_minutes))
    maps_url = google_maps_url(route)
    distance_km, ride_minutes = route_distance_summary(legs)

    if len(route) == 1:
        st.info(f"單店路線：今天只跑 {route.iloc[0]['name']}，會從 {HOME_ADDRESS} 出發，完成後再回到同一地址。")

    cols = st.columns(4)
    with cols[0]:
        metric_card("門市數", f"{len(route)} 家", "今日套用路線")
    with cols[1]:
        metric_card("騎乘距離", f"{distance_km} km", "含出發與返回")
    with cols[2]:
        metric_card("騎乘時間", f"{ride_minutes} 分鐘", f"每店停留 {int(stop_minutes)} 分鐘另計")
    with cols[3]:
        metric_card("分區數", f"{planning_df['region'].nunique()} 區", "越少越順路")

    left, right = st.columns([1.15, 0.85])
    with left:
        section_title("建議順序與時程", "依照目前選擇的跑法產生")
        st.dataframe(timeline, width="stretch", hide_index=True)
        st.caption(f"點對點騎乘估算（出發與返回：{HOME_ADDRESS}）")
        if legs:
            leg_df = pd.DataFrame(
                {
                    "起點": [leg.origin for leg in legs],
                    "終點": [leg.destination for leg in legs],
                    "公里": [round(leg.km, 1) for leg in legs],
                    "分鐘": [leg.minutes for leg in legs],
                    "來源": [leg.source for leg in legs],
                }
            )
            st.dataframe(leg_df, width="stretch", hide_index=True)
        else:
            st.info("目前沒有可計算的路線。")
        section_title("完成狀態", "勾選已跑完的店，剩下的可存到下次")
        status_df = timeline[["門市", "任務", "分區", "地址"]].copy()
        status_df.insert(0, "已完成", False)
        edited_status = st.data_editor(
            status_df,
            width="stretch",
            hide_index=True,
            disabled=["門市", "任務", "分區", "地址"],
            column_config={"已完成": st.column_config.CheckboxColumn("已完成")},
            key="completion_status",
        )
        st.button(
            "更新未完成記憶",
            on_click=save_unfinished_from_status,
            args=(edited_status.to_dict("records"),),
            width="stretch",
        )
    with right:
        section_title("地圖", "快速確認路線方向")
        render_map(route)
        st.link_button("開啟 Google Maps 導航", maps_url, width="stretch")

    st.markdown('<div id="line-copy"></div>', unsafe_allow_html=True)
    section_title("LINE 轉傳文字", "整理好的文字可以直接複製轉傳")
    st.code(line_text(title, timeline, legs, maps_url), language="text")
    back_to_top_link()


if __name__ == "__main__":
    main()

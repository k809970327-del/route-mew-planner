from __future__ import annotations

import html
import math
import re
import urllib.parse
from datetime import datetime, time, timedelta
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

HOME_ADDRESS = "台北市萬華區艋舺大道297號"
HOME_LAT = 25.0322
HOME_LON = 121.4939
ROAD_FACTOR = 1.4
DEFAULT_SPEED_KMH = 35
DEFAULT_STOP_MINUTES = 25
PENDING_FILE = Path(__file__).with_name("pending_store_list.json")
EXCLUDED_DISTRICTS = {"基隆市", "汐止區", "淡水區", "林口區", "深坑區"}
STORE_ALIASES = {"台北西藏店": "萬華西藏店", "西藏店": "萬華西藏店"}

RAW_STORES = [
    ("北投公館店", "台北市北投區公舘路198號"), ("北投致遠一店", "台北市北投區致遠一路二段19、21、23號"),
    ("北投光明店", "台北市北投區光明路220號1F"), ("北投明德店", "台北市北投區明德路161號B1樓"),
    ("士林雨聲店", "台北市士林區雨聲街52號、52-1號、52巷1號"), ("士林格致店", "台北市士林區格致路7號"),
    ("士林德行東店", "台北市士林區德行東路230號"), ("士林社中店", "台北市士林區社中街222號1樓"),
    ("士林華齡店", "台北市士林區華齡街175號"), ("台北太原店", "台北市大同區太原路155、157號"),
    ("台北重慶北店", "台北市大同區重慶北路1段73號B1"), ("台北酒泉店", "台北市大同區酒泉街105號"),
    ("台北同安店", "台北市中正區同安街71號"), ("台北羅斯福店", "台北市中正區羅斯福路3段285號B1"),
    ("台北大理店", "台北市萬華區大理街114號1樓"), ("台北長沙店", "台北市萬華區長沙街2段93號B1"),
    ("萬華西藏店", "台北市萬華區西藏路125巷13-15號"), ("台北萬大店", "台北市萬華區萬大路486巷48號1樓"),
    ("台北仁愛店", "台北市大安區仁愛路4段50-99, 50-100號B1"), ("台北仁愛二店", "台北市大安區仁愛路四段408號B1"),
    ("大安敦化南店", "台北市大安區敦化南路二段48號"), ("大安和平東店", "台北市大安區和平東路一段145號"),
    ("台北新生南店", "台北市大安區新生南路3段2號B1"), ("台北師大店", "台北市大安區師大路129號1樓"),
    ("台北信義店", "台北市大安區信義路4段296號B1"), ("台北四維店", "台北市大安區四維路198巷35號"),
    ("台北延吉店", "台北市大安區延吉街250號B1"), ("台北忠孝東店", "台北市大安區忠孝東路4段71號B1"),
    ("台北忠孝東二店", "台北市大安區忠孝東路3段218號B1"), ("台北農安店", "台北市中山區農安街257、259號"),
    ("台北農安二店", "台北市中山區農安街26、26-1號"), ("台北林森北店", "台北市中山區林森北路413號B1"),
    ("台北長安東店", "台北市中山區長安東路2段63、63-1、63-2號"), ("台北錦州店", "台北市中山區錦州街"),
    ("台北北安店", "台北市中山區北安路595巷11號, 13號"), ("台北八德店", "台北市松山區八德路4段83號"),
    ("台北光復店", "台北市松山區光復北路198號"), ("台北敦化北店", "台北市松山區敦化北路199巷5號"),
    ("台北松德店", "台北市信義區松德路99號B1"), ("內湖民權東店", "台北市內湖區民權東路6段296巷42-3號B1"),
    ("內湖成功二店", "台北市內湖區成功路2段320巷19號"), ("內湖康樂店", "台北市內湖區康樂街150號"),
    ("台北中坡南店", "台北市南港區中坡南路3號"), ("南港成福店", "台北市南港區成福路183號"),
    ("南港東明店", "台北市南港區東明街99號1樓"), ("南港舊莊店", "台北市南港區舊莊街一段196號"),
    ("文山木新店", "台北市文山區木新路二段158-1號"), ("文山景隆店", "台北市文山區景隆街36巷2號"),
    ("文山萬慶店", "台北市文山區萬慶街27號"), ("台北木柵店", "台北市文山區木柵路4段153號"),
    ("深坑北深店", "新北市深坑區北深路三段151號"), ("新店民族店", "新北市新店區民族路71號B1"),
    ("新店如意店", "新北市新店區如意街95、97號"), ("新店安康二店", "新北市新店區安康路二段136巷59號"),
    ("新店安康店", "新北市新店區安康路2段196號B1"), ("新店安祥店", "新北市新店區安祥路85-89號"),
    ("新店新坡一店", "新北市新店區新坡一街75號B1"), ("新店溪園店", "新北市新店區溪園路399號"),
    ("土城立德店", "新北市土城區立德路105號"), ("土城金城店", "新北市土城區金城路三段202-6號"),
    ("土城學府店", "新北市土城區學府路1段157, 161號"), ("永和仁愛店", "新北市永和區仁愛路152號B1"),
    ("永和竹林店", "新北市永和區竹林路60號"), ("中和中山店", "新北市中和區員山路489~497號1樓"),
    ("中和復興店", "新北市中和區復興路268號"), ("中和圓通店", "新北市中和區圓通路274號"),
    ("中和興南店", "新北市中和區興南路一段20號B1"), ("中和民治店", "新北市中和區民治街120號"),
    ("中和壽德店", "新北市中和區壽德街20號1樓"), ("板橋忠孝店", "新北市板橋區忠孝路237號"),
    ("板橋四維店", "新北市板橋區四維路247、249、251、253號"), ("板橋大觀店", "新北市板橋區大觀路3段236號1樓之14、1樓之15"),
    ("板橋金門二店", "新北市板橋區金門街153、155、159號"), ("樹林復興店", "新北市樹林區復興路198號"),
    ("樹林太順店", "新北市樹林區太順街64、66、68號"), ("樹林學成店", "新北市樹林區學成路536號"),
    ("三峽中山店", "新北市三峽區中山路171號"), ("三峽光明店", "新北市三峽區光明路71號"),
    ("三峽大學店", "新北市三峽區大學路119、121、123號1樓"), ("蘆洲三民店", "新北市蘆洲區三民路54號"),
    ("蘆洲中興店", "新北市蘆洲區中興街34、36號"), ("蘆洲長安二店", "新北市蘆洲區長安街387號1樓"),
    ("蘆洲長榮店", "新北市蘆洲區長榮路386號"), ("三重中正北店", "新北市三重區中正北路67、69號"),
    ("三重五華店", "新北市三重區五華街110巷1-4號"), ("三重仁愛二店", "新北市三重區仁愛街81號"),
    ("三重永福店", "新北市三重區永福街245、247、249號"), ("三重重陽店", "新北市三重區重陽路1段41號"),
    ("三重溪尾店", "新北市三重區溪尾街125號1樓"), ("新莊化成店", "新北市新莊區化成路193號"),
    ("新莊中平店", "新北市新莊區中平路377巷18、20號"), ("新莊中信店", "新北市新莊區中信街72號"),
    ("新莊昌隆店", "新北市新莊區昌隆街69、75、83號"), ("新莊公園一店", "新北市新莊區公園一路110號"),
    ("新莊後港一店", "新北市新莊區後港一路122-126號"), ("新莊富國店", "新北市新莊區富國路2號B1"),
    ("新莊龍安店", "新北市新莊區龍安路75號"), ("林口仁愛店", "新北市林口區仁愛路二段89號"),
    ("林口文化一店", "新北市林口區文化三路一段319、321、323、325號1樓"), ("林口文化三店", "新北市林口區文化三路一段543號"),
    ("五股成泰店", "新北市五股區成泰路一段235號之4"), ("五股西雲店", "新北市五股區西雲路169-1、171、171-1號"),
    ("五股明德店", "新北市五股區明德路12巷5號"), ("泰山明志店", "新北市泰山區明志路二段95-97號"),
]

REGION_BY_DISTRICT = {
    "北投區": "台北北區", "士林區": "台北北區", "大同區": "台北西區", "中正區": "台北中區", "萬華區": "台北西區",
    "大安區": "台北東區", "中山區": "台北中區", "松山區": "台北東區", "信義區": "台北東區", "內湖區": "台北東區",
    "南港區": "台北東區", "文山區": "台北南區", "新店區": "新北南區", "土城區": "新北西南區", "永和區": "新北西南區",
    "中和區": "新北西南區", "板橋區": "新北西南區", "樹林區": "新北西南區", "三峽區": "新北西南區", "蘆洲區": "新北西區",
    "三重區": "新北西區", "新莊區": "新北西區", "五股區": "新北西區", "泰山區": "新北西區",
}
DISTRICT_CENTERS = {
    "北投區": (25.1324, 121.5025), "士林區": (25.0950, 121.5246), "大同區": (25.0634, 121.5130), "中正區": (25.0324, 121.5196), "萬華區": (25.0337, 121.4977),
    "大安區": (25.0268, 121.5430), "中山區": (25.0643, 121.5335), "松山區": (25.0497, 121.5770), "信義區": (25.0330, 121.5666), "內湖區": (25.0695, 121.5898),
    "南港區": (25.0554, 121.6070), "文山區": (24.9898, 121.5705), "新店區": (24.9676, 121.5415), "土城區": (24.9722, 121.4437), "永和區": (25.0098, 121.5137),
    "中和區": (24.9993, 121.4980), "板橋區": (25.0114, 121.4638), "樹林區": (24.9907, 121.4206), "三峽區": (24.9343, 121.3693), "蘆洲區": (25.0849, 121.4706),
    "三重區": (25.0628, 121.4885), "新莊區": (25.0360, 121.4500), "五股區": (25.0840, 121.4380), "泰山區": (25.0587, 121.4329),
}


def inject_style() -> None:
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&display=swap');
    :root{--ink:#4b3b7a;--pink:#ff8fa3;--peach:#ffc0a8;--cream:#fff8e8;--lav:#efe6ff;--sky:#dff7ff;--mint:#dff6df;--shadow:rgba(97,69,124,.16)}
    .stApp{background:linear-gradient(135deg,#fff7df 0%,#ffe8f2 35%,#e8f4ff 70%,#f2e8ff 100%);background-image:radial-gradient(circle at 12% 18%,rgba(255,255,255,.75) 0 34px,transparent 35px),radial-gradient(circle at 24% 28%,rgba(255,255,255,.58) 0 25px,transparent 26px),radial-gradient(circle at 83% 23%,rgba(255,255,255,.70) 0 38px,transparent 39px),radial-gradient(circle at 93% 35%,rgba(255,255,255,.50) 0 28px,transparent 29px),linear-gradient(135deg,#fff7df 0%,#ffe8f2 35%,#e8f4ff 70%,#f2e8ff 100%);color:#54456d}
    .block-container{max-width:1080px;padding-top:1.1rem;padding-bottom:3rem;font-family:"Nunito","Microsoft JhengHei",sans-serif}
    .k-card,.route-card,.stDataFrame,.stDataEditor{background:rgba(255,250,239,.88);border:6px solid rgba(255,255,255,.92);border-radius:34px;padding:22px;margin:16px 0;box-shadow:0 18px 30px var(--shadow),0 8px 0 rgba(255,189,203,.18);backdrop-filter:blur(10px)}
    .k-hero{position:relative;overflow:hidden;min-height:310px;padding:24px 30px 30px;border:8px solid rgba(255,255,255,.95);border-radius:42px;background:radial-gradient(circle at 18% 30%,rgba(255,255,255,.95) 0 70px,transparent 72px),radial-gradient(circle at 82% 26%,rgba(255,255,255,.82) 0 74px,transparent 76px),linear-gradient(135deg,#fff1e6 0%,#ffe6f0 42%,#eef3ff 100%);box-shadow:0 22px 38px rgba(118,83,145,.18),0 12px 0 rgba(255,195,117,.16)}
    .k-hero:before{content:"";position:absolute;inset:0;background-image:radial-gradient(#ffe7aa 0 6px,transparent 7px),radial-gradient(#ffc6d4 0 5px,transparent 6px);background-size:82px 82px,118px 118px;background-position:12px 18px,44px 56px;opacity:.55;pointer-events:none}
    .k-hero:after{content:"";position:absolute;right:36px;bottom:38px;width:205px;height:112px;background:radial-gradient(circle at 28% 60%,#fff 0 36px,transparent 37px),radial-gradient(circle at 48% 43%,#fff 0 45px,transparent 46px),radial-gradient(circle at 70% 58%,#fff 0 38px,transparent 39px);filter:drop-shadow(0 15px 16px rgba(174,118,153,.18));opacity:.9}
    .k-nav{position:relative;z-index:2;text-align:right;margin-bottom:22px}.nav-pill,.pill{display:inline-block;background:rgba(255,255,255,.78);border:3px solid #ffd7a8;border-radius:999px;padding:9px 18px;margin:5px;color:#4b3b7a;font-weight:900;box-shadow:0 6px 14px rgba(174,118,153,.12)}
    .hero-copy{position:relative;z-index:2;max-width:650px;text-align:center;margin:auto}.k-title,.hero-title{font-size:56px;line-height:1.05;font-weight:900;color:#6642a5;margin:12px 0 10px;text-shadow:0 5px 0 rgba(255,255,255,.82)}.hero-title span{display:block;color:#ff8297}.hero-tag{display:inline-block;background:#ff8fa3;color:white;border:4px solid white;border-radius:999px;padding:10px 18px;font-weight:900;box-shadow:0 10px 16px rgba(255,143,163,.28)}.small,.hero-sub{color:#6e657c;line-height:1.75;font-size:17px;font-weight:700}.sparkles{font-size:26px;color:#ffd56c;letter-spacing:10px;margin:8px 0}
    h1,h2,h3,.stMarkdown strong{color:#4b3b7a!important}.task{color:#ec6f92;font-weight:900}.stButton>button,.stDownloadButton>button{border-radius:999px!important;border:4px solid white!important;background:linear-gradient(135deg,#ff9aa8,#ffb06f)!important;color:white!important;font-weight:900!important;box-shadow:0 9px 0 rgba(183,107,88,.18),0 14px 24px rgba(255,143,163,.25)!important;min-height:3.1rem!important}.stButton>button:hover{transform:translateY(-1px)}
    .stTextArea textarea,.stTextInput input{border-radius:28px!important;border:4px solid rgba(255,255,255,.86)!important;background:rgba(255,255,255,.86)!important;box-shadow:inset 0 0 0 1px rgba(255,183,201,.22),0 10px 24px rgba(110,86,140,.09)!important;font-size:18px!important;color:#54456d!important}.stExpander{border:0!important}.stExpander details{background:rgba(255,250,239,.82)!important;border:4px solid rgba(255,255,255,.9)!important;border-radius:28px!important;box-shadow:0 12px 26px rgba(97,69,124,.11)!important}
    [data-testid="stMetric"],[data-testid="stAlert"]{border-radius:28px!important}.stDataFrame,.stDataEditor{overflow:hidden;padding:0}.stDataFrame [role="grid"],.stDataEditor [role="grid"]{border-radius:26px!important;overflow:hidden}.element-container:has(.route-card){margin-bottom:.4rem}
    @media(max-width:700px){.block-container{padding-left:10px;padding-right:10px}.k-hero{min-height:300px;border-radius:30px;padding:16px 12px 24px}.k-nav{text-align:center;margin-bottom:10px}.nav-pill{padding:8px 12px;margin:3px;font-size:13px}.hero-title,.k-title{font-size:34px}.k-hero:after{right:-8px;bottom:12px;width:145px;height:82px;opacity:.55}.k-card,.route-card{border-radius:28px;padding:16px}.small,.hero-sub{font-size:15px}}
    </style>""", unsafe_allow_html=True)


def district_from_address(address: str) -> str:
    match = re.search(r"(台北市|新北市)([^市縣]+?區)", address)
    return match.group(2) if match else ""


def normalize_name(text: str) -> str:
    text = re.sub(r"[\s　:：｜|,，。．.\-_/()（）\[\]【】]+", "", str(text))
    for token in ["家樂福超市", "家樂福", "超市", "店"]:
        text = text.replace(token, "")
    return text


def build_stores() -> pd.DataFrame:
    rows = []
    for name, address in RAW_STORES:
        district = district_from_address(address)
        if any(ex in address for ex in EXCLUDED_DISTRICTS) or district in EXCLUDED_DISTRICTS:
            continue
        lat, lon = DISTRICT_CENTERS.get(district, (25.03, 121.52))
        rows.append({"name": name, "brand": "家樂福超市", "address": address, "lat": lat, "lon": lon, "region": REGION_BY_DISTRICT.get(district, "其他區"), "normalized_name": normalize_name(name)})
    return pd.DataFrame(rows)


def merge_task(existing: str, extra: str) -> str:
    parts = [part.strip() for part in f"{existing}；{extra}".split("；") if part.strip()]
    merged = []
    for part in parts:
        if part not in merged:
            merged.append(part)
    return "；".join(merged)


def parse_line(line: str) -> tuple[str, str]:
    tasks = []
    if "收退貨" in line or "退貨" in line:
        match = re.search(r"(?:收退貨|退貨)\s*[：:]?\s*(.+)$", line)
        item = match.group(1).strip(" ：:、,，") if match else ""
        item = re.sub(r"(拍照|臨時事件|臨時交辦)", "", item).strip(" ：:、,，")
        tasks.append(f"收退貨：{item}" if item else "收退貨")
    if "拍照" in line:
        tasks.append("拍照")
    if "臨時事件" in line or "臨時交辦" in line:
        tasks.append("臨時事件")
    name = re.split(r"收退貨|退貨|臨時事件|臨時交辦|拍照|[|｜]", line)[0].strip()
    return name, "；".join(tasks)


def build_picker_line(name: str, return_task: bool, photo_task: bool, urgent_task: bool) -> str:
    tasks = []
    if return_task:
        tasks.append("收退貨")
    if photo_task:
        tasks.append("拍照")
    if urgent_task:
        tasks.append("臨時事件")
    return f"{name} {' '.join(tasks)}" if tasks else name


def sync_store_picker_to_text() -> None:
    picker_state = st.session_state.get("store_picker_editor", {})
    base_rows = st.session_state.get("store_picker_rows", [])
    edited_rows = picker_state.get("edited_rows", {}) if isinstance(picker_state, dict) else {}
    selected = []
    for raw_index, changes in edited_rows.items():
        index = int(raw_index)
        if index >= len(base_rows):
            continue
        row = dict(base_rows[index])
        row.update(changes)
        if row.get("收退貨") or row.get("拍照") or row.get("臨時事件"):
            selected.append((
                row["name"],
                build_picker_line(row["name"], bool(row.get("收退貨")), bool(row.get("拍照")), bool(row.get("臨時事件"))),
            ))
    if not selected:
        return

    current_lines = [line.strip() for line in st.session_state.get("today_text", "").splitlines() if line.strip()]
    by_name = {}
    order = []
    for line in current_lines:
        name, _ = parse_line(line)
        if name not in by_name:
            order.append(name)
        by_name[name] = line
    for name, line in selected:
        if name not in by_name:
            order.append(name)
        by_name[name] = line
    st.session_state["today_text"] = "\n".join(by_name[name] for name in order if name in by_name)


def best_match_store(line: str, stores: pd.DataFrame):
    raw_name, task = parse_line(line)
    raw_name = STORE_ALIASES.get(raw_name, raw_name)
    norm = normalize_name(raw_name)
    compact = normalize_name(line)
    best = None
    best_score = 0.0
    best_trailing = ""
    for _, row in stores.iterrows():
        store_norm = row["normalized_name"]
        score = max(SequenceMatcher(None, norm, store_norm).ratio(), 1.0 if norm and (norm in store_norm or store_norm in norm) else 0.0)
        trailing = ""
        if compact.startswith(store_norm) and len(compact) > len(store_norm):
            score = 1.0
            trailing = compact[len(store_norm):]
        if score > best_score:
            best, best_score, best_trailing = row, score, trailing
    if best is not None and best_score >= 0.55:
        if not task and best_trailing:
            task = f"收退貨：{best_trailing}"
        return best, task, best_score
    return None, task, best_score


def match_inputs(text: str, stores: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    result, misses = [], []
    last_idx = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if last_idx is not None and ("臨時事件" in line or "臨時交辦" in line or "拍照" in line):
            _, task = parse_line(line)
            result[last_idx]["任務"] = merge_task(result[last_idx].get("任務", ""), task or "臨時事件")
            continue
        if last_idx is not None and not any(word in line for word in ["店", "家樂福", "收退貨", "退貨"]) and len(line) <= 24:
            old = result[last_idx].get("任務", "")
            result[last_idx]["任務"] = merge_task(old, f"收退貨：{line}")
            continue
        row, task, score = best_match_store(line, stores)
        if row is not None:
            rec = row.drop(labels=["normalized_name"]).to_dict()
            rec.update({"input_name": line, "任務": task, "match_score": round(score, 2)})
            result.append(rec)
            last_idx = len(result) - 1
        else:
            misses.append(line)
            last_idx = None
    return pd.DataFrame(result).drop_duplicates("name") if result else pd.DataFrame(), misses


def remaining_lines_after_done(text: str, stores: pd.DataFrame, done_names: set[str]) -> list[str]:
    remaining = []
    current_done = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        row, _, _ = best_match_store(line, stores)
        if row is not None:
            current_done = row["name"] in done_names
        if not current_done:
            remaining.append(line)
    return remaining


def complete_and_save(raw_text: str, stores: pd.DataFrame, done_names: set[str]) -> None:
    remaining = remaining_lines_after_done(raw_text, stores, done_names)
    save_pending(remaining)
    st.session_state["today_text"] = "\n".join(remaining)
    st.success(f"已自動保存剩餘 {len(remaining)} 筆。")
    st.rerun()


def haversine(a_lat, a_lon, b_lat, b_lon) -> float:
    radius = 6371
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = math.radians(b_lat - a_lat), math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def leg_km(a, b) -> float:
    return haversine(float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"])) * ROAD_FACTOR


def route_order(df: pd.DataFrame) -> pd.DataFrame:
    remaining = df.to_dict("records")
    current = {"lat": HOME_LAT, "lon": HOME_LON}
    ordered = []
    while remaining:
        nxt = min(remaining, key=lambda r: leg_km(current, r))
        ordered.append(nxt)
        remaining.remove(nxt)
        current = nxt
    return pd.DataFrame(ordered)


def maps_url(route: pd.DataFrame, current_location: bool = False) -> str:
    if route.empty:
        return "https://www.google.com/maps"
    dests = [f'{row["brand"]} {row["name"]} {row["address"]}' for _, row in route.iterrows()]
    params = {"api": "1", "travelmode": "driving", "destination": HOME_ADDRESS if len(dests) > 1 else dests[0]}
    if not current_location:
        params["origin"] = HOME_ADDRESS
    if len(dests) > 1:
        params["waypoints"] = "|".join(dests)
    return "https://www.google.com/maps/dir/?" + urllib.parse.urlencode(params, safe="|,")


def single_maps_url(row: pd.Series, current_location: bool = True) -> str:
    destination = f'{row.get("brand", "家樂福超市")} {row.get("name", row.get("門市", ""))} {row.get("address", row.get("地址", ""))}'
    params = {"api": "1", "travelmode": "driving", "destination": destination}
    if not current_location:
        params["origin"] = HOME_ADDRESS
    return "https://www.google.com/maps/dir/?" + urllib.parse.urlencode(params, safe=",")


def build_timeline(route: pd.DataFrame, start: time, stop_minutes: int, speed: int) -> tuple[pd.DataFrame, float, int]:
    rows, total_km, total_min = [], 0.0, 0
    current = {"lat": HOME_LAT, "lon": HOME_LON}
    cursor = datetime.combine(datetime.today(), start)
    for idx, row in route.reset_index(drop=True).iterrows():
        km = leg_km(current, row)
        mins = max(1, round(km / speed * 60))
        cursor += timedelta(minutes=mins)
        arrive = cursor
        leave = arrive + timedelta(minutes=stop_minutes)
        rows.append({"順序": idx + 1, "門市": row["name"], "任務": row.get("任務", ""), "分區": row["region"], "地址": row["address"], "抵達": arrive.strftime("%H:%M"), "離開": leave.strftime("%H:%M"), "公里": round(km, 1)})
        cursor = leave
        total_km += km
        total_min += mins + stop_minutes
        current = row
    if not route.empty:
        back_km = leg_km(route.iloc[-1], {"lat": HOME_LAT, "lon": HOME_LON})
        total_km += back_km
        total_min += max(1, round(back_km / speed * 60))
    return pd.DataFrame(rows), round(total_km, 1), total_min


def supabase_settings():
    try:
        url = str(st.secrets.get("SUPABASE_URL", "")).strip().rstrip("/")
        key = str(st.secrets.get("SUPABASE_SECRET_KEY", "") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
        user_id = str(st.secrets.get("APP_USER_ID", "candace")).strip() or "candace"
        return url, key, user_id
    except Exception:
        return "", "", "candace"


def auth_headers(key: str) -> dict[str, str]:
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def load_pending() -> list[str]:
    url, key, user_id = supabase_settings()
    if url and key:
        try:
            response = requests.get(f"{url}/rest/v1/route_state", headers=auth_headers(key), params={"user_id": f"eq.{user_id}", "select": "entries"}, timeout=8)
            if response.ok and response.json():
                return [str(item) for item in response.json()[0].get("entries", []) if str(item).strip()]
        except Exception:
            pass
    return []


def save_pending(entries: list[str]) -> None:
    url, key, user_id = supabase_settings()
    if not (url and key):
        return
    try:
        headers = auth_headers(key)
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
        requests.post(f"{url}/rest/v1/route_state", headers=headers, json={"user_id": user_id, "entries": entries, "updated_at": datetime.utcnow().isoformat()}, timeout=8)
    except Exception:
        pass


def require_pin() -> None:
    try:
        expected = str(st.secrets.get("APP_PIN", "")).strip()
    except Exception:
        expected = ""
    if not expected or st.session_state.get("pin_ok"):
        return
    st.markdown('<div class="k-card"><h1 class="k-title">跑店小幫手</h1><p class="small">請輸入密碼後繼續。</p></div>', unsafe_allow_html=True)
    value = st.text_input("密碼", type="password")
    if st.button("開啟工作清單"):
        if value == expected:
            st.session_state["pin_ok"] = True
            st.rerun()
        else:
            st.error("密碼不正確，請再試一次。")
    st.stop()


def line_text(route: pd.DataFrame, table: pd.DataFrame, km: float, mins: int, url: str) -> str:
    lines = [f"今日跑店：{len(route)} 家", f"預估：{km} km / {mins} 分鐘", ""]
    for _, row in table.iterrows():
        task = f"｜{row['任務']}" if row.get("任務") else ""
        lines.append(f"{row['順序']}. {row['門市']}{task} {row['抵達']}-{row['離開']}\n{row['地址']}")
    lines.extend(["", url])
    return "\n".join(lines)


def main() -> None:
    st.set_page_config(page_title="跑店小幫手", page_icon="🛵", layout="wide")
    inject_style()
    require_pin()
    stores = build_stores()
    if "today_text" not in st.session_state:
        st.session_state["today_text"] = "\n".join(load_pending())

    st.markdown(
        """
        <div class="k-hero">
          <div class="k-nav">
            <span class="nav-pill">今日清單</span>
            <span class="nav-pill">門市挑選</span>
            <span class="nav-pill">路線結果</span>
            <span class="nav-pill">LINE 文字</span>
          </div>
          <div class="hero-copy">
            <div class="hero-tag">Route Mew Planner</div>
            <div class="sparkles">★ ✦ ★</div>
            <h1 class="hero-title">今天跑哪幾家<span>喵一下排好</span></h1>
            <p class="hero-sub">從艋舺大道出發與返回。貼上清單或勾選門市後，自動整理收退貨、拍照、臨時事件與最順路線。</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    raw = st.text_area("今日清單", key="today_text", height=180, placeholder="台北長安東店 台糖頌精\n樹林學成店\n臨時交辦(拍照)")
    col_a, col_b = st.columns(2)
    with col_a:
        start_plan = st.button("開始規劃今日路線", type="primary", width="stretch")
    with col_b:
        if st.button("清空清單", width="stretch"):
            st.session_state["today_text"] = ""
            st.rerun()

    with st.expander("門市挑選 / 查地址"):
        keyword = st.text_input("搜尋門市或地址")
        view = stores if not keyword else stores[stores["name"].str.contains(keyword, na=False) | stores["address"].str.contains(keyword, na=False)]
        picker = view[["name", "brand", "region", "address"]].copy()
        picker.insert(0, "收退貨", False)
        picker.insert(1, "拍照", False)
        picker.insert(2, "臨時事件", False)
        st.session_state["store_picker_rows"] = picker.to_dict("records")
        st.caption("勾選後會自動帶入上方今日清單；同一家可同時勾多個任務。")
        st.data_editor(
            picker,
            key="store_picker_editor",
            hide_index=True,
            width="stretch",
            disabled=["name", "brand", "region", "address"],
            on_change=sync_store_picker_to_text,
            column_config={
                "收退貨": st.column_config.CheckboxColumn("收退貨"),
                "拍照": st.column_config.CheckboxColumn("拍照"),
                "臨時事件": st.column_config.CheckboxColumn("臨時事件"),
                "name": st.column_config.TextColumn("門市"),
                "brand": st.column_config.TextColumn("型態"),
                "region": st.column_config.TextColumn("分區"),
                "address": st.column_config.TextColumn("地址"),
            },
        )

    matched, misses = match_inputs(raw, stores)
    if not start_plan:
        if raw.strip():
            st.markdown('<div class="k-card"><b>比對預覽</b></div>', unsafe_allow_html=True)
            if not matched.empty:
                st.dataframe(matched[["input_name", "name", "任務", "region", "address"]], hide_index=True, width="stretch")
            if misses:
                st.warning("未比對到：" + "、".join(misses))
        return

    if matched.empty:
        st.error("沒有比對到門市，請確認店名。")
        return

    regions = matched["region"].nunique()
    if regions >= 2:
        st.warning(f"跨區提醒：今日清單涵蓋 {regions} 個區域。")

    route = route_order(matched)
    table, km, mins = build_timeline(route, time(9, 30), DEFAULT_STOP_MINUTES, DEFAULT_SPEED_KMH)
    full_url = maps_url(route, current_location=False)
    live_url = maps_url(route, current_location=True)

    st.markdown(f'<div class="k-card"><span class="pill">門市數 {len(route)} 家</span><span class="pill">{km} km</span><span class="pill">{mins} 分鐘</span><span class="pill">{regions} 區</span></div>', unsafe_allow_html=True)
    st.link_button("從目前位置接續導航", live_url, width="stretch")
    st.link_button("從艋舺大道出發導航", full_url, width="stretch")

    for _, row in table.iterrows():
        source = route[route["name"] == row["門市"]].iloc[0]
        st.markdown(f'<div class="route-card"><b>{row["順序"]}. {html.escape(row["門市"])}</b><div class="task">{html.escape(str(row.get("任務", "")))}</div><div>{row["抵達"]} - {row["離開"]}</div><div>{html.escape(row["地址"])}</div></div>', unsafe_allow_html=True)
        nav_col, done_col = st.columns([2, 1])
        with nav_col:
            st.link_button(f"導航到 {row['門市']}", single_maps_url(source, True), width="stretch")
        with done_col:
            if st.button(f"完成 {row['門市']}", key=f"done_{row['門市']}", width="stretch"):
                complete_and_save(raw, stores, {row["門市"]})

    st.dataframe(table, hide_index=True, width="stretch")
    status = table[["門市", "任務", "分區", "地址"]].copy()
    status.insert(0, "已完成", False)
    edited = st.data_editor(status, hide_index=True, width="stretch", disabled=["門市", "任務", "分區", "地址"])
    done = set(edited[edited["已完成"]]["門市"].tolist())
    if done:
        complete_and_save(raw, stores, done)

    st.markdown('<div class="k-card"><b>LINE 文字</b></div>', unsafe_allow_html=True)
    st.code(line_text(route, table, km, mins, full_url), language="text")


if __name__ == "__main__":
    main()

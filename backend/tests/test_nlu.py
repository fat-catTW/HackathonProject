"""§20.1 Unit Tests：欄位擷取與服務匹配。"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import nlu  # noqa: E402


TODAY = date(2026, 7, 21)  # 週二


def test_quantity_chinese():
    assert nlu.parse_quantity("清洗兩台冷氣") == 2
    assert nlu.parse_quantity("3台洗衣機") == 3
    assert nlu.parse_quantity("沒有數量") is None


def test_relative_dates():
    assert nlu.parse_date("明天下午", TODAY) == "2026-07-22"
    assert nlu.parse_date("後天", TODAY) == "2026-07-23"
    assert nlu.parse_date("下週三", TODAY) == "2026-07-29"
    assert nlu.parse_date("8月1日", TODAY) == "2026-08-01"
    assert nlu.parse_date("2026-08-15", TODAY) == "2026-08-15"


def test_time_slot():
    assert nlu.parse_time_slot("明天下午") == "AFTERNOON"
    assert nlu.parse_time_slot("早上比較方便") == "MORNING"
    assert nlu.parse_time_slot("晚上七點後") == "EVENING"


def test_phone():
    assert nlu.parse_phone("0912-345-678") == "0912345678"
    assert nlu.parse_phone("市話 02-27001234") == "0227001234"


def test_address_with_county_data():
    assert nlu.parse_address("地址是嘉義縣民雄鄉文隆村7鄰33號喔") == "嘉義縣民雄鄉文隆村7鄰33號"
    assert nlu.parse_address("臺北市大安區和平東路100號") == "台北市大安區和平東路100號"
    assert nlu.parse_address("沒有地址") is None


def test_service_matching():
    best, _ = nlu.detect_service("我要洗冷氣")
    assert best == "air_conditioner_cleaning"
    best, _ = nlu.detect_service("馬桶漏水")
    assert best == "plumbing_repair"
    best, _ = nlu.detect_service("洗衣機好臭")
    assert best == "washing_machine_cleaning"
    best, _ = nlu.detect_service("你好")
    assert best is None

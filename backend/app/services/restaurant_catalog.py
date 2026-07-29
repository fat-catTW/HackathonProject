"""Static restaurant directory for the restaurant reservation feature."""

RESTAURANTS: list[dict] = [
    {
        "id": "r001",
        "name": "22世紀風味館 信義旗艦店",
        "brand": "22世紀風味館",
        "address": "台北市信義區松高路12號3樓",
        "phone": "02-2723-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": True,
        "image_url": "/images/restaurants/r001.jpg",
    },
    {
        "id": "r002",
        "name": "22世紀風味館 板橋文化店",
        "brand": "22世紀風味館",
        "address": "新北市板橋區文化路一段280號2樓",
        "phone": "02-2258-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": True,
        "image_url": "/images/restaurants/r002.jpg",
    },
    {
        "id": "r003",
        "name": "22世紀風味館 台中公益店",
        "brand": "22世紀風味館",
        "address": "台中市南屯區公益路二段51號",
        "phone": "04-2326-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": False,
        "image_url": "/images/restaurants/r003.jpg",
    },
    {
        "id": "r004",
        "name": "22世紀風味館 高雄夢時代店",
        "brand": "22世紀風味館",
        "address": "高雄市前鎮區中華五路789號B1",
        "phone": "07-812-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": True,
        "image_url": "/images/restaurants/r004.jpg",
    },
    {
        "id": "r005",
        "name": "22世紀風味館 桃園中正店",
        "brand": "22世紀風味館",
        "address": "桃園市桃園區中正路1055號",
        "phone": "03-356-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": False,
        "verification_enabled": False,
        "image_url": "/images/restaurants/r005.jpg",
    },
    {
        "id": "r006",
        "name": "22世紀風味館 新竹巨城店",
        "brand": "22世紀風味館",
        "address": "新竹市東區中央路229號4樓",
        "phone": "03-623-0022",
        "cuisine": "複合式料理",
        "supports_booking_api": True,
        "verification_enabled": True,
        "image_url": "/images/restaurants/r006.jpg",
    },
]


def list_restaurants(limit: int = 6) -> list[dict]:
    return RESTAURANTS[:limit]


def get_restaurant(restaurant_id: str) -> dict | None:
    return next((r for r in RESTAURANTS if r["id"] == restaurant_id), None)


def supports_third_party_booking(restaurant_id: str) -> bool:
    restaurant = get_restaurant(restaurant_id)
    return bool(restaurant and restaurant["supports_booking_api"])

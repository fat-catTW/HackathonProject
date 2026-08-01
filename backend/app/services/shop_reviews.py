"""Static per-product review data and rating aggregation for the shop catalog.

Every product in shop_catalog.SHOP_PRODUCTS must have at least one entry here,
keyed by its own product_id — including the separate per-store product_ids for
the same physical item (e.g. prod_vitamin_c / prod_vitamin_c_lohas /
prod_vitamin_c_watsons), since a review reflects the experience of buying from
that specific store, not just the product itself.
"""
from __future__ import annotations

SHOP_REVIEWS: dict[str, list[dict]] = {
    "prod_tshirt_basic": [
        {"review_id": "rev_tshirt_basic_01", "author": "佳玲", "rating": 5, "comment": "布料摸起來很舒服，洗過幾次也沒變形，白色跟黑色我都買了。", "created_at": "2026-03-02", "verified_purchase": True},
        {"review_id": "rev_tshirt_basic_02", "author": "阿德", "rating": 4, "comment": "版型偏合身，怕熱的話買大一號比較好。", "created_at": "2026-04-18", "verified_purchase": True},
        {"review_id": "rev_tshirt_basic_03", "author": "小雨", "rating": 3, "comment": "顏色跟照片有點色差，但穿起來還算舒適。", "created_at": "2026-05-27", "verified_purchase": False},
    ],
    "prod_tumbler": [
        {"review_id": "rev_tumbler_01", "author": "Vincent", "rating": 5, "comment": "保冷真的有12小時，帶去爬山冰塊都還在。", "created_at": "2026-02-14", "verified_purchase": True},
        {"review_id": "rev_tumbler_02", "author": "美惠", "rating": 5, "comment": "粉色很好看，背帶設計外出很方便。", "created_at": "2026-03-09", "verified_purchase": True},
        {"review_id": "rev_tumbler_03", "author": "建宏", "rating": 4, "comment": "容量對男生來說偏小，但保溫效果不錯。", "created_at": "2026-06-01", "verified_purchase": True},
    ],
    "prod_coffee_coupon": [
        {"review_id": "rev_coffee_coupon_01", "author": "阿翔", "rating": 5, "comment": "全台門市都能兌換，出差在外地也用得到。", "created_at": "2026-03-20", "verified_purchase": True},
        {"review_id": "rev_coffee_coupon_02", "author": "淑芬", "rating": 4, "comment": "咖啡味道跟平常買的一樣，效期30天算夠用。", "created_at": "2026-04-05", "verified_purchase": True},
        {"review_id": "rev_coffee_coupon_03", "author": "阿哲", "rating": 3, "comment": "偶爾遇到門市咖啡機故障不能兌換，要換一家有點麻煩。", "created_at": "2026-05-11", "verified_purchase": False},
    ],
    "prod_onigiri_coupon": [
        {"review_id": "rev_onigiri_coupon_01", "author": "怡君", "rating": 5, "comment": "口味選擇多，鮭魚跟鮪魚都兌換過，很划算。", "created_at": "2026-02-22", "verified_purchase": True},
        {"review_id": "rev_onigiri_coupon_02", "author": "家豪", "rating": 4, "comment": "早餐救星，效期14天要記得快點用掉。", "created_at": "2026-03-30", "verified_purchase": True},
        {"review_id": "rev_onigiri_coupon_03", "author": "雅婷", "rating": 4, "comment": "門市庫存偶爾會缺貨，建議提早兌換。", "created_at": "2026-06-15", "verified_purchase": True},
    ],
    "prod_familymart_latte": [
        {"review_id": "rev_familymart_latte_01", "author": "俊傑", "rating": 5, "comment": "現萃口感比想像中濃郁，價格也划算。", "created_at": "2026-03-11", "verified_purchase": True},
        {"review_id": "rev_familymart_latte_02", "author": "詩涵", "rating": 4, "comment": "奶泡綿密，冰的熱的都好喝。", "created_at": "2026-04-25", "verified_purchase": True},
        {"review_id": "rev_familymart_latte_03", "author": "冠廷", "rating": 3, "comment": "早上尖峰時間排隊比較久。", "created_at": "2026-05-30", "verified_purchase": False},
    ],
    "prod_louisa_iced_americano": [
        {"review_id": "rev_louisa_iced_americano_01", "author": "品妤", "rating": 5, "comment": "路易莎的冰美式一直是我的最愛，兌換超方便。", "created_at": "2026-02-28", "verified_purchase": True},
        {"review_id": "rev_louisa_iced_americano_02", "author": "惠敏", "rating": 4, "comment": "咖啡因濃度夠，提神效果好。", "created_at": "2026-04-02", "verified_purchase": True},
        {"review_id": "rev_louisa_iced_americano_03", "author": "靜怡", "rating": 4, "comment": "門市不算多，要先查好離家近的分店。", "created_at": "2026-06-20", "verified_purchase": True},
    ],
    "prod_familymart_egg": [
        {"review_id": "rev_familymart_egg_01", "author": "阿宗", "rating": 5, "comment": "茶葉蛋滷得很入味，3顆份量剛好當點心。", "created_at": "2026-03-05", "verified_purchase": True},
        {"review_id": "rev_familymart_egg_02", "author": "佳玲", "rating": 4, "comment": "CP值高，效期14天記得盡快用掉。", "created_at": "2026-04-14", "verified_purchase": True},
        {"review_id": "rev_familymart_egg_03", "author": "阿德", "rating": 3, "comment": "蛋的大小不太一致，但味道沒問題。", "created_at": "2026-05-19", "verified_purchase": False},
    ],
    "prod_mos_fries": [
        {"review_id": "rev_mos_fries_01", "author": "小雨", "rating": 5, "comment": "薯條現炸的很酥脆，小份量剛好不會有罪惡感。", "created_at": "2026-02-18", "verified_purchase": True},
        {"review_id": "rev_mos_fries_02", "author": "Vincent", "rating": 4, "comment": "偶爾中午人多要等現炸，但值得等。", "created_at": "2026-04-08", "verified_purchase": True},
        {"review_id": "rev_mos_fries_03", "author": "美惠", "rating": 4, "comment": "配合套餐一起用更划算。", "created_at": "2026-06-03", "verified_purchase": True},
    ],
    "prod_daiso_storage_box": [
        {"review_id": "rev_daiso_storage_box_01", "author": "建宏", "rating": 5, "comment": "可堆疊設計很省空間，衣櫃整理一次到位。", "created_at": "2026-03-15", "verified_purchase": True},
        {"review_id": "rev_daiso_storage_box_02", "author": "阿翔", "rating": 4, "comment": "白色跟灰色都耐看，價格便宜可以多買幾個。", "created_at": "2026-04-21", "verified_purchase": True},
        {"review_id": "rev_daiso_storage_box_03", "author": "淑芬", "rating": 3, "comment": "塑膠材質偏薄，重物疊上去要小心。", "created_at": "2026-05-25", "verified_purchase": False},
    ],
    "prod_clean_spray": [
        {"review_id": "rev_clean_spray_01", "author": "阿哲", "rating": 5, "comment": "檸檬香味清爽，廚房油污噴一下就能擦掉。", "created_at": "2026-02-25", "verified_purchase": True},
        {"review_id": "rev_clean_spray_02", "author": "怡君", "rating": 4, "comment": "天然配方對敏感肌膚比較安心。", "created_at": "2026-03-28", "verified_purchase": True},
        {"review_id": "rev_clean_spray_03", "author": "家豪", "rating": 4, "comment": "浴室水垢要多噴幾次才有效。", "created_at": "2026-06-10", "verified_purchase": True},
    ],
    "prod_kitchen_wipes": [
        {"review_id": "rev_kitchen_wipes_01", "author": "雅婷", "rating": 5, "comment": "吸水力很好，廚房必備款，一次買好幾包。", "created_at": "2026-03-01", "verified_purchase": True},
        {"review_id": "rev_kitchen_wipes_02", "author": "俊傑", "rating": 4, "comment": "厚度夠，不容易破。", "created_at": "2026-04-11", "verified_purchase": True},
        {"review_id": "rev_kitchen_wipes_03", "author": "詩涵", "rating": 3, "comment": "抽取口設計偶爾會卡紙。", "created_at": "2026-05-16", "verified_purchase": False},
    ],
    "prod_vitamin_c": [
        {"review_id": "rev_vitamin_c_01", "author": "冠廷", "rating": 5, "comment": "檸檬口味不會太酸，泡完氣泡感十足。", "created_at": "2026-02-19", "verified_purchase": True},
        {"review_id": "rev_vitamin_c_02", "author": "品妤", "rating": 4, "comment": "感冒季節每天一錠，感覺比較不容易累。", "created_at": "2026-03-24", "verified_purchase": True},
        {"review_id": "rev_vitamin_c_03", "author": "惠敏", "rating": 4, "comment": "價格稍高但品牌信賴度夠。", "created_at": "2026-06-05", "verified_purchase": True},
    ],
    "prod_fish_oil": [
        {"review_id": "rev_fish_oil_01", "author": "靜怡", "rating": 5, "comment": "無腥味好吞嚥，吃了一個月精神狀況變好。", "created_at": "2026-03-08", "verified_purchase": True},
        {"review_id": "rev_fish_oil_02", "author": "阿宗", "rating": 4, "comment": "Omega-3濃度夠高，長輩也適合吃。", "created_at": "2026-04-17", "verified_purchase": True},
        {"review_id": "rev_fish_oil_03", "author": "佳玲", "rating": 3, "comment": "膠囊偏大，剛開始吞有點卡。", "created_at": "2026-05-22", "verified_purchase": False},
    ],
    "prod_vitamin_c_lohas": [
        {"review_id": "rev_vitamin_c_lohas_01", "author": "阿德", "rating": 5, "comment": "同款維他命C比健康藥妝便宜20元，直接改買這家。", "created_at": "2026-03-12", "verified_purchase": True},
        {"review_id": "rev_vitamin_c_lohas_02", "author": "小雨", "rating": 4, "comment": "出貨速度快，包裝完整。", "created_at": "2026-04-26", "verified_purchase": True},
        {"review_id": "rev_vitamin_c_lohas_03", "author": "Vincent", "rating": 4, "comment": "口味跟其他家一樣，價格是最大優勢。", "created_at": "2026-06-08", "verified_purchase": True},
    ],
    "prod_vitamin_c_watsons": [
        {"review_id": "rev_vitamin_c_watsons_01", "author": "美惠", "rating": 5, "comment": "屈臣氏買維他命C很方便，門市多好取貨。", "created_at": "2026-02-27", "verified_purchase": True},
        {"review_id": "rev_vitamin_c_watsons_02", "author": "建宏", "rating": 4, "comment": "價格中規中矩，服務態度不錯。", "created_at": "2026-04-06", "verified_purchase": True},
        {"review_id": "rev_vitamin_c_watsons_03", "author": "阿翔", "rating": 3, "comment": "常常缺貨要多跑幾家分店。", "created_at": "2026-05-14", "verified_purchase": False},
    ],
    "prod_clean_spray_miaojie": [
        {"review_id": "rev_clean_spray_miaojie_01", "author": "淑芬", "rating": 5, "comment": "跟舒潔那款一樣好用，價格更划算。", "created_at": "2026-03-18", "verified_purchase": True},
        {"review_id": "rev_clean_spray_miaojie_02", "author": "阿哲", "rating": 4, "comment": "茶樹味道清新，廚房浴室都能用。", "created_at": "2026-04-29", "verified_purchase": True},
        {"review_id": "rev_clean_spray_miaojie_03", "author": "怡君", "rating": 4, "comment": "瓶身噴頭設計順手。", "created_at": "2026-06-12", "verified_purchase": True},
    ],
    "prod_clean_spray_carrefour": [
        {"review_id": "rev_clean_spray_carrefour_01", "author": "家豪", "rating": 5, "comment": "家樂福這款最便宜，效果跟其他家沒差。", "created_at": "2026-02-21", "verified_purchase": True},
        {"review_id": "rev_clean_spray_carrefour_02", "author": "雅婷", "rating": 4, "comment": "大罐屯貨划算，量販店買一次夠用很久。", "created_at": "2026-04-03", "verified_purchase": True},
        {"review_id": "rev_clean_spray_carrefour_03", "author": "俊傑", "rating": 3, "comment": "噴頭偶爾會卡住，要搖一搖才順。", "created_at": "2026-05-28", "verified_purchase": False},
    ],
    "prod_tumbler_daiso": [
        {"review_id": "rev_tumbler_daiso_01", "author": "詩涵", "rating": 5, "comment": "跟統一時代同款但便宜100元，划算。", "created_at": "2026-03-06", "verified_purchase": True},
        {"review_id": "rev_tumbler_daiso_02", "author": "冠廷", "rating": 4, "comment": "保冷效果不錯，藍色顏色很好看。", "created_at": "2026-04-19", "verified_purchase": True},
        {"review_id": "rev_tumbler_daiso_03", "author": "品妤", "rating": 4, "comment": "背帶稍微陽春，但功能沒問題。", "created_at": "2026-06-17", "verified_purchase": True},
    ],
    "prod_tumbler_watsons": [
        {"review_id": "rev_tumbler_watsons_01", "author": "惠敏", "rating": 4, "comment": "屈臣氏買比較方便，價格中等。", "created_at": "2026-03-23", "verified_purchase": True},
        {"review_id": "rev_tumbler_watsons_02", "author": "靜怡", "rating": 4, "comment": "顏色選擇跟其他家一樣，取貨快。", "created_at": "2026-05-02", "verified_purchase": True},
        {"review_id": "rev_tumbler_watsons_03", "author": "阿宗", "rating": 3, "comment": "價格比大創貴一些，但門市多是加分。", "created_at": "2026-06-22", "verified_purchase": False},
    ],
    "prod_mic_fifine_k669b": [
        {"review_id": "rev_fifine_k669b_01", "author": "阿凱", "rating": 5, "comment": "第一次錄 podcast 就用這支，收音乾淨、價格親民，新手很夠用。", "created_at": "2026-05-12", "verified_purchase": True},
        {"review_id": "rev_fifine_k669b_02", "author": "小美", "rating": 4, "comment": "USB接上就能用，完全不用調設定，很適合入門。", "created_at": "2026-06-03", "verified_purchase": True},
        {"review_id": "rev_fifine_k669b_03", "author": "志明", "rating": 3, "comment": "拿來玩遊戲語音沒問題，但錄音室等級的細節還是差一截。", "created_at": "2026-06-25", "verified_purchase": True},
    ],
    "prod_mic_blue_yeti_x": [
        {"review_id": "rev_blue_yeti_x_01", "author": "春嬌", "rating": 5, "comment": "業界經典不是叫假的，四種指向模式錄訪談很方便切換。", "created_at": "2026-04-20", "verified_purchase": True},
        {"review_id": "rev_blue_yeti_x_02", "author": "阿豪", "rating": 5, "comment": "耳機孔即時監聽超實用，聲音細膩，podcast用起來很專業。", "created_at": "2026-05-15", "verified_purchase": True},
        {"review_id": "rev_blue_yeti_x_03", "author": "雨萱", "rating": 4, "comment": "體積比想像中大，桌面空間要留意，但音質真的沒話說。", "created_at": "2026-06-30", "verified_purchase": True},
    ],
    "prod_mic_rode_nt_usb_mini": [
        {"review_id": "rev_rode_nt_usb_mini_01", "author": "承翰", "rating": 5, "comment": "體積小巧放在小桌子剛剛好，磁吸架很穩不會震動收音。", "created_at": "2026-05-02", "verified_purchase": True},
        {"review_id": "rev_rode_nt_usb_mini_02", "author": "怡君", "rating": 5, "comment": "收音真的很乾淨，背景雜音壓得很好，適合在家錄音。", "created_at": "2026-05-24", "verified_purchase": True},
        {"review_id": "rev_rode_nt_usb_mini_03", "author": "家豪", "rating": 4, "comment": "外型簡約好看，就是配件比較陽春。", "created_at": "2026-06-14", "verified_purchase": False},
    ],
    "prod_mic_hyperx_quadcast_s": [
        {"review_id": "rev_hyperx_quadcast_s_01", "author": "俊傑", "rating": 5, "comment": "RGB燈效直播畫面加分，音質對電競實況來說很夠用。", "created_at": "2026-04-28", "verified_purchase": True},
        {"review_id": "rev_hyperx_quadcast_s_02", "author": "詩涵", "rating": 4, "comment": "內建防震架跟防噴罩省了額外採購，開箱就能用。", "created_at": "2026-05-19", "verified_purchase": True},
        {"review_id": "rev_hyperx_quadcast_s_03", "author": "冠廷", "rating": 3, "comment": "價格偏高，如果不需要RGB其實有更划算的選擇。", "created_at": "2026-06-27", "verified_purchase": True},
    ],
    "prod_mic_atr2100x_usb": [
        {"review_id": "rev_atr2100x_usb_01", "author": "品妤", "rating": 5, "comment": "雙人訪談用USB接兩支剛剛好，動圈式對環境噪音抑制很有感。", "created_at": "2026-05-08", "verified_purchase": True},
        {"review_id": "rev_atr2100x_usb_02", "author": "惠敏", "rating": 5, "comment": "XLR/USB雙介面很彈性，之後要升級混音器也能直接接。", "created_at": "2026-05-30", "verified_purchase": True},
        {"review_id": "rev_atr2100x_usb_03", "author": "靜怡", "rating": 4, "comment": "戶外收音也試過，抗噪表現不錯，就是機身偏重。", "created_at": "2026-06-18", "verified_purchase": False},
    ],
    "prod_mic_shure_mv7": [
        {"review_id": "rev_shure_mv7_01", "author": "承翰", "rating": 5, "comment": "自動增益超好用，不用自己調輸入音量，收音水準直接拉到電台等級。", "created_at": "2026-05-10", "verified_purchase": True},
        {"review_id": "rev_shure_mv7_02", "author": "雨萱", "rating": 5, "comment": "USB跟XLR都能接，之後要升級混音器完全不用換麥克風，一次到位。", "created_at": "2026-06-01", "verified_purchase": True},
        {"review_id": "rev_shure_mv7_03", "author": "阿豪", "rating": 4, "comment": "音質沒話說，就是價格不便宜，新手可能會猶豫。", "created_at": "2026-06-23", "verified_purchase": True},
    ],
    "prod_mic_elgato_wave3": [
        {"review_id": "rev_elgato_wave3_01", "author": "志明", "rating": 5, "comment": "Wave Link軟體可以分開控制遊戲聲跟麥克風音量，直播剪輯都方便。", "created_at": "2026-05-06", "verified_purchase": True},
        {"review_id": "rev_elgato_wave3_02", "author": "小美", "rating": 4, "comment": "防爆音技術真的有感，講話比較激動也不會噴麥。", "created_at": "2026-05-28", "verified_purchase": True},
        {"review_id": "rev_elgato_wave3_03", "author": "春嬌", "rating": 4, "comment": "外型簡約好看，軟體剛開始設定要花點時間熟悉。", "created_at": "2026-06-17", "verified_purchase": False},
    ],
    "prod_mic_samson_q2u": [
        {"review_id": "rev_samson_q2u_01", "author": "冠廷", "rating": 5, "comment": "價格是同類最便宜的，還附麥克風架跟收納袋，新手練習錄音很划算。", "created_at": "2026-05-14", "verified_purchase": True},
        {"review_id": "rev_samson_q2u_02", "author": "詩涵", "rating": 4, "comment": "USB接電腦直接用，XLR之後要接混音器也可以，彈性不錯。", "created_at": "2026-06-05", "verified_purchase": True},
        {"review_id": "rev_samson_q2u_03", "author": "俊傑", "rating": 3, "comment": "這個價位的音質已經很不錯，但跟高階款比細節還是有差。", "created_at": "2026-06-26", "verified_purchase": True},
    ],
    "prod_webcam_logitech_c920": [
        {"review_id": "rev_webcam_logitech_c920_01", "author": "阿宗", "rating": 5, "comment": "1080p畫質視訊會議很夠用，自動對焦反應快。", "created_at": "2026-04-15", "verified_purchase": True},
        {"review_id": "rev_webcam_logitech_c920_02", "author": "佳玲", "rating": 4, "comment": "搭配麥克風錄podcast影片版剛剛好，色彩還原不錯。", "created_at": "2026-05-21", "verified_purchase": True},
        {"review_id": "rev_webcam_logitech_c920_03", "author": "阿德", "rating": 4, "comment": "夾式支架穩固，就是低光源環境畫質會偏暗。", "created_at": "2026-06-09", "verified_purchase": True},
    ],
    "prod_audio_interface_scarlett_solo": [
        {"review_id": "rev_scarlett_solo_01", "author": "小雨", "rating": 5, "comment": "入門錄音介面首選，接上XLR麥克風音質提升很明顯。", "created_at": "2026-05-04", "verified_purchase": True},
        {"review_id": "rev_scarlett_solo_02", "author": "Vincent", "rating": 4, "comment": "操作介面直覺，第一次用類比介面也很快上手。", "created_at": "2026-05-26", "verified_purchase": True},
        {"review_id": "rev_scarlett_solo_03", "author": "美惠", "rating": 4, "comment": "想從純USB麥克風升級雙軌訪談的話這台很適合，但要另外買麥克風線。", "created_at": "2026-06-19", "verified_purchase": False},
    ],
    "prod_gpu_msi_rtx5090": [
        {"review_id": "rev_rtx5090_01", "author": "阿凱", "rating": 5, "comment": "4K全開跑起來完全不卡，玩最新遊戲跟跑AI模型都很順。", "created_at": "2026-05-09", "verified_purchase": True},
        {"review_id": "rev_rtx5090_02", "author": "志明", "rating": 5, "comment": "散熱表現比想像中安靜，滿載溫度也控制得不錯。", "created_at": "2026-06-02", "verified_purchase": True},
        {"review_id": "rev_rtx5090_03", "author": "雨萱", "rating": 4, "comment": "效能無話可說，就是體積很大，買之前要先量機殼空間。", "created_at": "2026-06-24", "verified_purchase": True},
    ],
    "prod_laptop_asus_rog": [
        {"review_id": "rev_asus_rog_01", "author": "承翰", "rating": 5, "comment": "240Hz螢幕玩FPS遊戲反應很快，散熱系統也壓得住長時間遊玩。", "created_at": "2026-05-11", "verified_purchase": True},
        {"review_id": "rev_asus_rog_02", "author": "小美", "rating": 4, "comment": "剪片跑轉檔速度明顯比舊筆電快很多，重量偏重外出攜帶要考慮。", "created_at": "2026-06-04", "verified_purchase": True},
        {"review_id": "rev_asus_rog_03", "author": "春嬌", "rating": 4, "comment": "曜岩黑質感很好，風扇全速時聲音有點明顯。", "created_at": "2026-06-21", "verified_purchase": False},
    ],
    "prod_keyboard_keychron_k8pro": [
        {"review_id": "rev_keychron_k8pro_01", "author": "阿豪", "rating": 5, "comment": "低軸體打字手感很輕盈，無線延遲完全感覺不出來。", "created_at": "2026-05-07", "verified_purchase": True},
        {"review_id": "rev_keychron_k8pro_02", "author": "詩涵", "rating": 5, "comment": "RGB燈效可以自訂分區，配色跟電競桌面很搭。", "created_at": "2026-05-29", "verified_purchase": True},
        {"review_id": "rev_keychron_k8pro_03", "author": "冠廷", "rating": 3, "comment": "手感偏軟，喜歡段落感的人可能不習慣，但打字很安靜。", "created_at": "2026-06-16", "verified_purchase": True},
    ],
    "prod_headphone_sony_xm6": [
        {"review_id": "rev_sony_xm6_01", "author": "品妤", "rating": 5, "comment": "降噪效果真的是業界標竿，搭高鐵通勤整個世界都安靜了。", "created_at": "2026-05-13", "verified_purchase": True},
        {"review_id": "rev_sony_xm6_02", "author": "惠敏", "rating": 5, "comment": "續航力很扎實，出國一趟充電次數少很多。", "created_at": "2026-06-06", "verified_purchase": True},
        {"review_id": "rev_sony_xm6_03", "author": "靜怡", "rating": 4, "comment": "音質跟降噪都很滿意，就是價格偏高。", "created_at": "2026-06-28", "verified_purchase": True},
    ],
}


def list_reviews(product_id: str) -> list[dict]:
    return list(SHOP_REVIEWS.get(product_id, []))


def get_rating_summary(product_id: str) -> dict:
    reviews = SHOP_REVIEWS.get(product_id, [])
    if not reviews:
        return {"rating_avg": 0.0, "rating_count": 0}
    avg = sum(r["rating"] for r in reviews) / len(reviews)
    return {"rating_avg": round(avg, 1), "rating_count": len(reviews)}

from dataclasses import dataclass


@dataclass
class MetricDefinition:
    key: str
    category: str
    is_additive: bool
    format_type: str  # 'currency', 'integer', 'percent', 'decimal'
    ru_label: str
    uz_label: str
    en_label: str
    tooltip_ru: str
    tooltip_uz: str
    tooltip_en: str
    meta_field: str | None = None
    meta_action_type: str | None = None
    is_limited: bool = False
    sample_value: float = 0.0

METRIC_DEFINITIONS: dict[str, MetricDefinition] = {
    "spend": MetricDefinition(
        key="spend",
        category="core",
        is_additive=True,
        format_type="currency",
        ru_label="Расход",
        uz_label="Sarflangan mablag'",
        en_label="Spend",
        tooltip_ru="Общая сумма расходов на рекламу за выбранный период",
        tooltip_uz="Tanlangan davr uchun reklamaga sarflangan jami mablag'",
        tooltip_en="Total amount spent on ads during the selected period",
        meta_field="spend",
        sample_value=145.20
    ),
    "impressions": MetricDefinition(
        key="impressions",
        category="core",
        is_additive=True,
        format_type="integer",
        ru_label="Показы",
        uz_label="Ko'rsatishlar",
        en_label="Impressions",
        tooltip_ru="Количество показов вашей рекламы на экранах",
        tooltip_uz="Reklamangiz ekranda ko'rsatilgan martalar soni",
        tooltip_en="Number of times your ads were on screen",
        meta_field="impressions",
        sample_value=28450
    ),
    "reach": MetricDefinition(
        key="reach",
        category="core",
        is_additive=False,  # Evaluated deduplicated via account level insights
        format_type="integer",
        ru_label="Охват",
        uz_label="Qamrov",
        en_label="Reach",
        tooltip_ru="Количество уникальных пользователей, увидевших рекламу хотя бы раз",
        tooltip_uz="Reklamani kamida bir marta ko'rgan unikal foydalanuvchilar soni",
        tooltip_en="Number of unique people who saw your ads at least once",
        meta_field="reach",
        sample_value=21300
    ),
    "clicks": MetricDefinition(
        key="clicks",
        category="traffic",
        is_additive=True,
        format_type="integer",
        ru_label="Клики (все)",
        uz_label="Bosishlar (jami)",
        en_label="Clicks (all)",
        tooltip_ru="Все клики по объявлению, включая клики на профиль, реакцию и 'ещё'",
        tooltip_uz="Reklamadagi barcha bosishlar (profil, munosabat, batafsil)",
        tooltip_en="Total clicks on your ad, including page title, post reactions, 'read more'",
        meta_field="clicks",
        sample_value=1280
    ),
    "link_clicks": MetricDefinition(
        key="link_clicks",
        category="traffic",
        is_additive=True,
        format_type="integer",
        ru_label="Клики по ссылке",
        uz_label="Havola bosishlari",
        en_label="Link Clicks",
        tooltip_ru="Клики, которые перенаправляют на внешний сайт, лендинг или форму",
        tooltip_uz="Tashqi sayt, lending yoki formaga olib boruvchi bosishlar",
        tooltip_en="Clicks on ad links that take people to destination experiences",
        meta_field="inline_link_clicks",
        meta_action_type="link_click",
        sample_value=840
    ),
    "profile_visits": MetricDefinition(
        key="profile_visits",
        category="traffic",
        is_additive=True,
        format_type="integer",
        ru_label="Посещения профиля",
        uz_label="Profil tashriflari",
        en_label="Profile Visits",
        tooltip_ru="Клики по названию профиля или аватару (Meta API: доступно не для всех типов объявлений)",
        tooltip_uz="Profil nomi yoki rasmiga bosishlar (Meta API cheklovlari bo'lishi mumkin)",
        tooltip_en="Clicks to view advertiser profile (Meta API: limited availability)",
        meta_action_type="onsite_conversion.messaging_user_profile_click",
        is_limited=True,
        sample_value=120
    ),
    "landing_page_views": MetricDefinition(
        key="landing_page_views",
        category="traffic",
        is_additive=True,
        format_type="integer",
        ru_label="Просмотры лендинга",
        uz_label="Lending sahifasi ko'rishlari",
        en_label="Landing Page Views",
        tooltip_ru="Успешные загрузки целевой страницы после клика по ссылке",
        tooltip_uz="Havola bosilgandan so'ng sahifaning to'liq yuklanishi",
        tooltip_en="Number of times a person clicked an ad link and then successfully loaded the destination webpage",
        meta_action_type="landing_page_view",
        sample_value=720
    ),
    "ctr": MetricDefinition(
        key="ctr",
        category="efficiency",
        is_additive=False,
        format_type="percent",
        ru_label="CTR (все клики)",
        uz_label="CTR (jami bosishlar)",
        en_label="CTR (all clicks)",
        tooltip_ru="Процент показов, закончившихся кликом (Клики / Показы * 100)",
        tooltip_uz="Bosishlar foizi (Bosishlar / Ko'rsatishlar * 100)",
        tooltip_en="Percentage of times people saw your ad and performed a click",
        sample_value=4.50
    ),
    "ctr_link": MetricDefinition(
        key="ctr_link",
        category="efficiency",
        is_additive=False,
        format_type="percent",
        ru_label="CTR (клики по ссылке)",
        uz_label="CTR (Havola bosish)",
        en_label="CTR (link clicks)",
        tooltip_ru="Процент показов, приведших к клику по целевой ссылке",
        tooltip_uz="Havolani bosish ko'rsatkichi foizda",
        tooltip_en="Percentage of times people saw your ad and clicked a destination link",
        sample_value=2.95
    ),
    "cpc": MetricDefinition(
        key="cpc",
        category="efficiency",
        is_additive=False,
        format_type="currency",
        ru_label="CPC",
        uz_label="CPC",
        en_label="CPC",
        tooltip_ru="Средняя стоимость одного клика (Расход / Клики)",
        tooltip_uz="Bitta bosish o'rtacha narxi (Mablag' / Bosishlar)",
        tooltip_en="Average cost for each click",
        sample_value=0.11
    ),
    "cpm": MetricDefinition(
        key="cpm",
        category="efficiency",
        is_additive=False,
        format_type="currency",
        ru_label="CPM",
        uz_label="CPM",
        en_label="CPM",
        tooltip_ru="Стоимость за 1,000 показов объявления (Расход / Показы * 1000)",
        tooltip_uz="1 000 ta ko'rsatish narxi",
        tooltip_en="Average cost for 1,000 impressions",
        sample_value=5.10
    ),
    "cpp": MetricDefinition(
        key="cpp",
        category="efficiency",
        is_additive=False,
        format_type="currency",
        ru_label="CPP (цена за 1000 охвата)",
        uz_label="CPP (1000 qamrov narxi)",
        en_label="CPP (Cost per 1,000 Reach)",
        tooltip_ru="Стоимость охвата 1,000 уникальных людей (Расход / Охват * 1000)",
        tooltip_uz="1 000 ta unikal odamni qamrab olish narxi",
        tooltip_en="Cost to reach 1,000 unique people",
        sample_value=6.82
    ),
    "new_followers": MetricDefinition(
        key="new_followers",
        category="engagement",
        is_additive=True,
        format_type="integer",
        ru_label="Новые подписчики",
        uz_label="Yangi obunachilar",
        en_label="New Followers",
        tooltip_ru="Отметки «Нравится» страницы Facebook с рекламы (Meta API: подписчики Instagram не поддерживаются в Insights)",
        tooltip_uz="Facebook sahifasiga obuna bo'lishlar (Meta API Instagram obunachilarini bermaydi)",
        tooltip_en="Facebook Page likes/follows attributed to ads (Instagram followers not supported in Ads Insights)",
        meta_action_type="like",
        is_limited=True,
        sample_value=35
    ),
    "leads": MetricDefinition(
        key="leads",
        category="conversions",
        is_additive=True,
        format_type="integer",
        ru_label="Лиды",
        uz_label="Lidlar",
        en_label="Leads",
        tooltip_ru="Количество заполненных лид-форм или зарегистрированных контактов",
        tooltip_uz="Yig'ilgan arizalar (lidlar) soni",
        tooltip_en="Number of leads generated from ad forms and conversion events",
        meta_action_type="lead",
        sample_value=42
    ),
    "cpl": MetricDefinition(
        key="cpl",
        category="conversions",
        is_additive=False,
        format_type="currency",
        ru_label="CPL (цена за лид)",
        uz_label="CPL (bitta lid narxi)",
        en_label="CPL (Cost per Lead)",
        tooltip_ru="Средняя стоимость привлечения одного лида (Расход / Лиды)",
        tooltip_uz="Bitta lid jalb qilish narxi",
        tooltip_en="Average cost for each lead generated",
        sample_value=3.45
    ),
    "messages": MetricDefinition(
        key="messages",
        category="messaging",
        is_additive=True,
        format_type="integer",
        ru_label="Сообщения (DM)",
        uz_label="Xabarlar (DM)",
        en_label="Messages (DM)",
        tooltip_ru="Количество начатых переписок в Messenger, Instagram Direct или WhatsApp",
        tooltip_uz="Boshlangan yozishmalar soni (Direct / WhatsApp)",
        tooltip_en="Number of messaging conversations started in Messenger, Instagram Direct, or WhatsApp",
        meta_action_type="onsite_conversion.messaging_conversation_started_7d",
        sample_value=32
    ),
    "cost_per_dm": MetricDefinition(
        key="cost_per_dm",
        category="messaging",
        is_additive=False,
        format_type="currency",
        ru_label="Стоимость DM",
        uz_label="DM narxi",
        en_label="Cost per DM",
        tooltip_ru="Средняя цена за одну начатую переписку (Расход / Сообщения)",
        tooltip_uz="Bitta yozishma boshlanishining o'rtacha narxi",
        tooltip_en="Average cost for each messaging conversation started",
        sample_value=4.54
    ),
    "calls": MetricDefinition(
        key="calls",
        category="calls",
        is_additive=True,
        format_type="integer",
        ru_label="Звонки",
        uz_label="Qo'ng'iroqlar",
        en_label="Calls",
        tooltip_ru="Количество звонков с рекламы 'Позвонить'",
        tooltip_uz="Reklamadagi 'Qo'ng'iroq qilish' orqali amalga oshirilgan qo'ng'iroqlar",
        tooltip_en="Number of phone calls initiated from call ads",
        meta_action_type="phone_call",
        sample_value=9
    ),
    "cost_per_call": MetricDefinition(
        key="cost_per_call",
        category="calls",
        is_additive=False,
        format_type="currency",
        ru_label="Стоимость звонка",
        uz_label="Qo'ng'iroq narxi",
        en_label="Cost per Call",
        tooltip_ru="Средняя стоимость одного совершенного звонка (Расход / Звонки)",
        tooltip_uz="Bitta qo'ng'iroqning o'rtacha narxi",
        tooltip_en="Average cost for each initiated phone call",
        sample_value=8.30
    ),
    "app_installs": MetricDefinition(
        key="app_installs",
        category="apps",
        is_additive=True,
        format_type="integer",
        ru_label="Установки приложения",
        uz_label="Ilova o'rnatishlar",
        en_label="App Installs",
        tooltip_ru="Количество установок мобильного приложения",
        tooltip_uz="Mobil ilovani yuklab o'rnatishlar soni",
        tooltip_en="Number of mobile app installs recorded",
        meta_action_type="mobile_app_install",
        sample_value=47
    ),
    "cost_per_install": MetricDefinition(
        key="cost_per_install",
        category="apps",
        is_additive=False,
        format_type="currency",
        ru_label="Стоимость установки",
        uz_label="O'rnatish narxi",
        en_label="Cost per Install",
        tooltip_ru="Средняя стоимость одной установки приложения (Расход / Установки)",
        tooltip_uz="Bitta ilova o'rnatilish narxi",
        tooltip_en="Average cost per app install",
        sample_value=3.09
    ),
    "video_views": MetricDefinition(
        key="video_views",
        category="video",
        is_additive=True,
        format_type="integer",
        ru_label="Просмотры видео (ThruPlays)",
        uz_label="Video ko'rishlar (ThruPlay)",
        en_label="Video Views (ThruPlays)",
        tooltip_ru="Количество воспроизведений видео до конца или не менее 15 секунд",
        tooltip_uz="Videoni oxirigacha yoki kamida 15 soniya ko'rishlar",
        tooltip_en="Number of times video played to completion or for at least 15 seconds",
        meta_action_type="video_thruplay_watched_actions",
        sample_value=3420
    ),
    "post_engagement": MetricDefinition(
        key="post_engagement",
        category="engagement",
        is_additive=True,
        format_type="integer",
        ru_label="Вовлеченность поста",
        uz_label="Post faolligi",
        en_label="Post Engagement",
        tooltip_ru="Общее количество всех действий с публикацией (лайки, комментарии, репосты)",
        tooltip_uz="Post bilan qilingan barcha amallar (layklar, izohlar, ulashishlar)",
        tooltip_en="Total number of actions taken on post (reactions, comments, shares)",
        meta_action_type="post_engagement",
        sample_value=764
    ),
    "roas": MetricDefinition(
        key="roas",
        category="conversions",
        is_additive=False,
        format_type="decimal",
        ru_label="ROAS (окупаемость)",
        uz_label="ROAS (qaytimlik)",
        en_label="ROAS (Return on Ad Spend)",
        tooltip_ru="Окупаемость расходов на рекламу (Ценность покупок / Расход)",
        tooltip_uz="Reklama xarajatlarining qaytishi (Xaridlar qiymati / Sarf)",
        tooltip_en="Return on ad spend (Purchase revenue / Ad spend)",
        sample_value=3.85
    )
}

# 4 Wizard Templates
TEMPLATES = {
    "daily_pulse": {
        "id": "daily_pulse",
        "is_recommended": True,
        "title_ru": "Ежедневный пульс",
        "title_uz": "Kunlik puls",
        "title_en": "Daily Pulse",
        "desc_ru": "Потрачено, Показы, Охват, Новые подписчики, CPM, CPP",
        "desc_uz": "Sarflangan, Ko'rsatishlar, Qamrov, Yangi obunachilar, CPM, CPP",
        "desc_en": "Spend, Impressions, Reach, New Followers, CPM, CPP",
        "metrics": ["spend", "impressions", "reach", "new_followers", "cpm", "cpp"]
    },
    "lead_generation": {
        "id": "lead_generation",
        "is_recommended": False,
        "title_ru": "Лидогенерация",
        "title_uz": "Lidlar jalb qilish",
        "title_en": "Lead Generation",
        "desc_ru": "Потрачено, Показы, Клики по ссылке, Лиды, CPL",
        "desc_uz": "Sarflangan, Ko'rsatishlar, Havola bosish, Lidlar, CPL",
        "desc_en": "Spend, Impressions, Link Clicks, Leads, CPL",
        "metrics": ["spend", "impressions", "link_clicks", "leads", "cpl"]
    },
    "direct_messages": {
        "id": "direct_messages",
        "is_recommended": False,
        "title_ru": "Личные сообщения",
        "title_uz": "Shaxsiy xabarlar",
        "title_en": "Direct Messages",
        "desc_ru": "Потрачено, Показы, Клики, Сообщения, Стоимость DM",
        "desc_uz": "Sarflangan, Ko'rsatishlar, Bosishlar, Xabarlar, DM narxi",
        "desc_en": "Spend, Impressions, Clicks, Messages, Cost per DM",
        "metrics": ["spend", "impressions", "clicks", "messages", "cost_per_dm"]
    },
    "brand_awareness": {
        "id": "brand_awareness",
        "is_recommended": False,
        "title_ru": "Узнаваемость",
        "title_uz": "Taniqlilik",
        "title_en": "Brand Awareness",
        "desc_ru": "Потрачено, Показы, Охват, CPM, CPP",
        "desc_uz": "Sarflangan, Ko'rsatishlar, Qamrov, CPM, CPP",
        "desc_en": "Spend, Impressions, Reach, CPM, CPP",
        "metrics": ["spend", "impressions", "reach", "cpm", "cpp"]
    }
}

# Optimization goal options for Campaign Filter in Step 2
OPTIMIZATION_GOALS = [
    {"key": "MESSAGES", "ru": "Сообщения / DM", "uz": "Xabarlar / DM", "en": "Messages / DM"},
    {"key": "LEAD_GENERATION", "ru": "Лиды", "uz": "Lidlar", "en": "Leads"},
    {"key": "CALLS", "ru": "Звонки", "uz": "Qo'ng'iroqlar", "en": "Calls"},
    {"key": "CONVERSIONS", "ru": "Конверсии / Продажи", "uz": "Konversiyalar / Savdo", "en": "Conversions / Sales"},
    {"key": "LINK_CLICKS", "ru": "Клики по ссылке и трафик", "uz": "Havola bosish va trafik", "en": "Link Clicks & Traffic"},
    {"key": "VIDEO_VIEWS", "ru": "Просмотры видео", "uz": "Video ko'rishlar", "en": "Video Views"},
    {"key": "POST_ENGAGEMENT", "ru": "Вовлечённость", "uz": "Faollik", "en": "Engagement"},
    {"key": "REACH", "ru": "Охват и узнаваемость", "uz": "Qamrov va taniqlilik", "en": "Reach & Awareness"},
    {"key": "APP_INSTALLS", "ru": "Установки приложений", "uz": "Ilova o'rnatishlar", "en": "App Installs"}
]

# Smart Metric Detection mapping (objective -> recommended metric keys)
OBJECTIVE_TO_METRICS: dict[str, list[str]] = {
    "MESSAGES": ["messages", "cost_per_dm"],
    "OUTCOME_MESSAGES": ["messages", "cost_per_dm"],
    "LEAD_GENERATION": ["leads", "cpl"],
    "OUTCOME_LEADS": ["leads", "cpl"],
    "CALLS": ["calls", "cost_per_call"],
    "CONVERSIONS": ["leads", "cpl", "roas"],
    "OUTCOME_SALES": ["roas"],
    "LINK_CLICKS": ["link_clicks", "ctr_link"],
    "OUTCOME_TRAFFIC": ["link_clicks", "ctr_link", "landing_page_views"],
    "VIDEO_VIEWS": ["video_views"],
    "POST_ENGAGEMENT": ["post_engagement"],
    "OUTCOME_ENGAGEMENT": ["post_engagement"],
    "REACH": ["reach", "cpm", "cpp"],
    "OUTCOME_AWARENESS": ["reach", "cpm", "cpp"],
    "APP_INSTALLS": ["app_installs", "cost_per_install"],
    "OUTCOME_APP_PROMOTION": ["app_installs", "cost_per_install"]
}

def get_default_labels(lang: str = "ru") -> dict[str, str]:
    labels = {}
    for key, definition in METRIC_DEFINITIONS.items():
        if lang == "uz":
            labels[key] = definition.uz_label
        elif lang == "en":
            labels[key] = definition.en_label
        else:
            labels[key] = definition.ru_label
    return labels

def format_metric_value(val: float | None, format_type: str, currency: str = "USD", lang: str = "ru", is_approximate: bool = False) -> str:
    if val is None:
        if lang == "uz":
            return "mavjud emas"
        elif lang == "en":
            return "N/A"
        return "н/д"
    prefix = "≈ " if is_approximate else ""
    if format_type == "currency":
        curr_symbol = "$" if currency == "USD" else f" {currency}"
        if currency == "USD":
            return f"{prefix}${val:,.2f}"
        return f"{prefix}{val:,.2f}{curr_symbol}"
    elif format_type == "percent":
        return f"{prefix}{val:.2f}%"
    elif format_type == "integer":
        return f"{prefix}{int(round(val)):,}".replace(",", " ")
    elif format_type == "decimal":
        return f"{prefix}{val:.2f}"
    return f"{prefix}{val}"

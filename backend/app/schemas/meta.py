
from pydantic import BaseModel, Field


class MetaTokenVerifyRequest(BaseModel):
    access_token: str = Field(..., min_length=10)

class MetaProfileResponse(BaseModel):
    meta_user_id: str | None = None
    meta_user_name: str | None = None
    meta_avatar_url: str | None = None
    is_valid: bool = True

class MetaAdAccountResponse(BaseModel):
    id: str
    account_id: str | None = None
    name: str
    currency: str = "USD"
    timezone_name: str = "UTC"
    account_status: int = 1
    business_name: str | None = None

class MetaCampaignResponse(BaseModel):
    id: str
    name: str
    objective: str
    status: str
    effective_status: str

class MetaMetricInfo(BaseModel):
    key: str
    category: str
    is_additive: bool
    format_type: str
    ru_label: str
    uz_label: str
    en_label: str
    tooltip_ru: str
    tooltip_uz: str
    tooltip_en: str
    is_limited: bool = False
    sample_value: float = 0.0

class MetaTemplateInfo(BaseModel):
    id: str
    is_recommended: bool
    title_ru: str
    title_uz: str
    title_en: str
    desc_ru: str
    desc_uz: str
    desc_en: str
    metrics: list[str]

class MetaMetadataResponse(BaseModel):
    metrics: list[MetaMetricInfo]
    templates: list[MetaTemplateInfo]
    optimization_goals: list[dict[str, str]]

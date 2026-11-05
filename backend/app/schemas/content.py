
# {
#   "source": { "platform": "naver_blog", "blog_id": "copper567", "log_no": "224443571088", "url": "https://blog.naver.com/copper567/224443571088" },
#   "title": "인디자인독학 실무자들은 이렇게 공부해요",
#   "text": "본문 텍스트…",
#   "images": [
#     { "asset_id": "5b8e…", "url": "/api/v1/assets/5b8e…", "width": 966, "height": 644, "alt": null }
#   ]
# }


from pydantic import BaseModel, HttpUrl, Field


class ContentExtractRequest(BaseModel):
    url: HttpUrl


class SourceInfo(BaseModel):
    platform: str
    blog_id: str
    log_no: str
    url: HttpUrl


class ImageAsset(BaseModel):
    asset_id: str
    url: str
    width: int
    height: int
    alt: str | None = None


class ContentExtractResponse(BaseModel):
    source: SourceInfo
    title: str
    text: str
    images: list[ImageAsset] = Field(default_factory=list)

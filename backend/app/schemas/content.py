
# {
#   "source": { "platform": "naver_blog", "blog_id": "copper567", "log_no": "224443571088", "url": "https://blog.naver.com/copper567/224443571088" },
#   "title": "인디자인독학 실무자들은 이렇게 공부해요",
#   "text": "본문 첫 문단\n[이미지 1]\n다음 문단…",
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
    text: str = Field(
        description='본문. 문단은 줄바꿈, 이미지 자리는 "[이미지 N]" 한 줄 (N은 images 순서, 1부터)',
    )
    images: list[ImageAsset] = Field(default_factory=list)

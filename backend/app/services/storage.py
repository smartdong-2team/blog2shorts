
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4
from urllib.parse import urlparse
import ipaddress
import socket

import requests
from PIL import Image, UnidentifiedImageError


# backend/storage/images/
STORAGE_DIR = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "images"
)

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

ALLOWED_HOSTS = {
    "mblogthumb-phinf.pstatic.net",
    "blogthumb-phinf.pstatic.net",
    "postfiles.pstatic.net",
    "storep-phinf.pstatic.net",
}

ALLOWED_FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}


@dataclass
class StoredAsset:
    asset_id: UUID
    path: Path
    media_type: str
    width: int
    height: int

    @property
    def url(self) -> str:
        return f"/api/v1/assets/{self.asset_id}"


class ImageStorageError(Exception):
    pass


def validate_image_url(url: str) -> None:
    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise ImageStorageError("허용되지 않은 이미지 URL입니다.")

    # 내부 네트워크 주소로의 접근을 방지하기 위한 기본 검사
    try:
        addresses = socket.getaddrinfo(
            parsed.hostname,
            443,
            type=socket.SOCK_STREAM,
        )

        if not addresses or any(
            not ipaddress.ip_address(address[4][0]).is_global
            for address in addresses
        ):
            raise ImageStorageError("접근할 수 없는 이미지 서버입니다.")

    except socket.gaierror as exc:
        raise ImageStorageError("이미지 서버 주소를 확인할 수 없습니다.") from exc


def save_image(url: str) -> StoredAsset:
    validate_image_url(url)

    try:
        with requests.get(
            url,
            timeout=(5, 15),
            stream=True,
            allow_redirects=False,
        ) as response:
            if response.is_redirect:
                raise ImageStorageError("이미지 리다이렉트를 허용하지 않습니다.")

            response.raise_for_status()

            data = bytearray()

            for chunk in response.iter_content(chunk_size=8192):
                data.extend(chunk)

                if len(data) > MAX_IMAGE_SIZE:
                    raise ImageStorageError("이미지 용량이 10MB를 초과했습니다.")

        image_bytes = bytes(data)

        try:
            with Image.open(BytesIO(image_bytes)) as image:
                image_format = image.format

                if image_format not in ALLOWED_FORMATS:
                    raise ImageStorageError("지원하지 않는 이미지 형식입니다.")

                image.verify()

            with Image.open(BytesIO(image_bytes)) as image:
                width, height = image.size

                if width <= 0 or height <= 0:
                    raise ImageStorageError("이미지 크기가 올바르지 않습니다.")

                if width * height > 40_000_000:
                    raise ImageStorageError("이미지 해상도가 너무 큽니다.")

        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ImageStorageError("올바른 이미지 파일이 아닙니다.") from exc

        extension, media_type = ALLOWED_FORMATS[image_format]

        asset_id = uuid4()

        STORAGE_DIR.mkdir(parents=True, exist_ok=True)

        file_path = STORAGE_DIR / f"{asset_id}.{extension}"
        file_path.write_bytes(image_bytes)

        return StoredAsset(
            asset_id=asset_id,
            path=file_path,
            media_type=media_type,
            width=width,
            height=height,
        )

    except requests.RequestException as exc:
        raise ImageStorageError("이미지 다운로드에 실패했습니다.") from exc


def get_asset(asset_id: UUID) -> StoredAsset | None:
    for extension, media_type in ALLOWED_FORMATS.values():
        file_path = STORAGE_DIR / f"{asset_id}.{extension}"

        if file_path.is_file():
            return StoredAsset(
                asset_id=asset_id,
                path=file_path,
                media_type=media_type,
                width=0,
                height=0,
            )

    return None

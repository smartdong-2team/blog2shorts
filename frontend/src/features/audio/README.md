# features/audio — 음성과 음악 (4단계)

- `VoiceMusicPicker.tsx`: 목소리·배경음악·음악 크기 선택. 검토 모드에서는 장면 확인 화면에, 자동 모드에서는 기본값(`DEFAULT_AUDIO`)으로 진행한 뒤 완성 후 바꿔 다시 만들 수 있다.
- `options.ts`: 선택지 목록과 기본값. 실제 TTS 목소리 ID·음악 파일이 정해지면 값만 바꾼다.
- 렌더 요청(`POST /api/v1/videos`)의 `voice` 필드와 추가될 음악 필드에 대응한다 (docs/api-design.md 5절).

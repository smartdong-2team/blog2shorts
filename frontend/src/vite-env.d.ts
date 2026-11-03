// Vite가 노출하는 사용자 정의 환경변수 타입 (VITE_ 접두사만 클라이언트에 노출됨)
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

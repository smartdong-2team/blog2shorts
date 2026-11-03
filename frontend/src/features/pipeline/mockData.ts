import type { Content, Scene, ScriptSummary } from './types'

// 백엔드 연결 전 화면 확인용 예시 글. 이미지는 public/mock/ 의 SVG
export const SAMPLE_URL = 'https://blog.naver.com/copper567/224443571088'

export const SAMPLE_CONTENT: Content = {
  title: '인디자인독학 실무자들은 이렇게 공부해요',
  source_url: SAMPLE_URL,
  images: Array.from({ length: 6 }, (_, i) => ({
    asset_id: `mock-${i + 1}`,
    url: `/mock/img-${i + 1}.svg`,
    alt: `예시 이미지 ${i + 1}`,
  })),
  text: [
    '편집 디자인을 처음 시작하는 분들이 가장 많이 묻는 게 "인디자인은 어디서부터 공부해야 하나요?"예요.',
    '[이미지 1]',
    '실무자들은 기능을 하나씩 외우기보다, 실제로 만들 결과물 하나를 정해 놓고 거꾸로 필요한 기능을 익힙니다. 명함, 포스터, 8쪽짜리 소책자처럼 작고 끝이 보이는 작업부터요.',
    '[이미지 2]',
    '첫 주에는 문서 설정과 마스터 페이지, 단락 스타일만 제대로 잡아도 충분합니다. 이 세 가지가 잡히면 페이지가 늘어나도 수정이 쉬워져요.',
    '[이미지 3]',
    '레이아웃 그리드는 감으로 맞추지 말고 숫자로 정하세요. 여백과 단 간격을 먼저 정해 두면 이미지와 글이 자연스럽게 자리를 찾습니다.',
    '[이미지 4]',
    '둘째 주부터는 잘 만든 책 한 권을 골라 펼침면을 그대로 따라 만들어 보세요. 왜 이 위치에 제목이 있는지, 행간은 얼마인지 재 보면서 따라 하면 눈이 빠르게 늡니다.',
    '[이미지 5]',
    '자주 쓰는 단축키는 모니터 옆에 붙여 두고, 같은 작업을 세 번 반복하면 스타일이나 스크립트로 바꿀 수 없는지 찾아보세요.',
    '[이미지 6]',
    '마지막으로, 완성한 작업은 꼭 PDF로 내보내 포트폴리오 폴더에 모아 두세요. 한 달 뒤 처음 만든 것과 비교해 보면 얼마나 늘었는지 바로 보입니다.',
  ].join('\n'),
}

export const SAMPLE_SUMMARY: ScriptSummary = {
  topic: '실무자식 인디자인 독학법',
  key_points: [
    '만들 결과물 하나를 정하고 필요한 기능만 거꾸로 익힌다',
    '첫 주엔 문서 설정·마스터 페이지·단락 스타일, 그리드는 숫자로',
    '잘 만든 책을 따라 만들고, 완성작은 PDF로 모아 비교한다',
  ],
}

export const SAMPLE_SCENES: Omit<Scene, 'id'>[] = [
  {
    role: 'hook',
    caption: '인디자인, 뭐부터 하지?',
    narration: '인디자인 독학, 기능부터 외우고 있다면 순서가 틀렸어요.',
    asset_id: 'mock-1',
    motion: 'zoom_in',
  },
  {
    role: 'body',
    caption: '결과물 하나부터',
    narration: '실무자들은 명함이나 포스터처럼 작은 결과물 하나를 정하고, 필요한 기능만 거꾸로 익힙니다.',
    asset_id: 'mock-2',
    motion: 'pan_left',
  },
  {
    role: 'body',
    caption: '첫 주는 세 가지만',
    narration: '첫 주에는 문서 설정, 마스터 페이지, 단락 스타일. 이 세 가지만 잡아도 수정이 쉬워져요.',
    asset_id: 'mock-3',
    motion: 'zoom_out',
  },
  {
    role: 'body',
    caption: '좋은 책을 따라 만들기',
    narration: '둘째 주부터는 잘 만든 책 한 권을 골라 펼침면을 그대로 따라 만들어 보세요.',
    asset_id: 'mock-4',
    motion: 'pan_right',
  },
  {
    role: 'cta',
    caption: 'PDF로 모아 비교하기',
    narration: '완성한 작업은 PDF로 모아 두고 한 달 뒤 비교해 보세요. 더 많은 독학 팁은 블로그에서 확인하세요.',
    asset_id: 'mock-6',
    motion: 'zoom_in',
  },
]

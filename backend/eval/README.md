# 대본 프롬프트 평가

프롬프트(`app/services/script_prompts.py`)를 고쳤을 때 대본이 실제로 나아졌는지 숫자로 비교하는 도구입니다.
같은 블로그 글 묶음(`posts.txt`)으로 대본을 여러 번 만들고 아래 두 가지를 모읍니다. 버전끼리는 맞대어 비교합니다(`--pairwise`).

- **규칙 지표:** 검증 통과율, 전체 글자 수, 350자 초과 횟수, 첫 문장 길이, 35자 넘는 문장 비율, 빈말 개수, hook_text 길이
- **LLM 채점(1~5점):** 항목마다 문제를 먼저 적게 하고, 문제 개수로 점수를 매깁니다. 어디가 약한지 볼 때 씁니다.
  - `hook_promise`: 첫 문장이 구체적으로 약속하는가, 약속한 걸 실제로 주는가
  - `new_info_per_scene`: 장면마다 원문의 구체적인 정보가 있는가
  - `faithfulness`: 원문에 없는 사실이 없는가
  - `spoken_naturalness`: 귀로 듣기 편한가
  - `cta`: 마지막 장면이 구체적 행동을 유도하는가
  - `hook_text`: 상단 제목이 짧고 구체적인가

## 실행

`backend` 폴더에서 실행합니다. `.env`의 `OPENAI_API_KEY`를 씁니다.

```bash
uv run python scripts/eval_script.py --label baseline
```

- 기본값: 글 17개 × 3번, 대본 모델은 `.env` 설정(`gpt-4.1-mini`), 채점 모델은 `gpt-4.1`
- 글은 처음 한 번 받아 `eval/cache/`에 저장하고, 결과는 `eval/results/<시각>-<이름>/`에 남깁니다. 둘 다 git에 올리지 않습니다.
- 비용: 기본 설정 한 번에 1~2달러 정도입니다. 빨리 볼 때는 `--limit 3 --runs 1`, 채점을 빼려면 `--no-judge`

## 프롬프트 비교

1. 지금 프롬프트로 한 번 돌려 둡니다(`--label baseline`).
2. 바꿀 프롬프트를 파일로 만들어 돌립니다. `results/<폴더>/instructions.txt`를 복사해 고치면 편합니다.

   ```bash
   uv run python scripts/eval_script.py --instructions my_prompt.txt --label shorter-rules
   ```

3. 두 결과를 표로 봅니다.

   ```bash
   uv run python scripts/eval_script.py --compare eval/results/<baseline 폴더> eval/results/<새 폴더>
   ```

4. 같은 글로 만든 대본끼리 맞대어 어느 쪽이 나은지 봅니다. **버전 차이는 이 결과로 판단하세요.**

   ```bash
   uv run python scripts/eval_script.py --pairwise eval/results/<baseline 폴더> eval/results/<새 폴더>
   ```

   - 같은 글의 1번째 대본끼리, 2번째 대본끼리 짝지어 `gpt-4.1`에 고르게 합니다. 검증에 실패한 대본은 뺍니다.
   - 순서를 바꿔 두 번 묻고, 두 번 다 이긴 경우만 승으로 셉니다(나머지는 무).
   - 1~5점 평균은 버전 차이가 작으면 흔들림에 묻힙니다. 2026-11-14 기준 v3와 v6는 평균이 0.07점 차이였지만,
     맞대 보면 v6가 26승 2패였습니다.
   - 대본이 길수록 정보가 많아 유리할 수 있으니 `--compare`의 전체 글자 수도 같이 보세요.

채점 기준(`JUDGE_INSTRUCTIONS`)을 바꿨다면 예전 결과와 점수를 바로 비교할 수 없습니다.
`--rejudge eval/results/<폴더>`로 예전 대본을 새 기준으로 다시 채점한 뒤 비교하세요.

## 읽을 때 주의

- **이미지는 빼고 글만 보냅니다.** 이미지 고르기는 평가하지 않습니다.
- **한 번만 생성합니다.** 앱은 검증에 실패하면 한 번 더 시도하므로, 앱에서 보이는 실패율은 여기 통과율보다 낮습니다.
- **채점은 흔들립니다.** 같은 대본 51개를 두 번 채점해 보니(2026-11-13)
  - 대본 하나의 항목 점수는 평균 0.5점씩 달랐고 같은 점수는 60%였습니다.
  - 항목별 평균은 최대 0.2점, 전체 평균은 0.03점 달랐습니다.
  - 그래서 항목별로 0.2점 안팎의 차이는 차이로 보지 말고, 실패 이유와 `runs.jsonl`의 `problems`를 같이 읽으세요.
- `posts.txt`를 바꾸면 이전 결과와 비교하지 마세요.

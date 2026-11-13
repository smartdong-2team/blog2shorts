"""대본 프롬프트 평가.

같은 블로그 글 묶음(eval/posts.txt)으로 대본을 여러 번 만들고,
검증 통과율·글자 수 같은 규칙 지표와 LLM 채점 점수를 모아 비교한다.
사용법은 eval/README.md 참고.
"""

import argparse
import asyncio
import json
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.openai import get_openai_client  # noqa: E402
from app.schemas.script import (  # noqa: E402
    ScriptAIOutput,
    ScriptGenerateRequest,
    ScriptOutputFormat,
)
from app.services.content_extractor import IMAGE_MARKER, extract_content  # noqa: E402
from app.services.script_generate import (  # noqa: E402
    build_user_content,
    normalize_ai_output,
)
from app.services.script_prompts import SCRIPT_INSTRUCTIONS  # noqa: E402

EVAL_DIR = BACKEND_DIR / "eval"
CACHE_DIR = EVAL_DIR / "cache"
RESULTS_DIR = EVAL_DIR / "results"

# 프롬프트에서 쓰지 말라고 한 빈말. 나오면 셈한다
FILLER_WORDS = [
    "차근차근",
    "체계적",
    "큰 도움이 돼요",
    "중요해요",
    "응원할게요",
    "꿀팁",
    "효율적인",
    "알려드려요",
    "알려드릴게요",
]
LONG_SENTENCE_CHARS = 35
CHARS_PER_SECOND = 5  # script_generate.CHARS_PER_SECOND와 같은 값


# --------------------------------------------------
# 1. 글 불러오기 (한 번 받은 글은 cache에 저장)
# --------------------------------------------------
def read_post_urls(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def load_post(url: str, refresh: bool) -> dict:
    """블로그 글을 받아 제목·본문을 돌려준다. 이미지 자리 표시는 앱처럼 뺀다."""

    key = url.rstrip("/").split("/")[-1]
    cache_file = CACHE_DIR / f"{key}.json"

    if cache_file.exists() and not refresh:
        return json.loads(cache_file.read_text(encoding="utf-8"))

    content = extract_content(url)
    text = IMAGE_MARKER.sub("", content.text)
    text = "\n".join(line for line in text.split("\n") if line.strip())
    post = {"id": key, "url": content.url, "title": content.title, "text": text[:20_000]}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
    return post


# --------------------------------------------------
# 2. 대본 만들기 (앱과 같은 요청을 한 번만 보낸다. 앱은 실패하면 한 번 더 시도한다)
# --------------------------------------------------
def validation_errors(error: Exception) -> list[str]:
    if isinstance(error, ValidationError):
        return [
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}".lstrip(": ")
            for item in error.errors()
        ]
    return [str(error)]


async def generate_once(client, post: dict, instructions: str, model: str) -> dict:
    request = ScriptGenerateRequest(title=post["title"], text=post["text"], images=[])
    started = time.monotonic()
    response = await client.responses.parse(
        model=model,
        instructions=instructions,
        input=[{"role": "user", "content": await build_user_content(request)}],
        text_format=ScriptOutputFormat,
    )
    seconds = round(time.monotonic() - started, 1)

    if response.output_parsed is None:
        return {"output": None, "valid": False, "errors": ["AI 결과 없음"], "seconds": seconds}

    output = normalize_ai_output(response.output_parsed)
    try:
        ScriptAIOutput.model_validate(output)
        errors = []
    except (ValidationError, ValueError) as error:
        errors = validation_errors(error)

    return {"output": output, "valid": not errors, "errors": errors, "seconds": seconds}


# --------------------------------------------------
# 3. 규칙 지표
# --------------------------------------------------
def sentences_of(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def rule_metrics(output: dict) -> dict:
    scenes = output["scenes"]
    narrations = [scene["narration"] for scene in scenes]
    joined = " ".join(narrations)
    sentences = [s for text in narrations for s in sentences_of(text)]
    hook_text = output.get("hook_text", "")
    first_sentence = sentences_of(narrations[0])[0] if narrations and narrations[0] else ""

    return {
        "scene_count": len(scenes),
        "total_chars": sum(len(text) for text in narrations),
        "est_sec": round(sum(len(text) for text in narrations) / CHARS_PER_SECOND),
        "max_scene_chars": max((len(text) for text in narrations), default=0),
        "first_sentence_chars": len(first_sentence),
        "long_sentences": sum(len(s) > LONG_SENTENCE_CHARS for s in sentences),
        "sentence_count": len(sentences),
        "filler_hits": [word for word in FILLER_WORDS if word in joined or word in hook_text],
        "formal_endings": len(re.findall(r"니다[.!?]?", joined)),
        "hook_text_chars": len(hook_text.replace("\n", "")),
        "hook_text_lines": len([line for line in hook_text.split("\n") if line.strip()]),
    }


# --------------------------------------------------
# 4. LLM 채점
# --------------------------------------------------
class Score(BaseModel):
    # 문제를 먼저 적게 해야 점수가 후해지지 않는다
    problems: list[str]
    score: int


class Judgement(BaseModel):
    hook_promise: Score
    new_info_per_scene: Score
    faithfulness: Score
    spoken_naturalness: Score
    cta: Score
    hook_text: Score


CRITERIA = list(Judgement.model_fields)

JUDGE_INSTRUCTIONS = """너는 교육 콘텐츠 숏폼 대본을 채점하는 편집자야.
원문 블로그 글과, 그 글로 만든 45초 안팎의 쇼츠 대본을 보고 항목마다 problems와 score를 줘.

먼저 problems에 그 항목의 구체적인 문제를 대본 문구를 인용해 하나씩 적어. 사소해도 적어.
score는 problems 개수로 정해: 0개 5점, 1개 4점, 2개 3점, 3개 2점, 4개 이상 또는 치명적 문제 1점.
잘 쓴 점은 적지 마. 칭찬은 점수에 반영하지 않아.

- hook_promise: 첫 장면 첫 문장이 원문의 구체적 정보(숫자, 항목 수, 과목명, 흔한 실수, 대상)로
  이 영상에서 얻을 것을 약속하는가.
  문제 예: 정의·인사로 시작, '알려드릴게요'식 예고만 있음, 질문만 하고 무엇을 얻는지 없음,
  약속한 내용(예: 합격률 숫자)을 body에서 실제로 주지 않음(치명적).
- new_info_per_scene: body 장면마다 원문에서 온 구체적 정보가 하나씩 있는가.
  문제 예: 앞 장면 되풀이, 어느 시험에나 맞는 일반론('기출을 반복하세요', '계획을 세우세요'), 원문에 있는 숫자·항목을 두고 뭉뚱그림.
- faithfulness: 대본의 사실·숫자·주장이 모두 원문에 있는가. 원문에 없는 숫자·주장·상품명은 하나라도 치명적.
  원문 내용을 뺀 것, 홍보 위치, 말투는 여기서 따지지 마(다른 항목에서 본다).
  원문에 강의·상품이 있으면 cta에서 그 이름을 말하는 건 문제가 아니야.
- spoken_naturalness: TTS로 한 번 듣고 이해되는가.
  문제 예: 35자 넘는 문장, 동사 없는 나열, 어색한 어미, 빈말('체계적', '중요해요', '효과적이에요', '알려드릴게요', '응원할게요').
- cta: 마지막 장면이 한두 문장으로 구체적 행동을 유도하는가.
  문제 예: 인사·응원으로 끝남, 빈말 수식('체계적인 강의'), body에서 상품 홍보.
- hook_text: 영상 위에 고정되는 제목. 20자 안팎 두 줄, 첫 줄 주제 키워드 + 둘째 줄 얻는 것(숫자나 구체적 단어).
  문제 예: 상투어('공개', '꿀팁', '총정리'), 질문형, 첫 문장 반복, 얻는 것이 막연함.
"""


def format_script(output: dict) -> str:
    lines = [f"[hook_text] {output.get('hook_text', '')!r}"]
    for scene in output["scenes"]:
        lines.append(f"[{scene['order']} {scene['role']}] {scene['narration']}")
    return "\n".join(lines)


async def judge(client, post: dict, output: dict, model: str) -> dict:
    response = await client.responses.parse(
        model=model,
        instructions=JUDGE_INSTRUCTIONS,
        input=[
            {
                "role": "user",
                "content": (
                    f"# 원문 제목\n{post['title']}\n\n# 원문\n{post['text']}\n\n"
                    f"# 대본\n{format_script(output)}"
                ),
            }
        ],
        text_format=Judgement,
        temperature=0,
    )
    parsed = response.output_parsed
    if parsed is None:
        return {}
    return {
        name: {"score": max(1, min(5, getattr(parsed, name).score)), "problems": getattr(parsed, name).problems}
        for name in CRITERIA
    }


# --------------------------------------------------
# 5. 실행
# --------------------------------------------------
async def run_one(client, semaphore, post, run_index, args, instructions) -> dict:
    async with semaphore:
        record = {"post": post["id"], "title": post["title"], "run": run_index}
        try:
            record.update(await generate_once(client, post, instructions, args.model))
        except Exception as error:  # 네트워크·API 오류도 결과에 남기고 계속한다
            record.update({"output": None, "valid": False, "errors": [f"{type(error).__name__}: {error}"]})
            return record

        if record["output"]:
            record["metrics"] = rule_metrics(record["output"])
            if not args.no_judge:
                try:
                    record["judge"] = await judge(client, post, record["output"], args.judge_model)
                except Exception as error:
                    record["judge_error"] = f"{type(error).__name__}: {error}"

        mark = "통과" if record["valid"] else "실패"
        print(f"  {post['id']} #{run_index + 1} {mark} {record.get('metrics', {}).get('total_chars', '-')}자", flush=True)
        return record


def mean(values) -> float | None:
    values = [v for v in values if v is not None]
    return round(statistics.mean(values), 2) if values else None


def summarize(records: list[dict]) -> dict:
    with_output = [r for r in records if r.get("metrics")]
    metric = lambda name: mean(r["metrics"][name] for r in with_output)  # noqa: E731
    judged = [r for r in records if r.get("judge")]

    errors: dict[str, int] = {}
    for record in records:
        for error in record.get("errors", []):
            # 실제 값이 들어간 메시지는 규칙 이름만 남겨 묶는다
            key = re.sub(r"\d+", "N", error)[:80]
            errors[key] = errors.get(key, 0) + 1

    return {
        "runs": len(records),
        "pass_rate": round(sum(r["valid"] for r in records) / len(records), 3) if records else None,
        "total_chars": metric("total_chars"),
        "over_350": sum(r["metrics"]["total_chars"] > 350 for r in with_output),
        "scene_count": metric("scene_count"),
        "first_sentence_chars": metric("first_sentence_chars"),
        "long_sentence_ratio": mean(
            r["metrics"]["long_sentences"] / r["metrics"]["sentence_count"]
            for r in with_output
            if r["metrics"]["sentence_count"]
        ),
        "filler_per_run": mean(len(r["metrics"]["filler_hits"]) for r in with_output),
        "hook_text_chars": metric("hook_text_chars"),
        "judge": {name: mean(r["judge"][name]["score"] for r in judged) for name in CRITERIA} if judged else {},
        "judge_avg": mean(mean(r["judge"][name]["score"] for name in CRITERIA) for r in judged) if judged else None,
        "errors": dict(sorted(errors.items(), key=lambda item: -item[1])),
    }


SUMMARY_ROWS = [
    ("검증 통과율", "pass_rate"),
    ("전체 글자 수 평균", "total_chars"),
    ("350자 초과 횟수", "over_350"),
    ("장면 수 평균", "scene_count"),
    ("첫 문장 글자 수", "first_sentence_chars"),
    (f"{LONG_SENTENCE_CHARS}자 넘는 문장 비율", "long_sentence_ratio"),
    ("빈말 개수/회", "filler_per_run"),
    ("hook_text 글자 수", "hook_text_chars"),
    ("채점 평균 (1~5)", "judge_avg"),
]


def summary_markdown(columns: dict[str, dict]) -> str:
    names = list(columns)
    lines = ["| 지표 | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for label, key in SUMMARY_ROWS:
        lines.append(f"| {label} | " + " | ".join(str(columns[n].get(key)) for n in names) + " |")
    for criterion in CRITERIA:
        lines.append(
            f"| 채점: {criterion} | " + " | ".join(str(columns[n]["judge"].get(criterion)) for n in names) + " |"
        )

    for name in names:
        if columns[name]["errors"]:
            lines.append(f"\n**{name} 검증 실패 이유**")
            lines += [f"- {count}회: `{message}`" for message, count in columns[name]["errors"].items()]
    return "\n".join(lines)


def load_records(result_dir: Path) -> list[dict]:
    path = result_dir / "runs.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


async def run(args) -> None:
    instructions = (
        Path(args.instructions).read_text(encoding="utf-8") if args.instructions else SCRIPT_INSTRUCTIONS
    )
    urls = read_post_urls(Path(args.posts))[: args.limit or None]

    print(f"글 {len(urls)}개 불러오는 중...")
    posts = []
    for url in urls:
        try:
            posts.append(await asyncio.to_thread(load_post, url, args.refresh))
        except Exception as error:
            print(f"  건너뜀 {url}: {error}")

    label = args.label or ("custom" if args.instructions else "current")
    out_dir = RESULTS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{label}"
    out_dir.mkdir(parents=True)
    (out_dir / "instructions.txt").write_text(instructions, encoding="utf-8")

    print(f"대본 {len(posts) * args.runs}개 생성 (모델 {args.model}, 채점 {'끔' if args.no_judge else args.judge_model})")
    client = get_openai_client()
    semaphore = asyncio.Semaphore(args.concurrency)
    try:
        records = await asyncio.gather(
            *(run_one(client, semaphore, post, i, args, instructions) for post in posts for i in range(args.runs))
        )
    finally:
        await client.close()

    with (out_dir / "runs.jsonl").open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary = summarize(records)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = summary_markdown({label: summary})
    (out_dir / "summary.md").write_text(markdown + "\n", encoding="utf-8")

    print("\n" + markdown)
    print(f"\n결과: {out_dir}")


async def rejudge(args) -> None:
    """채점 기준을 바꿨을 때, 대본은 그대로 두고 채점만 다시 한다."""

    source = Path(args.rejudge)
    records = load_records(source)
    posts = {
        record["post"]: json.loads((CACHE_DIR / f"{record['post']}.json").read_text(encoding="utf-8"))
        for record in records
    }

    client = get_openai_client()
    semaphore = asyncio.Semaphore(args.concurrency)

    async def one(record: dict) -> dict:
        if not record.get("output"):
            return record
        async with semaphore:
            try:
                record["judge"] = await judge(client, posts[record["post"]], record["output"], args.judge_model)
                record.pop("judge_error", None)
            except Exception as error:
                record["judge_error"] = f"{type(error).__name__}: {error}"
        return record

    try:
        records = await asyncio.gather(*(one(record) for record in records))
    finally:
        await client.close()

    out_dir = source.with_name(f"{source.name}-rejudge")
    out_dir.mkdir(exist_ok=True)
    with (out_dir / "runs.jsonl").open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(summary_markdown({out_dir.name: summarize(records)}))
    print(f"\n결과: {out_dir}")


def compare(dirs: list[str]) -> None:
    columns = {Path(d).name: summarize(load_records(Path(d))) for d in dirs}
    print(summary_markdown(columns))


def main() -> None:
    parser = argparse.ArgumentParser(description="대본 프롬프트 평가")
    parser.add_argument("--posts", default=str(EVAL_DIR / "posts.txt"), help="글 주소 목록 파일")
    parser.add_argument("--instructions", help="비교할 프롬프트 파일. 없으면 지금 프롬프트")
    parser.add_argument("--label", help="결과 폴더 이름에 붙일 이름")
    parser.add_argument("--runs", type=int, default=3, help="글 하나당 생성 횟수")
    parser.add_argument("--limit", type=int, default=0, help="앞에서부터 글 N개만")
    parser.add_argument("--model", default=get_settings().openai_script_model, help="대본 모델")
    parser.add_argument("--judge-model", default="gpt-4.1", help="채점 모델")
    parser.add_argument("--no-judge", action="store_true", help="LLM 채점 생략 (규칙 지표만)")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--refresh", action="store_true", help="저장해 둔 글을 다시 받기")
    parser.add_argument("--compare", nargs="+", metavar="RESULT_DIR", help="결과 폴더 여러 개를 표로 비교")
    parser.add_argument("--rejudge", metavar="RESULT_DIR", help="이 결과 폴더의 대본을 지금 채점 기준으로 다시 채점")
    args = parser.parse_args()

    if args.compare:
        compare(args.compare)
    elif args.rejudge:
        asyncio.run(rejudge(args))
    else:
        asyncio.run(run(args))


if __name__ == "__main__":
    main()

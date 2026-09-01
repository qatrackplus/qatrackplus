from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

MAX_DEP_FINDINGS = 30
MAX_PATTERN_FINDINGS = 50
MAX_AI_STYLE_FINDINGS = 25
MAX_AI_DOC_FINDINGS = 25
MAX_SAMPLE_FILES = 16
MAX_DOC_FILES = 16

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / 'pyproject.toml'
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

DESIRED_LABELS = ['maintenance', 'technical debt', 'documentation', 'ai']

PATTERN_RULES = [
    (re.compile(r'^\s*print\('), 'low', 'Use structured logging for persistent diagnostics instead of print statements.'),
    (re.compile(r'^\s*except\s*:\s*$'), 'high', 'Avoid bare except; catch explicit exception types.'),
    (re.compile(r'logger\.warn\('), 'medium', 'Use logger.warning(...) instead of deprecated logger.warn(...).'),
    (re.compile(r'%\s*[a-zA-Z_][a-zA-Z0-9_]*\s*$'), 'low', 'Prefer f-strings or str.format for readability.'),
    (re.compile(r'django\.conf\.urls\s+import\s+url'), 'high', 'Replace deprecated django.conf.urls.url usage.'),
    (re.compile(r'^\s*from\s+django\.utils\s+import\s+six'), 'high', 'Remove django.utils.six usage; migrate to Python-native equivalents.'),
    (re.compile(r'^\s*assert\s+'), 'medium', 'Avoid assert statements in runtime paths; raise explicit exceptions instead.'),
]


@dataclass
class Finding:
    path: str
    line: int
    severity: str
    confidence: str
    concern: str
    excerpt: str
    recommendation: str


def http_json(method: str, url: str, token: str, payload: dict | None = None) -> dict | list:
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(url=url, method=method, data=data)
    request.add_header('Authorization', 'Bearer ' + token)
    request.add_header('Accept', 'application/vnd.github+json')
    request.add_header('Content-Type', 'application/json')
    request.add_header('User-Agent', 'qatrackplus-annual-health-review')
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode('utf-8'))


def github_api(path: str) -> str:
    base = os.environ.get('GITHUB_API_URL', 'https://api.github.com').rstrip('/')
    return f'{base}{path}'


def load_pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding='utf-8'))


def normalize_package_name(spec: str) -> str:
    return re.split(r'[<>=!~;\s\[]', spec.strip(), maxsplit=1)[0].strip()


def extract_dependencies(pyproject: dict) -> list[str]:
    deps: list[str] = []
    project = pyproject.get('project', {})
    for dep in project.get('dependencies', []):
        deps.append(normalize_package_name(dep))
    for key in ('postgres', 'mysql', 'mssql', 'docker'):
        for dep in project.get('optional-dependencies', {}).get(key, []):
            deps.append(normalize_package_name(dep))
    deduped = sorted({d for d in deps if d and d.lower() != 'python'})
    return deduped


def get_pypi_info(package: str) -> dict | None:
    url = f'https://pypi.org/pypi/{urllib.parse.quote(package)}/json'
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as err:
        logging.warning('Failed to fetch PyPI metadata for %s: %s', package, err)
        return None
    except json.JSONDecodeError as err:
        logging.warning('Invalid JSON from PyPI for %s: %s', package, err)
        return None


def dependency_findings(packages: list[str]) -> list[dict]:
    findings: list[dict] = []
    now = dt.datetime.now(dt.UTC)
    for package in packages:
        pypi = get_pypi_info(package)
        if not pypi:
            findings.append(
                {
                    'package': package,
                    'severity': 'medium',
                    'signals': ['Unable to retrieve package metadata from PyPI during review.'],
                }
            )
            continue

        info = pypi.get('info', {})
        classifiers = info.get('classifiers', []) or []
        releases = pypi.get('releases', {}) or {}
        latest_upload: dt.datetime | None = None
        for release_files in releases.values():
            for item in release_files:
                upload_time = item.get('upload_time_iso_8601') or item.get('upload_time')
                if not upload_time:
                    continue
                stamp = upload_time.replace('Z', '+00:00')
                try:
                    parsed = dt.datetime.fromisoformat(stamp)
                except ValueError:
                    continue
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=dt.UTC)
                if latest_upload is None or parsed > latest_upload:
                    latest_upload = parsed

        signals: list[str] = []
        if latest_upload is None:
            signals.append('No release upload timestamps found in metadata.')
        else:
            days_since_release = (now - latest_upload).days
            if days_since_release > 730:
                signals.append(f'No releases in approximately {days_since_release} days.')

        py_classifiers = [c for c in classifiers if c.startswith('Programming Language :: Python ::')]
        has_312 = any(c.endswith('3.12') for c in py_classifiers)
        has_313 = any(c.endswith('3.13') for c in py_classifiers)
        if not has_312 and not has_313:
            signals.append('No Python 3.12/3.13 classifier support declared.')

        if info.get('yanked'):
            signals.append('Package metadata indicates yanked status.')

        if signals:
            severity = 'high' if any('No releases' in s for s in signals) else 'medium'
            findings.append({'package': package, 'severity': severity, 'signals': signals})

    findings.sort(key=lambda x: {'high': 0, 'medium': 1, 'low': 2}.get(x['severity'], 3))
    return findings[:MAX_DEP_FINDINGS]


def python_files() -> list[Path]:
    files: list[Path] = []
    for path in (ROOT / 'qatrack').rglob('*.py'):
        rel = path.relative_to(ROOT).as_posix()
        if '/migrations/' in rel or '/tests/' in rel or rel.startswith('qatrack/theme/'):
            continue
        files.append(path)
    files.sort()
    return files


def pattern_code_style_findings() -> list[Finding]:
    findings: list[Finding] = []
    for path in python_files():
        rel = path.relative_to(ROOT).as_posix()
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
        except (OSError, UnicodeDecodeError) as err:
            logging.warning('Unable to read %s for pattern scan: %s', rel, err)
            continue
        for idx, line in enumerate(lines, start=1):
            for regex, severity, recommendation in PATTERN_RULES:
                if regex.search(line):
                    findings.append(
                        Finding(
                            path=rel,
                            line=idx,
                            severity=severity,
                            confidence='high',
                            concern=f'Pattern rule matched: `{regex.pattern}`',
                            excerpt=line.strip()[:240],
                            recommendation=recommendation,
                        )
                    )
                    break
            if len(findings) >= MAX_PATTERN_FINDINGS:
                return findings
    return findings


def read_style_context() -> str:
    agents = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
    pyproject = PYPROJECT.read_text(encoding='utf-8')

    def section(text: str, header: str) -> str:
        lines = text.splitlines()
        capture = False
        captured: list[str] = []
        for line in lines:
            if line.strip() == header:
                capture = True
                captured.append(line)
                continue
            if capture and line.startswith('### '):
                break
            if capture:
                captured.append(line)
        return '\n'.join(captured).strip()

    dependencies_section = section(agents, '### Dependencies')
    language_section = section(agents, '### Language')
    agents_focus = '\n\n'.join(s for s in [dependencies_section, language_section] if s)

    pyproject_keywords = ('requires-python', 'Django', 'ruff', 'target-version', 'quote-style')
    pyproject_focus = '\n'.join(
        line
        for line in pyproject.splitlines()
        if any(keyword in line for keyword in pyproject_keywords)
    )
    return f'AGENTS.md context:\n{agents_focus}\n\npyproject.toml context:\n{pyproject_focus}'


def sample_code_for_ai() -> str:
    samples: list[str] = []
    for path in python_files()[:MAX_SAMPLE_FILES]:
        rel = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError) as err:
            logging.warning('Unable to read %s for AI code sample: %s', rel, err)
            continue
        snippet = '\n'.join(text.splitlines()[:120])[:7000]
        samples.append(f'FILE: {rel}\n```\n{snippet}\n```')
    return '\n\n'.join(samples)


def sample_docs_for_ai() -> str:
    docs: list[Path] = sorted((ROOT / 'docs').rglob('*.rst'))
    extras = [ROOT / 'README.md', ROOT / 'AGENTS.md']
    files = docs[:MAX_DOC_FILES] + [p for p in extras if p.exists()]
    samples: list[str] = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError) as err:
            logging.warning('Unable to read %s for AI docs sample: %s', rel, err)
            continue
        snippet = '\n'.join(text.splitlines()[:140])[:7000]
        samples.append(f'FILE: {rel}\n```\n{snippet}\n```')
    return '\n\n'.join(samples)


def _extract_json_payload(content: str) -> list[dict]:
    content = content.strip()
    if content.startswith('```'):
        lines = content.splitlines()
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        for i, line in enumerate(lines):
            if line.strip() == '```':
                lines = lines[:i]
                break
        content = '\n'.join(lines).strip()
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return parsed
        return []
    except json.JSONDecodeError:
        match = re.search(r'(\[\s*\{.*\}\s*\])', content, flags=re.DOTALL)
        if not match:
            return []
        try:
            parsed = json.loads(match.group(1))
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []


def ai_review(prompt: str) -> tuple[list[dict], str | None]:
    token = os.environ.get('GITHUB_TOKEN')
    api_url = os.environ.get('AI_API_URL', 'https://models.inference.ai.azure.com/chat/completions')
    model = os.environ.get('AI_MODEL', 'gpt-4.1-mini')
    if not token:
        return [], 'Missing GITHUB_TOKEN for AI review.'
    payload = {
        'model': model,
        'temperature': 0.1,
        'messages': [
            {
                'role': 'system',
                'content': (
                    'You are reviewing a Django/Python repository. '
                    'Return only a JSON array. Do not include prose outside JSON.'
                ),
            },
            {'role': 'user', 'content': prompt},
        ],
    }
    request = urllib.request.Request(api_url, method='POST', data=json.dumps(payload).encode('utf-8'))
    request.add_header('Authorization', 'Bearer ' + token)
    request.add_header('Content-Type', 'application/json')
    request.add_header('User-Agent', 'qatrackplus-annual-health-review')
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as err:
        return [], f'AI API HTTP error: {err.code}'
    except urllib.error.URLError as err:
        return [], f'AI API URL error: {err}'
    except TimeoutError as err:
        return [], f'AI API timeout: {err}'
    except json.JSONDecodeError as err:
        return [], f'AI API returned invalid JSON: {err}'

    content = body.get('choices', [{}])[0].get('message', {}).get('content', '')
    parsed = _extract_json_payload(content)
    return parsed, None


def ai_code_style_findings() -> tuple[list[Finding], str | None]:
    prompt = f"""
Repository style context:
{read_style_context()}

Code samples:
{sample_code_for_ai()}

Task:
- Identify code style drift or outdated idioms at a deep level for Python 3.12 and Django 4.2.
- Keep this output independent from any pattern-based checks; overlap is acceptable.
- Return max {MAX_AI_STYLE_FINDINGS} findings as a JSON array.
- Each object must include: path, line, severity, confidence, concern, excerpt, recommendation.
- Confidence should be one of: high, medium, low.
- Severity should be one of: high, medium, low.
"""
    raw, err = ai_review(prompt)
    if err:
        return [], err
    findings: list[Finding] = []
    for item in raw[:MAX_AI_STYLE_FINDINGS]:
        findings.append(
            Finding(
                path=str(item.get('path', 'unknown')),
                line=int(item.get('line', 1) or 1),
                severity=str(item.get('severity', 'medium')),
                confidence=str(item.get('confidence', 'medium')),
                concern=str(item.get('concern', 'AI-identified style concern')),
                excerpt=str(item.get('excerpt', '')).strip()[:240],
                recommendation=str(item.get('recommendation', '')),
            )
        )
    return findings, None


def ai_doc_tone_findings() -> tuple[list[Finding], str | None]:
    prompt = f"""
Repository writing guidance:
{read_style_context()}

Documentation samples:
{sample_docs_for_ai()}

Task:
- Review for tone mismatch against approachable, human, Canadian-English style.
- Flag passages that are too formal, abrupt, dry, or off-putting.
- Ignore low-value spelling-variant complaints when internal consistency exists.
- Return max {MAX_AI_DOC_FINDINGS} findings as a JSON array.
- Each object must include: path, line, severity, confidence, concern, excerpt, recommendation.
"""
    raw, err = ai_review(prompt)
    if err:
        return [], err
    findings: list[Finding] = []
    for item in raw[:MAX_AI_DOC_FINDINGS]:
        findings.append(
            Finding(
                path=str(item.get('path', 'unknown')),
                line=int(item.get('line', 1) or 1),
                severity=str(item.get('severity', 'medium')),
                confidence=str(item.get('confidence', 'medium')),
                concern=str(item.get('concern', 'AI-identified documentation tone concern')),
                excerpt=str(item.get('excerpt', '')).strip()[:240],
                recommendation=str(item.get('recommendation', '')),
            )
        )
    return findings, None


def format_findings(findings: list[Finding], empty_message: str) -> str:
    if not findings:
        return empty_message
    lines: list[str] = []
    for f in findings:
        lines.append(
            f"- **[{f.severity}/{f.confidence}]** `{f.path}:{f.line}` — {f.concern}\n"
            f"  - Excerpt: `{f.excerpt}`\n"
            f"  - Recommendation: {f.recommendation}"
        )
    return '\n'.join(lines)


def format_dependency_findings(findings: list[dict]) -> str:
    if not findings:
        return 'No high-signal dependency maintenance concerns were detected this run.'
    lines: list[str] = []
    for item in findings:
        signals = '; '.join(item.get('signals', []))
        lines.append(f"- **[{item.get('severity', 'medium')}]** `{item['package']}` — {signals}")
    return '\n'.join(lines)


def get_repo_and_year() -> tuple[str, str, int]:
    repository = os.environ.get('GITHUB_REPOSITORY')
    if not repository or '/' not in repository:
        raise RuntimeError('GITHUB_REPOSITORY is required (owner/repo).')
    owner, repo = repository.split('/', 1)
    year = int(os.environ.get('ANNUAL_REVIEW_YEAR', dt.datetime.now(dt.UTC).year))
    return owner, repo, year


def find_or_create_issue(owner: str, repo: str, token: str, title: str, body: str) -> None:
    issues = http_json(
        'GET',
        github_api(f'/repos/{owner}/{repo}/issues?state=open&per_page=100'),
        token,
    )
    if not isinstance(issues, list):
        raise RuntimeError(f'Expected list response for issues query, got: {type(issues).__name__}')
    existing = None
    for issue in issues:
        if 'pull_request' in issue:
            continue
        if issue.get('title') == title:
            existing = issue
            break

    labels_api = http_json('GET', github_api(f'/repos/{owner}/{repo}/labels?per_page=100'), token)
    if not isinstance(labels_api, list):
        raise RuntimeError(f'Expected list response for labels query, got: {type(labels_api).__name__}')
    existing_label_names = {item.get('name') for item in labels_api}
    labels = [label for label in DESIRED_LABELS if label in existing_label_names]

    payload = {'title': title, 'body': body}
    if labels:
        payload['labels'] = labels

    if existing:
        issue_number = existing['number']
        update_payload = {'body': body, 'labels': labels}
        http_json('PATCH', github_api(f'/repos/{owner}/{repo}/issues/{issue_number}'), token, payload=update_payload)
        print(f'Updated existing annual issue #{issue_number}.')
    else:
        created = http_json('POST', github_api(f'/repos/{owner}/{repo}/issues'), token, payload)
        if not isinstance(created, dict):
            raise RuntimeError(f'Expected issue create response object, got: {type(created).__name__}')
        print(f"Created annual issue #{created.get('number')}.")


def main() -> int:
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print('GITHUB_TOKEN is required.', file=sys.stderr)
        return 1

    owner, repo, year = get_repo_and_year()
    pyproject = load_pyproject()
    dependencies = extract_dependencies(pyproject)
    dep_findings = dependency_findings(dependencies)
    pattern_findings = pattern_code_style_findings()
    ai_style_findings, ai_style_error = ai_code_style_findings()
    ai_doc_findings, ai_doc_error = ai_doc_tone_findings()

    now = dt.datetime.now(dt.UTC).strftime('%Y-%m-%d %H:%M UTC')
    ai_style_section = format_findings(
        ai_style_findings,
        f'No AI-driven code style findings were returned.{" " + ai_style_error if ai_style_error else ""}',
    )
    ai_doc_section = format_findings(
        ai_doc_findings,
        f'No AI-driven documentation tone findings were returned.{" " + ai_doc_error if ai_doc_error else ""}',
    )
    pattern_section = format_findings(
        pattern_findings,
        'No pattern-based code style findings were detected for the configured heuristic rules.',
    )

    body = f"""## Annual repository health review ({year})

_Generated: {now}_

This annual issue is a roadmap input, not a fix-everything-now demand. Findings are expected to be resolved incrementally through the year as **distinct, focused PRs**.

### How to use this issue
- Pick one theme or small cluster of related findings.
- Open a dedicated PR for that slice of work.
- Reference this issue section in each follow-up PR.
- Avoid giant all-in-one remediation branches.

### Review tracks included
1. Dependency health review (deterministic signals)
2. Pattern-based code style review (heuristic rules)
3. AI-driven code style review (deep analysis)
4. AI-assisted documentation tone review

> **No deduplication policy:** overlap between pattern-based and AI-driven code style sections is expected and acceptable.

## 1) Dependency health review
{format_dependency_findings(dep_findings)}

## 2) Pattern-based code style review
{pattern_section}

## 3) AI-driven code style review
{ai_style_section}

## 4) AI-assisted documentation tone review
{ai_doc_section}

---

### Notes
- AI findings are heuristic and may include overlap with pattern findings.
- This workflow is review-only and does not auto-edit files.
- Prioritize changes by impact and risk, then split work into separate PRs across the year.
"""

    title = f'Annual Repository Health Review {year}'
    find_or_create_issue(owner, repo, token, title, body)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

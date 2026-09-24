from pathlib import Path
import re

PATH = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')


def mask_noncode(src: str) -> str:
    out = list(src)
    i = 0
    n = len(src)
    state = 'code'
    quote = ''
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        if state == 'code':
            if c == '/' and nxt == '/':
                out[i] = out[i + 1] = ' '
                i += 2
                state = 'line_comment'
                continue
            if c == '/' and nxt == '*':
                out[i] = out[i + 1] = ' '
                i += 2
                state = 'block_comment'
                continue
            if c in ('\'', '"', '`'):
                quote = c
                out[i] = ' '
                i += 1
                state = 'string'
                continue
            i += 1
            continue
        if state == 'line_comment':
            if c == '\n':
                state = 'code'
            else:
                out[i] = ' '
            i += 1
            continue
        if state == 'block_comment':
            if c == '*' and nxt == '/':
                out[i] = out[i + 1] = ' '
                i += 2
                state = 'code'
            else:
                if c != '\n':
                    out[i] = ' '
                i += 1
            continue
        if state == 'string':
            if c == '\\':
                out[i] = ' '
                if i + 1 < n:
                    if src[i + 1] != '\n':
                        out[i + 1] = ' '
                    i += 2
                else:
                    i += 1
                continue
            if c == quote:
                out[i] = ' '
                i += 1
                state = 'code'
                continue
            if c != '\n':
                out[i] = ' '
            i += 1
            continue
    return ''.join(out)


def find_top_level_functions(src: str):
    masked = mask_noncode(src)
    depth = 0
    positions = []
    i = 0
    n = len(masked)
    while i < n:
        c = masked[i]
        if c == '{':
            depth += 1
            i += 1
            continue
        if c == '}':
            depth = max(0, depth - 1)
            i += 1
            continue
        if depth == 0 and masked.startswith('function', i):
            before = masked[i - 1] if i else ' '
            after = masked[i + 8] if i + 8 < n else ' '
            if not (before.isalnum() or before in '_$') and after.isspace():
                m = re.match(r'function\s+([A-Za-z_$][\w$]*)\s*\(', masked[i:])
                if m:
                    name = m.group(1)
                    brace = masked.find('{', i + m.end())
                    if brace == -1:
                        raise RuntimeError(f'No opening brace for {name}')
                    d = 1
                    j = brace + 1
                    while j < n and d:
                        if masked[j] == '{':
                            d += 1
                        elif masked[j] == '}':
                            d -= 1
                        j += 1
                    if d != 0:
                        raise RuntimeError(f'Unbalanced function {name}')
                    end = j
                    while end < n and masked[end] in ' \t\r':
                        end += 1
                    if end < n and masked[end] == ';':
                        end += 1
                    if end < n and masked[end] == '\n':
                        end += 1
                    positions.append((name, i, end))
                    i = end
                    continue
        i += 1
    return positions


def consolidate(src: str):
    funcs = find_top_level_functions(src)
    by_name = {}
    for idx, (name, start, end) in enumerate(funcs):
        by_name.setdefault(name, []).append((idx, start, end))

    duplicate_names = {k: v for k, v in by_name.items() if len(v) > 1}
    remove = []
    for name, items in duplicate_names.items():
        # Preserve runtime semantics of the current file: the last top-level declaration wins.
        for _, start, end in items[:-1]:
            remove.append((start, end, name))

    out = src
    for start, end, name in sorted(remove, reverse=True):
        out = out[:start] + f'// [V10 CLEAN] wcześniejsza definicja {name} usunięta; aktywna wersja znajduje się dalej w pliku.\n' + out[end:]

    # Remove accidental standalone garbage identifiers observed during manual copy/paste.
    out = re.sub(r'(?m)^\s*[aA]\s*;?\s*$', '', out)

    return out, duplicate_names


def count_functions(src: str):
    counts = {}
    for name, _, _ in find_top_level_functions(src):
        counts[name] = counts.get(name, 0) + 1
    return counts


def main():
    src = PATH.read_text(encoding='utf-8')
    cleaned, dups = consolidate(src)
    counts = count_functions(cleaned)
    still_dups = {k: v for k, v in counts.items() if v > 1}
    if still_dups:
        raise SystemExit(f'Duplicates remain: {still_dups}')

    required = [
        'onOpen','V8_SETUP','ODSWIEZ_WSZYSTKO','ODSWIEZ_PORANNY_BRIEF',
        'ODSWIEZ_ETF_BTC_ETH','ODSWIEZ_LAB','SPRAWDZ_EKSTREMA',
        'writePolishPanel_','writeLongEngine_','writeTacticalEngine_',
        'writeFlowEngine_','writeMorningRadarBrief_','setupMorningBrief_',
        'classifyAlarmDirection_','alarmDirection_'
    ]
    missing = [x for x in required if counts.get(x) != 1]
    if missing:
        raise SystemExit(f'Required functions missing/not unique: {missing}')

    PATH.write_text(cleaned, encoding='utf-8')
    print('V10 consolidated successfully')
    print('Removed duplicate definitions:', {k: len(v)-1 for k, v in sorted(dups.items())})
    print('Final top-level function count:', len(counts))


if __name__ == '__main__':
    main()

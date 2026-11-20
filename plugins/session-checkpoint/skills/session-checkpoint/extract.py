#!/usr/bin/env python3
"""Digest a Claude Code session transcript for a checkpoint audit.

Usage: extract.py <session.jsonl> <out_dir> [--scratchpad DIR] [--notes FILE ...]

Writes into out_dir:
  owner.md      every message the owner typed, numbered, with transcript line and time
                (typed turns AND messages typed mid-turn, delivered as queued_command)
  peers.md      messages from other Claude sessions and subagent hand-backs (secondary input)
  assistant.md  the assistant's visible text replies (what was told to the owner)
  scratch.md    every file in the scratchpad, flagged when no note file mentions it
Prints a one-line summary. Never prints message bodies to stdout.
"""
import json, os, re, sys, argparse, datetime

SKIP_PREFIX = ('<system-reminder', '<task-notification', '<local-command', 'Caveat:', '[Request interrupted')
PEER_MARK = ('<cross-session-message', '<agent-message', '[Subagent hand-back]')
NOTIFY_MARK = ('[SYSTEM NOTIFICATION', '<task-notification')
SUMMARY_MARK = 'This session is being continued from a previous conversation'


def texts(content):
    if isinstance(content, str):
        return [content]
    out = []
    for c in content or []:
        if isinstance(c, dict) and c.get('type') == 'text':
            out.append(c.get('text', ''))
    return out


def has_tool_result(content):
    return isinstance(content, list) and any(isinstance(c, dict) and c.get('type') == 'tool_result' for c in content)


def strip_reminders(t):
    return re.sub(r'<system-reminder[^>]*>.*?</system-reminder>', '', t, flags=re.S).strip()


def classify(t):
    s = t.lstrip()
    if not s or SUMMARY_MARK in s[:300]:
        return None
    if any(m in s[:400] for m in PEER_MARK):
        return 'peer'
    if s.startswith(NOTIFY_MARK) or s.startswith(SKIP_PREFIX):
        return None
    return 'owner'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('jsonl'); ap.add_argument('out')
    ap.add_argument('--scratchpad'); ap.add_argument('--notes', nargs='*', default=[])
    ap.add_argument('--durable', nargs='*', default=[], help='folders where scratchpad work was copied (same name and size counts as saved)')
    a = ap.parse_args()
    if not os.path.isfile(a.jsonl):
        print(f'error: transcript not found: {a.jsonl}', file=sys.stderr); sys.exit(2)
    if a.scratchpad and not os.path.isdir(a.scratchpad):
        print(f'error: scratchpad is not a directory: {a.scratchpad}', file=sys.stderr); sys.exit(2)
    os.makedirs(a.out, exist_ok=True)
    owner, peers, asst = [], [], []
    seen = set()
    for n, line in enumerate(open(a.jsonl, encoding='utf-8', errors='replace'), 1):
        try:
            r = json.loads(line)
        except Exception:
            continue
        ts = (r.get('timestamp') or '')[:16]
        t = r.get('type')
        if t == 'user' and not r.get('isCompactSummary'):
            c = (r.get('message') or {}).get('content')
            if has_tool_result(c):
                continue
            for x in texts(c):
                x = strip_reminders(x)
                k = classify(x)
                if r.get('isMeta') and k != 'peer':   # meta records are never the owner
                    continue
                if k and (k, x) not in seen:
                    seen.add((k, x)); (owner if k == 'owner' else peers).append((n, ts, x))
        elif t == 'attachment' and (r.get('attachment') or {}).get('type') == 'queued_command':
            x = strip_reminders(str(r['attachment'].get('prompt') or ''))
            k = classify(x)
            if k and (k, x) not in seen:
                seen.add((k, x)); (owner if k == 'owner' else peers).append((n, ts, x + '\n[typed mid-turn]' if k == 'owner' else x))
        elif t == 'queue-operation' and r.get('operation') == 'enqueue':
            x = strip_reminders(str(r.get('content') or ''))
            k = classify(x)
            if k == 'peer' and not any(x in p[2] or p[2] in x for p in peers):
                peers.append((n, ts, x))
        elif t == 'assistant':
            for x in texts((r.get('message') or {}).get('content')):
                if x.strip():
                    asst.append((n, ts, x.strip()))

    def dump(name, rows, title):
        with open(os.path.join(a.out, name), 'w') as f:
            f.write(f'# {title}\n\nSource: {a.jsonl}\n\n')
            for i, (n, ts, x) in enumerate(rows, 1):
                f.write(f'## {i}. line {n}, {ts} UTC\n\n{x}\n\n')
    dump('owner.md', owner, 'Owner messages (typed by the owner)')
    dump('peers.md', peers, 'Peer-session and subagent messages (NOT the owner)')
    dump('assistant.md', asst, 'Assistant replies (what the owner was told)')

    flagged = 0
    if a.scratchpad and os.path.isdir(a.scratchpad):
        notes = ''
        for p in a.notes:
            for root, _, files in (os.walk(p) if os.path.isdir(p) else [(os.path.dirname(p), [], [os.path.basename(p)])]):
                for fn in files:
                    fp = os.path.join(root, fn)
                    if fp.endswith(('.md', '.txt', '.json', '.yaml', '.yml')):
                        try: notes += open(fp, errors='replace').read()
                        except Exception: pass
        saved = set()
        for d in a.durable:
            for root, _, files in os.walk(d):
                for fn in files:
                    try: saved.add((fn, os.path.getsize(os.path.join(root, fn))))
                    except Exception: pass
        rows = []
        for root, dirs, files in os.walk(a.scratchpad):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', 'tasks') and not d.endswith('venv') and d != 'cache']
            for fn in files:
                fp = os.path.join(root, fn); rel = os.path.relpath(fp, a.scratchpad)
                if os.path.abspath(fp).startswith(os.path.abspath(a.out)):
                    continue
                sz = os.path.getsize(fp)
                state = 'COPIED' if (fn, sz) in saved else ('named' if (fn in notes or rel in notes) else 'NOT-SAVED')
                flagged += state == 'NOT-SAVED'
                rows.append((state, rel, sz))
        with open(os.path.join(a.out, 'scratch.md'), 'w') as f:
            f.write(f'# Scratchpad files\n\nScratchpad: {a.scratchpad}\nCOPIED = an identical-size copy exists in a --durable folder. named = a note file mentions it but no copy was found (check the note says where it went). NOT-SAVED = lost at restart unless copied or deliberately discarded.\n\n')
            order = {'NOT-SAVED': 0, 'named': 1, 'COPIED': 2}
            for state, rel, sz in sorted(rows, key=lambda r: (order[r[0]], r[1])):
                f.write(f"- {state:9s} {rel} ({sz:,} B)\n")
    print(f'owner {len(owner)}, peers {len(peers)}, assistant {len(asst)}, scratchpad files NOT-SAVED {flagged}; written to {a.out}')


if __name__ == '__main__':
    main()

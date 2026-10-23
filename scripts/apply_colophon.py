"""Install/check the shared footer without rewriting unrelated markup. No runtime dependencies."""
import argparse
import json
from pathlib import Path
import re
import subprocess

START = '<!-- CWU COLOPHON START -->'
END = '<!-- CWU COLOPHON END -->'
LINK = re.compile(r'<link\b[^>]*data-cwu-colophon[^>]*>\s*', re.I)
BLOCK = re.compile(r'\n?' + re.escape(START) + r'.*?' + re.escape(END) + r'\s*', re.S)

def pages(root):
    tracked = subprocess.run(['git', '-C', str(root), 'ls-files', '--cached', '--others', '--exclude-standard', '*.html'], capture_output=True, text=True, check=True).stdout.splitlines()
    return [root / name for name in sorted(set(tracked)) if not any(part in {'source', '.deps', 'node_modules', 'captures', 'scripts', 'templates'} for part in Path(name).parts)]

def integrate(text, template, target):
    footer_start = text.lower().rfind('<footer')
    footer_end = text.lower().rfind('</footer>')
    region = text[footer_start:footer_end]
    found = None
    for match in re.finditer(r'<div\b[^>]*>', region, re.I):
        classes = re.search(r'class=["\x27]([^"\x27]*)', match.group(), re.I)
        if classes and target in classes.group(1).split():
            found = match
            break
    if found:
        depth = 1
        closing = None
        for match in re.finditer(r'</?div\b[^>]*>', region[found.end():], re.I):
            depth += -1 if match.group().startswith('</') else 1
            if depth == 0:
                closing = found.end() + match.start()
                break
        if closing is None:
            raise ValueError('Unbalanced existing footer container: ' + target)
        opening = found.group()
        if target != 'footer-meta' and 'cwu-legal-row' not in opening:
            opening = re.sub(r'(class=["\x27])', r'\1cwu-legal-row ', opening, count=1)
        region = region[:found.start()] + opening + region[found.end():closing] + template + region[closing:]
        return text[:footer_start] + region + text[footer_end:]
    return text[:footer_end] + template + text[footer_end:]

def apply(root, check=False):
    root = Path(root)
    config = json.loads((root / 'site-colophon.json').read_text(encoding='utf-8'))
    template = (root / 'scripts' / 'colophon.html').read_text(encoding='utf-8').strip()
    rendered = skipped = changed = 0
    failures = []
    for path in pages(root):
        original = path.read_text(encoding='utf-8-sig')
        if re.search(r'<meta\b[^>]*http-equiv\s*=\s*[\"\x27]?refresh', original, re.I):
            skipped += 1
            continue
        rendered += 1
        prefix = '../' * (len(path.relative_to(root).parts) - 1)
        csslink = '<link rel="stylesheet" href="' + prefix + 'assets/cwu-colophon.css" data-cwu-colophon="true">'
        if check:
            if original.count('id="cwu-colophon"') != 1 or original.count(START) != 1 or csslink not in original or template not in original or (config.get('ownerAssumesMediaOwnership') and 'falerios' in original.lower()):
                failures.append(str(path.relative_to(root)))
            continue
        text = LINK.sub('', BLOCK.sub('', original))
        if config.get('ownerAssumesMediaOwnership'):
            text = re.sub(r'<span>Source photo credit:.*?</span>', '', text, flags=re.S)
            text = re.sub(r'<p\b[^>]*>.*?</p>', lambda m: '' if 'falerios' in m.group().lower() or 'Truck photo courtesey of Rinehart driver' in m.group() else m.group(), text, flags=re.S)
        text = re.sub(r'Independent design review\s*(?:&middot;|&#183;|.)\s*Source photo credit:', 'Source photo credit:', text)
        text = re.sub(r'</head\s*>', csslink + '\n</head>', text, count=1, flags=re.I)
        if re.search(r'</footer\s*>', text, re.I):
            text = integrate(text, template, config.get('footerContainer', 'footer-base'))
        else:
            text = re.sub(r'</body\s*>', '<footer class="cwu-preview-footer">\n' + template + '\n</footer>\n</body>', text, count=1, flags=re.I)
        text = re.sub(r'[ \t]+\n(?=<!-- CWU COLOPHON START -->)', '\n', text)
        if text != original:
            path.write_text(text, encoding='utf-8')
            changed += 1
    if failures:
        raise SystemExit('Colophon check failed: ' + ', '.join(failures))
    result = dict(rendered=rendered, redirects=skipped, changed=changed, checked=check)
    print(json.dumps(result))
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    apply(args.root, args.check)

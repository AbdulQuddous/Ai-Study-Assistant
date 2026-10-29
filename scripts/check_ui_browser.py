"""Exercise real rendered templates and local scripts with Chromium WebDriver."""
import argparse
import base64
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

BASE = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='Check the real UI in Chromium using isolated synthetic fixtures.')
parser.add_argument('--browser', type=Path, help='Chromium/Chrome executable')
parser.add_argument('--driver', type=Path, help='Compatible ChromeDriver executable')
parser.add_argument('--screenshots-dir', type=Path, default=BASE / 'docs/screenshots')
args = parser.parse_args()

def find_executable(explicit, candidates):
    if explicit:
        return str(explicit.resolve())
    for candidate in candidates:
        found = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
        if found:
            return found
    parser.error('Chromium and ChromeDriver are required; pass --browser and --driver.')

BROWSER = find_executable(args.browser, ['/snap/chromium/current/usr/lib/chromium-browser/chrome', 'chromium', 'google-chrome', 'chromium-browser'])
DRIVER = find_executable(args.driver, ['/snap/chromium/current/usr/lib/chromium-browser/chromedriver', 'chromedriver'])
preview_dir = tempfile.TemporaryDirectory(prefix='study-ui-preview-')
PREVIEW = Path(preview_dir.name)
subprocess.run([sys.executable, str(BASE / 'scripts/render_ui_preview.py'), '--output-dir', str(PREVIEW)], check=True)
ARTIFACTS = args.screenshots_dir.resolve()
ARTIFACTS.mkdir(parents=True, exist_ok=True)
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
endpoint = f'http://127.0.0.1:{port}'
log = open(PREVIEW / 'webdriver.log', 'w')
process = subprocess.Popen([DRIVER, f'--port={port}', '--allowed-ips=127.0.0.1'], stdout=log, stderr=log)
session = None
checks = []

def request(method, path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(endpoint + path, data=body, method=method, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.load(response).get('value')
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode()) from None
    if isinstance(result, dict) and 'error' in result:
        raise RuntimeError(str(result))
    return result

def cmd(path, payload=None, method='POST'):
    return request(method, f'/session/{session}' + path, payload)

def js(code, *args):
    return cmd('/execute/sync', {'script': code, 'args': list(args)})

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)

def load(page):
    cmd('/url', {'url': (PREVIEW / f'{page}.html').as_uri()})
    time.sleep(.1)
    check(f'{page}: script loaded', js("return document.querySelector('[data-theme-toggle]').hasAttribute('aria-pressed')"))

def size(width, height, mobile=False):
    cmd('/goog/cdp/execute', {'cmd': 'Emulation.setDeviceMetricsOverride', 'params': {
        'width': width, 'height': height, 'deviceScaleFactor': 1, 'mobile': mobile}})
    cmd('/window/rect', {'width': width, 'height': height})

def screenshot(name):
    data = cmd('/screenshot', method='GET')
    (ARTIFACTS / f'{name}.png').write_bytes(base64.b64decode(data))

def click(selector):
    js('document.querySelector(arguments[0]).click()', selector)

def type_value(selector, value):
    js("const el=document.querySelector(arguments[0]);el.value=arguments[1];el.dispatchEvent(new Event('input',{bubbles:true}));", selector, value)

try:
    for _ in range(50):
        try:
            request('GET', '/status')
            break
        except Exception:
            time.sleep(.1)
    value = request('POST', '/session', {'capabilities': {'alwaysMatch': {
        'browserName': 'chrome', 'goog:chromeOptions': {'binary': BROWSER, 'args': [
            '--headless', '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
            '--no-first-run', '--disable-background-networking', '--allow-file-access-from-files',
            '--force-device-scale-factor=1']}, 'goog:loggingPrefs': {'browser': 'ALL'}}}})
    session = value['sessionId']
    size(1440, 1120)
    load('dashboard')
    check('desktop layout has no overflow', js('return document.documentElement.scrollWidth <= innerWidth'))
    screenshot('dashboard-desktop')
    click('[data-theme-toggle]')
    check('theme switches to dark', js("return document.documentElement.dataset.theme === 'dark'"))
    cmd('/refresh', {})
    check('theme persists after reload', js("return document.documentElement.dataset.theme === 'dark'"))
    screenshot('dashboard-dark')
    click('[data-theme-toggle]')
    for page in ['subjects', 'notes', 'documents', 'upload', 'document', 'qa', 'quizzes', 'quiz-detail', 'quiz', 'result', 'profile', 'login', 'register', 'note-form', 'subject-form', 'note']:
        load(page)
        check(f'{page}: no desktop overflow', js('return document.documentElement.scrollWidth <= innerWidth'))
        if page in ['subjects', 'notes', 'documents', 'document', 'qa', 'quizzes', 'quiz', 'result', 'login', 'upload']:
            screenshot(f'{page}-desktop')
    load('documents')
    type_value('#document-filter', 'algorithms')
    check('document filter narrows visible cards', js("return document.querySelectorAll('#document-grid [data-filter-card]:not([hidden])').length === 1"))
    type_value('#document-filter', 'no-document-matches-this')
    check('filter empty state appears', js("return !document.querySelector('#document-no-results').hidden"))
    click('[data-clear-filter]')
    check('clearing filter restores cards', js("return document.querySelectorAll('#document-grid [data-filter-card]:not([hidden])').length === 4"))
    load('qa')
    check('AI answers display emphasis instead of Markdown markers', js("return !!document.querySelector('.message-answer .ai-prose strong') && !document.querySelector('.message-answer .ai-prose').innerText.includes('**')"))
    check('AI answers display readable bullet lists', js("return document.querySelectorAll('.message-answer .ai-prose li').length === 2"))
    check('AI answer copy target has no space entity artifacts', js("return !document.querySelector('[id^=answer-]').innerText.includes('&#x20;')"))
    click('[data-question-suggestion]')
    check('question suggestion fills textarea', js("return document.querySelector('textarea').value.includes('main ideas')"))
    check('question character count updates', js("return !document.querySelector('.character-count').textContent.startsWith('0 /')"))
    click('.sources summary')
    check('source excerpt expands', js("return document.querySelector('.sources details').open"))
    load('document')
    check('AI summary displays section headings', js("return document.querySelectorAll('#document-summary h3').length === 3"))
    check('AI summary displays numbered and bullet lists', js("return !!document.querySelector('#document-summary ol') && !!document.querySelector('#document-summary ul')"))
    check('AI summary copy target has no formatting artifacts', js("return !document.querySelector('#document-summary').innerText.includes('**') && !document.querySelector('#document-summary').innerText.includes('&#x20;') && !document.querySelector('#document-summary').innerText.includes('###')"))
    load('login')
    type_value('input[type="password"]', 'synthetic-only')
    click('.password-toggle')
    check('password visibility toggle works', js("return document.querySelector('input[name=password]').type === 'text'"))
    load('note-form')
    type_value('textarea[name="content"]', 'Three little words')
    check('note word count updates', js("return document.querySelector('[data-word-count]').textContent === '3 words'"))
    load('upload')
    js("const data=new DataTransfer();data.items.add(new File(['%PDF-demo'], 'lecture.pdf', {type:'application/pdf'}));const input=document.querySelector('input[type=file]');input.files=data.files;input.dispatchEvent(new Event('change',{bubbles:true}));")
    check('selected PDF feedback appears', js("return document.querySelector('[data-file-feedback]').textContent.includes('lecture.pdf') && document.querySelector('input[type=file]').validity.valid"))
    js("const data=new DataTransfer();data.items.add(new File(['wrong type'], 'lecture.txt'));const input=document.querySelector('input[type=file]');input.files=data.files;input.dispatchEvent(new Event('change',{bubbles:true}));")
    check('invalid extension is rejected in browser', js("return !document.querySelector('input[type=file]').validity.valid"))
    load('quiz')
    click('input[type=radio]')
    check('quiz answered count updates', js("return document.querySelector('[data-answered-count]').textContent === '1 of 3 answered'"))
    check('quiz jump link reflects answered state', js("return document.querySelector('.question-nav a').classList.contains('is-answered')"))
    # Cancel actual file navigation after the application handles the submit event.
    js("document.addEventListener('submit', event => event.preventDefault());")
    click('#submit-btn')
    check('unanswered-question dialog opens', js("return document.querySelector('dialog').open"))
    click('[data-continue-quiz]')
    check('keep answering closes dialog', js("return !document.querySelector('dialog').open && !document.querySelector('#submit-btn').disabled"))
    click('#submit-btn')
    click('[data-confirm-submit]')
    check('confirmed submission displays loading', js("return document.querySelector('#submit-btn').disabled && document.querySelector('#quiz-form').getAttribute('aria-busy') === 'true'"))
    js("window.dispatchEvent(new PageTransitionEvent('pageshow')); ")
    check('browser back restores submit controls', js("return !document.querySelector('#submit-btn').disabled && !document.querySelector('#quiz-form').hasAttribute('aria-busy')"))
    # Mobile layouts and drawer interaction.
    size(390, 844, mobile=True)
    for page in ['dashboard', 'documents', 'upload', 'qa', 'quiz', 'result', 'login', 'register', 'notes', 'subject-form', 'note-form', 'quiz-detail', 'document']:
        load(page)
        check(f'{page}: no mobile overflow', js('return document.documentElement.scrollWidth <= innerWidth'))
        if page in ['dashboard', 'qa', 'quiz', 'login']:
            screenshot(f'{page}-mobile')
    load('dashboard')
    check('mobile sidebar starts inert', js("return document.querySelector('#sidebar').inert"))
    click('[data-menu-toggle]')
    check('mobile menu opens', js("return document.querySelector('#sidebar').classList.contains('is-open') && !document.querySelector('#sidebar').inert && document.querySelector('.workspace-body').inert"))
    click('[data-close-sidebar]')
    check('mobile menu closes and restores focus', js("return document.querySelector('#sidebar').inert && document.activeElement.matches('[data-menu-toggle]')"))
    click('[data-menu-toggle]')
    click('[data-sidebar-close]')
    check('drawer close button restores page interaction', js("return !document.querySelector('.workspace-body').inert && document.querySelector('#sidebar').inert"))
    click('[data-menu-toggle]')
    js("const elements=[...document.querySelectorAll('#sidebar a[href], #sidebar button:not([disabled])')];elements.at(-1).focus();")
    cmd('/actions', {'actions': [{'type': 'key', 'id': 'keyboard', 'actions': [
        {'type': 'keyDown', 'value': '\ue004'}, {'type': 'keyUp', 'value': '\ue004'}]}]})
    check('Tab keeps focus inside the mobile drawer', js("return document.activeElement === document.querySelector('#sidebar a')"))
    cmd('/actions', {'actions': [{'type': 'key', 'id': 'keyboard', 'actions': [
        {'type': 'keyDown', 'value': '\ue00c'}, {'type': 'keyUp', 'value': '\ue00c'}]}]})
    check('Escape closes the drawer and restores focus', js("return document.querySelector('#sidebar').inert && document.activeElement.matches('[data-menu-toggle]')"))
    size(320, 740, mobile=True)
    for page in ['dashboard', 'quiz', 'qa', 'upload', 'register']:
        load(page)
        check(f'{page}: no overflow at 320px', js('return document.documentElement.scrollWidth <= innerWidth'))
    logs = cmd('/se/log', {'type': 'browser'})
    errors = [item['message'] for item in logs if item.get('level') == 'SEVERE']
    check('no browser console errors', not errors)
    report = {'passed': len(checks), 'checks': checks, 'console_errors': errors,
              'screenshots': sorted(path.name for path in ARTIFACTS.glob('*.png')),
              'fixtures': 'Synthetic data rendered through real Django views; no live AI calls or working database writes.'}
    (ARTIFACTS / 'browser-results.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'passed': len(checks), 'console_errors': errors, 'screenshots': report['screenshots']}, indent=2))
finally:
    if session:
        try: request('DELETE', f'/session/{session}')
        except Exception: pass
    process.terminate()
    process.wait(timeout=10)
    log.close()
    preview_dir.cleanup()

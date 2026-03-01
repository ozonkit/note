log("Go to login page")
page.goto("https://note.com/login", wait_until="domcontentloaded")
page.wait_for_load_state("networkidle")

log(f"Current URL: {page.url}")
log(f"Title: {page.title()}")

# まずは id セレクタを最優先
email_sel_candidates = ["#email", 'input#email', 'input[name="email"]', 'input[type="email"]', 'input[autocomplete="email"]']
pass_sel_candidates  = ["#password", 'input#password', 'input[name="password"]', 'input[type="password"]', 'input[autocomplete="current-password"]']

def pick_first_selector(candidates):
    for sel in candidates:
        try:
            page.wait_for_selector(sel, timeout=6_000)
            return sel
        except PlaywrightTimeoutError:
            continue
    return None

email_sel = pick_first_selector(email_sel_candidates)
pass_sel  = pick_first_selector(pass_sel_candidates)

if not email_sel or not pass_sel:
    # headlessで違うページを掴んでる可能性があるので証拠を残す
    page.screenshot(path="debug.png", full_page=True)
    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    raise RuntimeError(f"Login inputs not found. email_sel={email_sel}, pass_sel={pass_sel} (see debug.png/debug.html)")

log(f"Email selector: {email_sel}")
log(f"Pass selector:  {pass_sel}")

log("Fill credentials")
page.locator(email_sel).fill(email)
page.locator(pass_sel).fill(password)

log("Click login")
# ログインボタン候補（note側の変更に備えて複数）
login_btn_candidates = [
    'button:has-text("ログイン")',
    'button[type="submit"]',
    'input[type="submit"]',
]
clicked = False
for sel in login_btn_candidates:
    try:
        page.locator(sel).first.click(timeout=6_000)
        clicked = True
        log(f"Clicked login button: {sel}")
        break
    except Exception:
        continue

if not clicked:
    page.screenshot(path="debug.png", full_page=True)
    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    raise RuntimeError("Login button not found (see debug.png/debug.html)")

page.wait_for_load_state("networkidle")
log(f"After login URL: {page.url}")

import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

NOTE_LOGIN_URL = "https://note.com/login"
NOTE_DRAFTS_URL = "https://note.com/notes/drafts"

def log(msg: str):
    print(msg, flush=True)

def must_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

def pick_first_selector(page, candidates, timeout_each_ms=6000):
    """候補セレクタのうち最初に見つかったものを返す。見つからなければ None。"""
    for sel in candidates:
        try:
            page.wait_for_selector(sel, timeout=timeout_each_ms)
            return sel
        except PlaywrightTimeoutError:
            continue
    return None

def dismiss_common_popups(page):
    """よくある同意/閉じる系を雑に潰す（見つかったらクリックするだけ）。"""
    for sel in [
        'button:has-text("同意")',
        'button:has-text("OK")',
        'button:has-text("閉じる")',
        'button[aria-label*="閉じる"]',
        'button[aria-label*="close"]',
    ]:
        try:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.click(timeout=1500)
                log(f"Dismissed popup: {sel}")
                break
        except Exception:
            pass

def save_debug(page, prefix="debug"):
    try:
        page.screenshot(path=f"{prefix}.png", full_page=True)
    except Exception:
        pass
    try:
        with open(f"{prefix}.html", "w", encoding="utf-8") as f:
            f.write(page.content())
    except Exception:
        pass
    log(f"Saved {prefix}.png / {prefix}.html")

def publish_note_with_tags():
    hashtags = ["夫婦", "不倫", "再構築", "内省", "正しさ"]

    email = must_env("NOTE_EMAIL")
    password = must_env("NOTE_PASS")
    test_mode = os.getenv("TEST_MODE", "false").lower() in ("1", "true", "yes", "y")

    log("=== publish_note.py start ===")
    log(f"TEST_MODE={test_mode}")
    log(f"hashtags={hashtags}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        context = browser.new_context(
            locale="ja-JP",
            user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        )
        page = context.new_page()
        page.set_default_timeout(30_000)

        try:
            # --------------------
            # Login
            # --------------------
            log("Go to login page")
            page.goto(NOTE_LOGIN_URL, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle")

            log(f"Current URL: {page.url}")
            log(f"Title: {page.title()}")

            dismiss_common_popups(page)

            # まずは #email / #password を最優先にする
            email_candidates = [
                "#email",
                "input#email",
                'input[name="email"]',
                'input[type="email"]',
                'input[autocomplete="email"]',
                'input[placeholder*="メール"]',
                'input[aria-label*="メール"]',
            ]
            pass_candidates = [
                "#password",
                "input#password",
                'input[name="password"]',
                'input[type="password"]',
                'input[autocomplete="current-password"]',
                'input[placeholder*="パスワード"]',
            ]

            email_sel = pick_first_selector(page, email_candidates)
            pass_sel = pick_first_selector(page, pass_candidates)

            if not email_sel or not pass_sel:
                save_debug(page, "debug")
                raise RuntimeError(
                    f"Login inputs not found. email_sel={email_sel}, pass_sel={pass_sel}. "
                    "Possibly blocked/redirected/different DOM."
                )

            log(f"Email input found: {email_sel}")
            log(f"Password input found: {pass_sel}")

            log("Fill credentials")
            page.locator(email_sel).fill(email)
            page.locator(pass_sel).fill(password)

            # ログインボタン候補
            login_btn_candidates = [
                'button:has-text("ログイン")',
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Login")',
            ]

            clicked = False
            for sel in login_btn_candidates:
                try:
                    page.locator(sel).first.click(timeout=6_000)
                    log(f"Clicked login button: {sel}")
                    clicked = True
                    break
                except Exception:
                    continue

            if not clicked:
                save_debug(page, "debug")
                raise RuntimeError("Login button not found. See debug.png/debug.html")

            page.wait_for_load_state("networkidle")
            log(f"After login URL: {page.url}")

            # --------------------
            # Drafts -> open first draft
            # --------------------
            log("Go to drafts page")
            page.goto(NOTE_DRAFTS_URL, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle")

            dismiss_common_popups(page)

            # ドラフトの「編集」ボタン/リンク候補
            edit_candidates = [
                '.m-draftItem__edit',
                'a:has-text("編集")',
                'button:has-text("編集")',
                'a[href*="/edit"]',
            ]

            edit_sel = pick_first_selector(page, edit_candidates, timeout_each_ms=8000)
            if not edit_sel:
                save_debug(page, "debug")
                raise RuntimeError("Could not find draft edit link/button. UI selector may have changed.")

            log(f"Open first draft by: {edit_sel}")
            page.locator(edit_sel).first.click()
            page.wait_for_load_state("domcontentloaded")

            # --------------------
            # Open publish settings
            # --------------------
            log("Open publish settings")
            setting_candidates = [
                'button:has-text("公開設定")',
                'a:has-text("公開設定")',
                'button:has-text("公開")',
            ]

            setting_sel = pick_first_selector(page, setting_candidates, timeout_each_ms=8000)
            if not setting_sel:
                save_debug(page, "debug")
                raise RuntimeError("Could not open publish settings. Button text/selector may have changed.")

            page.locator(setting_sel).first.click()
            log(f"Opened publish settings using: {setting_sel}")

            # --------------------
            # Add hashtags
            # --------------------
            log("Find hashtag input")
            tag_input_candidates = [
                'input[placeholder*="ハッシュタグ"]',
                'input[aria-label*="ハッシュタグ"]',
                'input[name*="tag"]',
                'input[id*="tag"]',
            ]
            tag_sel = pick_first_selector(page, tag_input_candidates, timeout_each_ms=8000)
            if not tag_sel:
                save_debug(page, "debug")
                raise RuntimeError("Could not find hashtag input. Need to update selector.")

            log(f"Hashtag input found: {tag_sel}")

            for tag in hashtags:
                log(f"Add tag: {tag}")
                page.locator(tag_sel).click()
                page.locator(tag_sel).fill(tag)
                page.keyboard.press("Enter")
                page.wait_for_timeout(500)

            # --------------------
            # Publish (skip in TEST_MODE)
            # --------------------
            if test_mode:
                log("TEST_MODE is true: skip clicking Publish.")
            else:
                log("Click Publish")
                publish_candidates = [
                    'button:has-text("投稿する")',
                    'button:has-text("公開する")',
                ]
                pub_sel = pick_first_selector(page, publish_candidates, timeout_each_ms=10_000)
                if not pub_sel:
                    save_debug(page, "debug")
                    raise RuntimeError("Could not find Publish button. Selector/text may have changed.")
                page.locator(pub_sel).first.click()
                log(f"Clicked publish using: {pub_sel}")

            log("DONE")
            browser.close()

        except Exception as e:
            log(f"FAIL: {e}")
            save_debug(page, "debug")
            try:
                browser.close()
            except Exception:
                pass
            raise

def main():
    publish_note_with_tags()

if __name__ == "__main__":
    main()

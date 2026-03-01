import os
import sys
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
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(30_000)

        try:
            # --- ログイン ---
            log("Go to login page")
            page.goto(NOTE_LOGIN_URL, wait_until="domcontentloaded")

            log("Fill credentials")
            page.fill('input[type="email"]', email)
            page.fill('input[type="password"]', password)

            log("Click login")
            page.click('button:has-text("ログイン")')

            # ログイン後の通信が落ち着くのを待つ
            page.wait_for_load_state("networkidle")
            log("Login step done (networkidle)")

            # --- 下書き一覧へ ---
            log("Go to drafts")
            page.goto(NOTE_DRAFTS_URL, wait_until="domcontentloaded")

            # 「編集」ボタン/リンク（UI変更に備えて複数候補）
            log("Find and click draft edit")
            edit_locators = [
                '.m-draftItem__edit',
                'a:has-text("編集")',
                'button:has-text("編集")',
            ]

            for sel in edit_locators:
                try:
                    page.wait_for_selector(sel, timeout=8_000)
                    page.click(sel)
                    log(f"Clicked edit using selector: {sel}")
                    break
                except PlaywrightTimeoutError:
                    continue
            else:
                raise RuntimeError("Could not find draft edit button/link. UI selector may have changed.")

            page.wait_for_load_state("domcontentloaded")

            # --- 公開設定を開く ---
            log("Open publish settings")
            setting_candidates = [
                'button:has-text("公開設定")',
                'a:has-text("公開設定")',
                'button:has-text("公開")',
            ]
            for sel in setting_candidates:
                try:
                    page.wait_for_selector(sel, timeout=8_000)
                    page.click(sel)
                    log(f"Opened publish settings using: {sel}")
                    break
                except PlaywrightTimeoutError:
                    continue
            else:
                raise RuntimeError("Could not open publish settings. Button text/selector may have changed.")

            # --- ハッシュタグ入力 ---
            log("Find hashtag input")
            tag_input_candidates = [
                'input[placeholder*="ハッシュタグ"]',
                'input[aria-label*="ハッシュタグ"]',
                'input[name*="tag"]',
            ]
            tag_input = None
            for sel in tag_input_candidates:
                try:
                    page.wait_for_selector(sel, timeout=8_000)
                    tag_input = sel
                    log(f"Hashtag input found: {sel}")
                    break
                except PlaywrightTimeoutError:
                    continue
            if not tag_input:
                raise RuntimeError("Could not find hashtag input. Need to update selector.")

            for tag in hashtags:
                log(f"Add tag: {tag}")
                page.click(tag_input)
                page.fill(tag_input, tag)
                page.keyboard.press("Enter")
                page.wait_for_timeout(500)

            # --- 投稿ボタン ---
            if test_mode:
                log("TEST_MODE is true: skip clicking Publish.")
            else:
                log("Click Publish")
                publish_candidates = [
                    'button:has-text("投稿する")',
                    'button:has-text("公開する")',
                ]
                for sel in publish_candidates:
                    try:
                        page.wait_for_selector(sel, timeout=10_000)
                        page.click(sel)
                        log(f"Clicked publish using: {sel}")
                        break
                    except PlaywrightTimeoutError:
                        continue
                else:
                    raise RuntimeError("Could not find Publish button. Selector/text may have changed.")

            log("DONE")
            browser.close()

        except Exception as e:
            log(f"FAIL: {e}")
            try:
                page.screenshot(path="debug.png", full_page=True)
                log("Saved screenshot: debug.png")
            except Exception as _:
                pass
            try:
                browser.close()
            except Exception:
                pass
            raise  # exit code 1

def main():
    publish_note_with_tags()

if __name__ == "__main__":
    main()

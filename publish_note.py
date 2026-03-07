import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

EDIT_URL = "https://editor.note.com/notes/n466b124c2023/edit/"
NOTE_LOGIN_URL = "https://note.com/login"

def log(msg: str):
    print(msg, flush=True)

def must_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

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

def dismiss_common_popups(page):
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

def is_login_form_visible(page) -> bool:
    # note.com/login のフォームが見えているか
    try:
        return page.locator("#email").count() > 0 and page.locator("#password").count() > 0
    except Exception:
        return False

def login_if_needed(page, email: str, password: str):
    """
    いま表示されているページがログインを要求しているならログインする。
    成功しない場合は理由を残して落とす。
    """
    dismiss_common_popups(page)

    # 既にログイン済みで edit に居るなら何もしない
    if "editor.note.com" in page.url and "/edit" in page.url:
        log("Already on editor edit page (likely logged in).")
        return

    # ログインフォームが見えない場合でも、念のため /login へ行って確認
    if not is_login_form_visible(page):
        log("Login form not visible; navigating to login page to check.")
        page.goto(NOTE_LOGIN_URL, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        dismiss_common_popups(page)

    log(f"Login check URL: {page.url}")
    if not is_login_form_visible(page):
        save_debug(page, "debug_login_form_not_found")
        raise RuntimeError("Login form not found (maybe blocked or different flow). See debug_login_form_not_found.png/html")

    log("Fill credentials")
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)

    log("Click login")
    # クリックと同時に遷移が発生することが多いので、できるだけ「遷移」を待つ
    try:
        with page.expect_navigation(timeout=15_000):
            page.locator('button:has-text("ログイン")').first.click()
    except Exception:
        # expect_navigation が外れることもあるので、落ち着くまで待つ
        page.locator('button:has-text("ログイン")').first.click()

    page.wait_for_load_state("networkidle")
    log(f"After login URL: {page.url}")

    # まだ /login に留まるならログイン失敗
    if "note.com/login" in page.url:
        save_debug(page, "debug_login_failed")
        raise RuntimeError("Login failed (still on /login). See debug_login_failed.png/html")

def publish_note_with_tags():
    hashtags = ["夫婦", "不倫", "再構築", "内省", "正しさ", "不倫された側"]

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
            # 1) 編集URLへ直行（未ログインならここでログインへ飛ぶ）
            log(f"Go to edit URL: {EDIT_URL}")
            page.goto(EDIT_URL, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle")
            log(f"Current URL: {page.url}")
            log(f"Title: {page.title()}")

            # 2) 必要ならログイン
            login_if_needed(page, email, password)

            # 3) ログイン後、必ず編集URLへ戻す（リダイレクトされていた場合用）
            if "editor.note.com" not in page.url or "/edit" not in page.url:
                log("Navigate back to edit URL after login.")
                page.goto(EDIT_URL, wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle")

            log(f"On editor page URL: {page.url}")
            if "editor.note.com" not in page.url or "/edit" not in page.url:
                save_debug(page, "debug_not_on_editor")
                raise RuntimeError("Not on editor edit page even after login. See debug_not_on_editor.png/html")

            dismiss_common_popups(page)

            # 4) 公開設定を開く（候補を広めに）
            log("Open publish settings")
            publish_setting_candidates = [
                'button:has-text("公開設定")',
                'button:has-text("公開")',
                'a:has-text("公開設定")',
            ]
            opened = False
            for sel in publish_setting_candidates:
                try:
                    if page.locator(sel).count() > 0:
                        page.locator(sel).first.click(timeout=10_000)
                        opened = True
                        log(f"Opened publish settings using: {sel}")
                        break
                except Exception:
                    continue
            if not opened:
                save_debug(page, "debug_publish_settings_not_found")
                raise RuntimeError("Publish settings button not found. See debug_publish_settings_not_found.png/html")

            # 5) ハッシュタグ入力（候補を広めに）
            log("Find hashtag input")
            tag_candidates = [
                'input[placeholder*="ハッシュタグ"]',
                'input[aria-label*="ハッシュタグ"]',
                'input[name*="tag"]',
                'input[id*="tag"]',
            ]
            tag_sel = None
            for sel in tag_candidates:
                try:
                    page.wait_for_selector(sel, timeout=10_000)
                    tag_sel = sel
                    log(f"Hashtag input found: {sel}")
                    break
                except PlaywrightTimeoutError:
                    continue
            if not tag_sel:
                save_debug(page, "debug_tag_input_not_found")
                raise RuntimeError("Hashtag input not found. See debug_tag_input_not_found.png/html")

            for tag in hashtags:
                log(f"Add tag: {tag}")
                page.locator(tag_sel).click()
                page.locator(tag_sel).fill(tag)
                page.keyboard.press("Enter")
                page.wait_for_timeout(500)

            # 6) 投稿（TEST_MODEならスキップ）
            if test_mode:
                log("TEST_MODE is true: skip clicking Publish.")
            else:
                log("Click Publish (step 1)")

                publish_btn_candidates = [
                    'button:has-text("投稿する")',
                    'button:has-text("公開する")',
                ]

                def click_first(candidates, timeout=10_000):
                    for sel in candidates:
                        try:
                            page.wait_for_selector(sel, timeout=timeout)
                            page.locator(sel).first.click()
                            log(f"Clicked: {sel}")
                            return True
                        except Exception:
                            continue
                    return False

                # 1回目クリック
                if not click_first(publish_btn_candidates, timeout=15_000):
                    save_debug(page, "debug_publish_button_not_found")
                    raise RuntimeError("Publish button not found. See debug_publish_button_not_found.png/html")

                # 2段階目の確認が出るケースがあるので、短時間だけ再クリックを試す
                log("Click Publish (step 2 if confirmation appears)")
                try:
                    # 出たときだけ押せればOK。出ないなら例外→無視
                    if click_first(publish_btn_candidates, timeout=3_000):
                        log("Confirmation publish clicked.")
                except Exception:
                    pass

                # 成功判定：/edit から離れる or 公開完了っぽい表示を待つ
                log("Wait for publish completion")

                # どれか満たせば成功扱い（UI差分に備えて複数条件）
                published = False
                try:
                    page.wait_for_url(lambda url: "/edit" not in url, timeout=20_000)
                    log(f"URL changed after publish: {page.url}")
                    published = True
                except Exception:
                    pass

                if not published:
                    # “公開しました”系のトースト/文言を拾う（見つかったら成功扱い）
                    try:
                        page.wait_for_selector('text=公開しました', timeout=5_000)
                        log("Detected toast: 公開しました")
                        published = True
                    except Exception:
                        pass

                if not published:
                    # 失敗時は画面を保存して原因を見える化
                    save_debug(page, "debug_publish_maybe_failed")
                    raise RuntimeError(
                        "Publish may have failed (no URL change / no success toast). "
                        "See debug_publish_maybe_failed.png/html"
                    )

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

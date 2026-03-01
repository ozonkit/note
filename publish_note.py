from playwright.sync_api import sync_playwright

def publish_note_with_tags():
    # 設定したいハッシュタグのリスト
    hashtags = ["夫婦", "不倫", "再構築", "内省", "正しさ"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # --- ログイン処理 ---
        page.goto("https://note.com/login")
        page.fill('input[type="email"]', "あなたのメールアドレス")
        page.fill('input[type="password"]', "あなたのパスワード")
        page.click('button:has-text("ログイン")')
        page.wait_for_timeout(3000)

        # --- 下書き編集画面へ ---
        page.goto("https://note.com/notes/drafts")
        page.wait_for_selector('.m-draftItem__edit')
        page.click('.m-draftItem__edit') # 一番上の下書きを選択
        
        # --- 公開設定画面へ ---
        # 「公開設定」または「公開設定画面へ」ボタンをクリック
        page.wait_for_selector('button:has-text("公開設定")')
        page.click('button:has-text("公開設定")')

        # --- ハッシュタグの入力 ---
        # noteのハッシュタグ入力欄のプレースホルダーなどをターゲットにします
        tag_input_selector = 'input[placeholder="ハッシュタグを追加"]' # もしくは適切なセレクタ
        page.wait_for_selector(tag_input_selector)

        for tag in hashtags:
            page.fill(tag_input_selector, tag)
            page.keyboard.press("Enter")
            page.wait_for_timeout(500) # 入力反映のための短い待機

        # --- 最終的な投稿ボタン ---
        # 投稿内容やハッシュタグに間違いがないか最終確認して投稿
        # page.click('button:has-text("投稿する")') 

        print(f"以下のタグを設定して投稿処理を行いました: {', '.join(hashtags)}")
        browser.close()

# 実行
publish_note_with_tags()

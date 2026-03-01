from playwright.sync_api import sync_playwright

def publish_note():
    with sync_playwright() as p:
        # ブラウザ起動
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # ログイン処理
        page.goto("https://note.com/login")
        page.fill('input[type="email"]', "あなたのメールアドレス")
        page.fill('input[type="password"]', "あなたのパスワード")
        page.click('button:has-text("ログイン")')
        
        page.wait_for_timeout(3000) # 遷移待ち

        # 下書き一覧ページへ
        page.goto("https://note.com/notes/drafts")
        
        # 一番上の下書きの「編集」ボタンをクリック
        page.click('.m-draftItem__edit') # セレクタは時期により変動の可能性あり
        
        # 公開設定〜投稿
        page.click('button:has-text("公開設定画面へ")')
        page.click('button:has-text("投稿する")')

        print("投稿が完了しました！")
        browser.close()

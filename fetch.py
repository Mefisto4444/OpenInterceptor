from playwright.sync_api import sync_playwright, Response, BrowserContext, Page
from playwright_stealth import stealth_sync
from http.cookiejar import CookieJar, Cookie
import browser_cookie3
import json
import colorama

#Cookies oriented classes below
class CookieManager:
    """Class to manage cookies from diffrent sources."""
    def get_cookies():
        cookies = []
        cookies.extend(browser_cookie3.brave(domain_name='openai.com'))
        cookies.extend(browser_cookie3.brave(domain_name='chat.openai.com'))
        return cookies
    def prepare_cookies(cookies:list[Cookie]) -> list:
        l = []
        for c in cookies:
            l.append(PlaywrightCookie(c).serialize())
        return l

class PlaywrightCookie:
    """Class to create http.cookiejar.Cookiecompatible with playwright cookie pattern"""
    def get_httpOnly(cookie:Cookie):
        if type(cookie.__dict__['_rest']) is dict and 'HTTPOnly' in cookie.__dict__['_rest'].keys():
            return True
        return False
    
    def __init__(self, cookie:Cookie) -> None:
        self.name = cookie.name
        self.value = cookie.value
        self.domain = cookie.domain
        self.path = cookie.path
        self.expires = cookie.expires
        self.httpOnly = PlaywrightCookie.get_httpOnly(cookie)
        self.secure = bool(cookie.secure)

    def serialize(self):
        """Serialize PlaywrightCookie object to JSON."""
        return json.loads(json.dumps(self.__dict__))

    def __str__(self) -> str:
        return str(self.__dict__)

#Browser oriented and chatbot behaviour classes below
class ChatBot:
    """Class for managing chats and conversation with ChatGPT"""
    def get_last_message(page:Page):
        return page.locator('div[data-testid^="conversation-turn"]').last.locator('div[data-message-author-role="assistant"]'
        ).inner_text().strip()

    def __init__(self, context:BrowserContext, cookies:list[PlaywrightCookie]) -> None:
        self.context = context
        self.cookies = cookies
        self.responding = False

    def response_filter(self, response:Response, page:Page):
        if response.url == 'https://chat.openai.com/backend-api/lat/r':
            print(ChatBot.get_last_message(page))
            self.responding = False
            return True
        return False

    def run(self):
        page = self.context.new_page()
        stealth_sync(page)
        self.context.add_cookies(self.cookies)
        print('przechodzę do openai')
        page.on('response', lambda r:self.response_filter(r, page))
        page.goto('https://chat.openai.com/')
        page.wait_for_selector('textarea[id="prompt-textarea"]')
        while True:
            if self.responding == False:
                page.locator('textarea[id="prompt-textarea"]').type(input('>>'))
                page.locator('button[data-testid="send-button"]').click()
            self.responding = True
            with page.expect_response('https://chat.openai.com/backend-api/lat/r', timeout=120000) as res_event:
                print(ChatBot.get_last_message(page))

def main():
    prepared_cookies = CookieManager.prepare_cookies(CookieManager.get_cookies())
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=True)
        bot = ChatBot(browser.new_context(), prepared_cookies)
        bot.run()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Zakończono chat')

"""Lotus login shell, with Frappe's original authentication and recovery flows."""
from html.parser import HTMLParser
from pathlib import Path
import frappe
from frappe.www.login import get_context as native_login_context

no_cache = True


class LoginStyles(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        href = attrs.get('href', '')
        if tag == 'link' and attrs.get('rel') == 'stylesheet' and href.startswith('/assets/lotus_farm/frontend/'):
            self.urls.append(href)


def login_text(value):
    return {
        'Sign In': 'Đăng nhập', 'Password': 'Mật khẩu', 'Continue': 'Đăng nhập',
        'Welcome! Please sign in to continue.': 'Đăng nhập để tiếp tục công việc.',
        'Forgot password?': 'Quên mật khẩu?', 'Forgot Password?': 'Quên mật khẩu?',
        'Login with Email Link': 'Đăng nhập qua email', 'Back to sign in': 'Quay lại đăng nhập',
        "Please enter your email, we'll send you password reset link": 'Nhập email để nhận liên kết đặt lại mật khẩu.',
        'Send Link': 'Gửi liên kết', 'Send login link': 'Gửi liên kết đăng nhập',
        'Login with password': 'Đăng nhập bằng mật khẩu',
        'Please check your email.': 'Vui lòng kiểm tra email.',
    }.get(value, frappe._(value))


def get_context(context):
    native_login_context(context)
    # Vite can emit a CSS-only entry as `file`, with shared CSS present only in
    # its generated HTML. Read those links so fonts/tokens always precede login styles.
    styles = LoginStyles()
    styles.feed(Path(frappe.get_app_path('lotus_farm', 'public', 'frontend', 'login.html')).read_text(encoding='utf8'))
    context.lotus_login_css = styles.urls
    context._ = login_text
    context.lang = 'vi'
    context.logo = '/assets/lotus_farm/images/lotus-agritech-header-v2.png'
    context.title = 'Đăng nhập · Lotus Agritech'
    context.no_header = True
    context.no_footer = True
    context.show_footer_on_login = False

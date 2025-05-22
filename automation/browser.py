from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

def get_driver(proxy='172.234.68.64:17468'):
    ip, port = proxy.split(":")

    profile = FirefoxProfile()

    # Настройки прокси
    profile.set_preference("network.proxy.type", 1)
    profile.set_preference("network.proxy.http", ip)
    profile.set_preference("network.proxy.http_port", int(port))
    profile.set_preference("network.proxy.ssl", ip)
    profile.set_preference("network.proxy.ssl_port", int(port))
    profile.set_preference("network.proxy.socks_remote_dns", True)

    options = Options()
    options.profile = profile

    driver = webdriver.Firefox(options=options)
    driver.set_window_size(1280, 1024)

    return driver

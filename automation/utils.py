import random
import string
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def generate_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(random.choice(chars) for _ in range(length))

def generate_name():
    first_names = ['John', 'Jane', 'Alex', 'Chris', 'Mike', 'Emily', 'Anna', 'David']
    last_names = ['Smith', 'Johnson', 'Brown', 'Lee', 'Walker', 'Miller', 'Taylor', 'Anderson']
    return random.choice(first_names), random.choice(last_names)

def wait_and_fill(driver, by, value, text, timeout=15):
    elem = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )
    elem.clear()
    elem.send_keys(text)

def wait_and_click(driver, by, value, timeout=15):
    elem = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, value))
    )
    elem.click()

def wait_for_element(driver, by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
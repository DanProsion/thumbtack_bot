from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, StaleElementReferenceException, ElementClickInterceptedException
)

def click_check_availability_button(driver, timeout=15):
    """
    Ищет и кликает на кнопку "Check availability" на странице.
    """
    try:
        # Ждём, пока появится кнопка с нужным текстом
        button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[.//span[contains(text(), 'Check availability')]]"
            ))
        )
        button.click()
        print("[✅] Кнопка 'Check availability' нажата.")
        return True

    except TimeoutException:
        print("[❌] Кнопка 'Check availability' не найдена за отведённое время.")
    except StaleElementReferenceException:
        print("[⚠️] Кнопка устарела. Попробуйте найти элемент заново.")
    except ElementClickInterceptedException:
        print("[⚠️] Кнопка не нажата. Возможно, она перекрыта другим элементом.")
    except Exception as e:
        print(f"[❌] Неизвестная ошибка при попытке кликнуть по кнопке: {e}")

    return False

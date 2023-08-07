import scrapy
from scrapy import Selector
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time


class CianSpider(scrapy.Spider):
    name = "cian"
    start_urls = [
        "https://kazan.cian.ru/cat.php?deal_type=sale&engine_version=2&offer_type=flat&p=1&region=4777&room1=1"
    ]

    current_url = 'https://kazan.cian.ru/cat.php?deal_type=sale&engine_version=2&offer_type=flat&p=1&region=4777&room1=1'

    # Выводим полученные результаты в формате JSON
    custom_settings = {
        'FEED_FORMAT': 'json',
        'FEED_URI': 'cian.json'
    }
    prev_page_number = 0

    def parse(self, response):
        # Получаем текущий номер страницы из адреса
        # Иногда url стартовой страницы может не содержать номер => присваиваем 1
        try:
            page_number = int(response.url.split('&p=')[1].split('&')[0])
        except IndexError:
            page_number = 1

        # Проверяем текущий номер страницы с номером прошлой страницы
        if page_number >= self.prev_page_number:
            self.prev_page_number = page_number
        else:
            # Если номер меньше - вызываем исключение и завершаем работу паука
            raise CloseSpider("Достигнут предел страниц")

        # Проверяем наличие контейнера с доп предложениями на странице (появляется только на последней странице)
        additional_block = response.xpath('//div[@data-name="Suggestions"]')
        # Если блок "Дополнительные предложения по Вашему запросу" найден
        if len(additional_block) != 0:
            response = self.click_more_button()

        # Получаем все карточки с объявлениями со страницы
        ads = response.xpath("//div[@class='_93444fe79c--content--lXy9G']").getall()

        # Извлекаем данные из каждой карточки
        for ad in ads:
            data = Selector(text=ad)
            try:
                addr_div = data.xpath("//div[@class='_93444fe79c--labels--L8WyJ']")
                addr = self.extract_address(addr_div)
            except:
                addr = None
            ad_data = {
                "title": data.xpath('//span[@data-mark="OfferTitle"]//span//text()').get(),
                "price": data.xpath('//span[@data-mark="MainPrice"]//span//text()').get(),
                "address": addr,
                "link": data.css('a._93444fe79c--link--eoxce::attr(href)').get(),
                "ad_page": page_number
            }
            yield ad_data

        # Переход на следующую страницу
        self.current_url = self.current_url.replace(f"p={page_number}", f"p={page_number + 1}")
        if self.current_url is not None:
            yield response.follow(self.current_url, self.parse)

    def extract_address(self, addr_div: Selector) -> str:
        """
        Объединяет адрес
        :param addr_div: элемент div содержащий адрес
        :return: строка с адресом
        """
        address_parts = addr_div.css('._93444fe79c--labels--L8WyJ a::text').getall()
        address = ', '.join(address_parts)
        return address

    def click_more_button(self) -> HtmlResponse:
        # При помощи Selenium работаем с кнопкой "Показать ещё"
        # Замените драйвер на свой
        driver = webdriver.Chrome()

        # Открыть текущую страницу
        driver.get(self.current_url)

        # Задержка на подгрузку страницы
        time.sleep(5)

        # Проверяем страницу на плашку о принятии куки (иначе не работает)
        try:
            accept_cookies_button = driver.find_element(By.XPATH, "//div[@data-name='CookiesNotification']"
                                                                  "//div[@class='_25d45facb5--button--CaFmg']")
            accept_cookies_button.click()
            time.sleep(2)
        except NoSuchElementException:
            pass

        while True:
            try:
                more_button = driver.find_element(By.CLASS_NAME, '_93444fe79c--moreSuggestionsButtonContainer--h0z5t')
                more_button.click()
                time.sleep(5)
            except:
                break

        # Обновляем содержимое ответа Scrapy
        body = driver.page_source
        url = driver.current_url
        response = HtmlResponse(url=url, body=body, encoding='utf-8')
        return response

    def closed(self, reason):
        # При завершении работы паука
        ...

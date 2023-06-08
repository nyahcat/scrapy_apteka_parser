"""
Запуск: ..\test_parse scrapy runspider test_parse\spiders\test-spider.py --output data.json -L WARNING
Изменены items.py, settings.py
"""

import scrapy
from test_parse.items import TestParseItem
import re
import time


class TestParser(scrapy.Spider):
    name = 'test_spider'
    # url-ы категорий
    start_urls = [
        'https://apteka-ot-sklada.ru/catalog/sredstva-gigieny/uhod-za-polostyu-rta/zubnye-niti_-ershiki',
        'https://apteka-ot-sklada.ru/catalog/sredstva-gigieny/uhod-za-polostyu-rta/opolaskivatel-dlya-rta',
        'https://apteka-ot-sklada.ru/catalog/sredstva-gigieny/uhod-za-polostyu-rta/pasty-zubnye-detskie'
    ]

    def parse(self, response):
        # Получаем url-ы товаров
        urls = response.xpath('//div[@class="goods-card__name text text_size_default text_weight_medium"]/a/@href').getall()

        # with open('test_site.txt', 'w', encoding='utf-8') as file:
        #     file.write(response.text)

        for url in urls:
            url = response.urljoin(url)
            yield scrapy.Request(url=url, cookies={'city': '92'}, callback=self.parse_data)  # Томск {'city':'92'}

        # Пагинация
        next_page_url = response.xpath('//li[@class="ui-pagination__item ui-pagination__item_next"]/a/@href').get()
        if next_page_url:
            next_page_url = response.urljoin(next_page_url)
            yield scrapy.Request(url=next_page_url, cookies={'city': '92'}, callback=self.parse)

    def parse_data(self, response):

        def get_rpc(url_text):
            """ С помощью RegEx получаем код товара из url """
            return re.search(r'(\d*)$', url_text).group()

        def get_price_dict(price_list):
            """ С помощью RegEx получаем список цен {list of float}, вычисляем скидку если есть """
            flag = len(price_list)
            current = original = float()
            sale_tag = ''
            if flag != 0:
                # ['\n        468.80 ₽\n      ', '\n        534.70 ₽\n      ']
                price_list = [float(re.search(r'\d*\.\d{2}', price).group()) for price in price_list]
                if flag == 2:
                    current = price_list[0]
                    original = price_list[1]
                    discount = round(100 - (current / original * 100), 2)
                    sale_tag = f'Скидка {discount}%'
                elif flag == 1:
                    current = original = price_list[0]
            return {'current': current, 'original': original, 'sale_tag': sale_tag}

        def get_images(img_list):
            """ Получаем ассеты, если фото-заглушка - оставляем пустое поле """
            if img_list:
                main_image = img_list[0] if not img_list[0].endswith('photo.jpg') else ''
                return {'main_image': main_image, 'set_images': img_list[:1] if len(img_list) > 1 else []}

        def get_description(descr_list):
            """  С помощью RegEx удаляем литералы """
            if descr_list:
                return re.sub(r'\s+', ' ', ' '.join(desription_list)).strip()


        item = TestParseItem()

        product_url = response.url

        item['timestamp'] = time.time()

        item['RPC'] = get_rpc(product_url)

        item['url'] = product_url

        item['title'] = response.xpath('//h1[@class="text text_size_display-1 text_weight_bold"]/span/text()').get(default='')

        item['brand'] = response.xpath('//div[@class="page-header__description"]/div/span[@itemtype="legalName"]/text()').get(default='')

        item['section'] = response.xpath('//li[@class="ui-breadcrumbs__item"]/a/span/span/text()').getall()

        price_data_list = response.xpath('//div[@class="goods-offer-panel__price"]/span/text()').getall()
        item['price_data'] = get_price_dict(price_data_list)

        item['stock'] = {'in_stock': True if price_data_list != [] else False, 'count': 0}

        img_urls_list = response.xpath('//ul[@class="goods-gallery__preview-list"]/li/div/img/@src').getall()
        if img_urls_list:
            img_urls_list = [response.urljoin(img_url) for img_url in img_urls_list]
        item['assets'] = get_images(img_urls_list)

        desription_list = response.xpath('//div[@class="custom-html content-text"]/p/text()').getall()
        item['metadata'] = {
            '__description': get_description(desription_list),
            'СТРАНА ПРОИЗВОДИТЕЛЬ': response.xpath('//div[@class="page-header__description"]/div/span[@itemtype="location"]/text()').get(default='')
        }
        yield item

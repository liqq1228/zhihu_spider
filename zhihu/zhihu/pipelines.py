# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import os

import requests
from pymongo import MongoClient
from scrapy import log

from zhihu.settings import MONGO_URI, PROJECT_DIR
from zhihu.items import ZhihuPeopleItem, ZhihuRelationItem


class ZhihuPipeline(object):
    """
    存储数据
    """
    def __init__(self, mongo_uri, mongo_db, image_dir):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.image_dir = image_dir
        self.client = None
        self.db= None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=MONGO_URI,
            mongo_db='zhihu',
            image_dir=os.path.join(PROJECT_DIR, 'images')
        )

    def open_spider(self, spider):
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        if not os.path.exists(self.image_dir):
            os.mkdir(self.image_dir)

    def close_spider(self, spider):
        self.client.close()

    def _download_image(self, image_url):
        """
        下载图片
        """
        try:
            image_name = os.path.split(image_url)[-1]
            image_path = os.path.join(self.image_dir, image_name)
            image = requests.get(image_url, stream=True)
            with open(image_path, 'wb') as img:
                img.write(image.content)
        except Exception as exc:
            log.ERROR(exc)

    def _process_people(self, item):
        """
        存储用户信息
        """
        collection = self.db['people']
        collection.update({'zhihu_id': item['zhihu_id']},
                          dict(item), upsert=True)

        image_url = item['image_url']
        if image_url:
            self._download_image(image_url)

    def _process_relation(self, item):
        """
        存储人际拓扑关系
        """
        collection = self.db['relation']

        data = collection.find_one({
            'zhihu_id': item['zhihu_id'],
            'user_type': item['user_type']})
        if not data:
            self.db['relation'].insert(dict(item))
        else:
            origin_list = data['user_list']
            new_list = item['user_list']
            data['user_list'] = list(set(origin_list) | set(new_list))
            collection.update({'zhihu_id': item['zhihu_id'],
                               'user_type': item['user_type']}, data)

    def process_item(self, item, spider):
        """
        处理item
        """
        if isinstance(item, ZhihuPeopleItem):
            self._process_people(item)
        elif isinstance(item, ZhihuRelationItem):
            self._process_relation(item)
        return item

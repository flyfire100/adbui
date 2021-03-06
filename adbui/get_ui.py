# coding=utf-8
import os
import sys
import re
from PIL import Image
from lxml import etree
from adbui.ocr import Ocr
from lxml.etree import tostring

short_keys = {'id': 'resource-id', 'class_': 'class', 'desc': 'content-desc'}


class GetUI(object):
    def __init__(self, adb_ext):
        self.__adb_ext = adb_ext
        self.xml = None
        self.ocr = None
        self.shape = None

    def init_ocr(self, app_id=None, secret_id=None, secret_key=None):
        self.ocr = Ocr(app_id, secret_id, secret_key)

    def init_shape(self):
        from adbui.shape import Shape
        self.shape = Shape()

    def get_ui_by_attr(self, is_contains=False, is_update=True, **kwargs):
        uis = self.get_uis_by_attr(is_contains=is_contains, is_update=is_update, **kwargs)
        return uis[0] if uis else None

    def get_uis_by_attr(self, is_contains=False, is_update=True, **kwargs):
        """
        通过节点的属性获取节点
        :param is_contains: 是否使用模糊查找
        :param is_update:
        :param kwargs:
        :return: 
        """
        for key in kwargs:
            if key in short_keys:
                kwargs[short_keys[key]] = kwargs.pop(key)
        if is_contains:
            s = list(map(lambda x: "contains(@{}, '{}')".format(x, kwargs[x]), kwargs))
            xpath = './/*[{}]'.format(' and '.join(s))
        else:
            s = list(map(lambda key: "[@{}='{}']".format(key, kwargs[key]), kwargs))
            xpath = './/*{}'.format(''.join(s))
        uis = self.get_uis_by_xpath(xpath, is_update=is_update)
        return uis

    def get_ui_by_xpath(self, xpath, is_update=True):
        uis = self.get_uis_by_xpath(xpath, is_update)
        return uis[0] if uis else None

    def get_uis_by_xpath(self, xpath, is_update=True):
        """
        通过xpath查找节点
        :param xpath: 
        :param is_update: 
        :return: 
        """
        if is_update:
            self.__adb_ext.dump()  # 获取xml文件
            self.__init_xml()
        xpath = xpath.decode('utf-8') if sys.version_info[0] < 3 else xpath
        elements = self.xml.xpath(xpath)
        uis = []
        for element in elements:
            uis.append(self.get_ui_by_element(element))
        return uis

    def get_ui_by_element(self, element):
        bounds = element.get('bounds')
        x1, y1, x2, y2 = re.compile(r"-?\d+").findall(bounds)
        ui = UI(self.__adb_ext, x1, y1, x2, y2, int(x2) - int(x1), int(y2) - int(y1))
        ui.element = element
        return ui

    def get_ui_by_ocr(self, text, min_hit=None, is_update=True):
        uis = self.get_uis_by_ocr(text, min_hit, is_update)
        return uis[0] if uis else None

    def get_uis_by_ocr(self, text, min_hit=None, is_update=True):
        """
        通过ocr识别获取节点
        :param text: 查找的文本
        :param min_hit: 设置查找文本的最小匹配数量
        :param is_update: 是否重新获取截图
        :return: 
        """
        if self.ocr is None:
            raise NameError('ocr is not init.how init find at https://github.com/hao1032/adbui')
        if is_update:
            self.__adb_ext.screenshot()  # 获取截图
        image_jpg = self.__get_image_jpg()
        ocr_result = self.ocr.get_result_image(image_jpg)
        text_list = list(text)
        min_hit = min_hit if min_hit else len(text_list)  # 如果min hit没有指定，使用min text的长度
        uis = []
        for item in ocr_result['items']:
            same_count = 0
            item_string = item['itemstring']
            item_string_list = list(item_string)

            # 计算 text_list 和 item_string_list 中相同元素的数量
            for char in text_list:
                if char in item_string_list:
                    item_string_list.pop(item_string_list.index(char))
                    same_count += 1

            if same_count >= min_hit:
                item_coord = item['itemcoord']
                ui = UI(self.__adb_ext, item_coord['x'], item_coord['y'],
                        item_coord['x'] + item_coord['width'], item_coord['y'] + item_coord['height'],
                        item_coord['width'], item_coord['height'])
                ui.text = item_string
                uis.append(ui)
        return uis

    def get_text_by_ocr(self, ui=None, rect=None, is_update=False):
        pass

    def get_ui_by_shape(self, width_range, height_range, box=None):
        uis = self.get_uis_by_shape(width_range, height_range, box)
        return uis[0] if uis else None

    def get_uis_by_shape(self, width_range, height_range, box=None):
        self.__adb_ext.screenshot()  # 获取截图
        jpg_img = self.__get_image_jpg()
        if box:
            jpg_img = jpg_img.crop(box)
        rectangles = self.shape.get_rectangle(jpg_img, width_range, height_range)
        uis = []
        for x1, y1, x2, y2, width, height in rectangles:
            ui = UI(self.__adb_ext, x1, y1, x2, y2, width, height)
            uis.append(ui)
        return uis

    def __get_image_jpg(self):
        img_path = '{}.png'.format(self.__adb_ext.get_pc_temp_name())
        return Image.open(img_path).convert('RGB')

    def __init_xml(self):
        xml_path = '{}.xml'.format(self.__adb_ext.get_pc_temp_name())
        self.xml = etree.parse(xml_path)

        for element in self.xml.findall('.//node'):
            element.tag = element.get('class').split('.')[-1]  # 将每个node的name替换为class值，和uiautomator里显示的一致


class UI:
    def __init__(self, adb_ext, x1, y1, x2, y2, width, height):
        self.__adb_ext = adb_ext
        self.x1 = int(x1)
        self.y1 = int(y1)
        self.x2 = int(x2)
        self.y2 = int(y2)
        self.width = int(width)
        self.height = int(height)
        self.text = None
        self.element = None

    def get_element_str(self):
        return tostring(self.element)

    def get_value(self, key):
        if key in short_keys:
            key = short_keys[key]
        return self.element.get(key)

    def click(self):
        x = self.x1 + int(self.width / 2)
        y = self.y1 + int(self.height / 2)
        self.__adb_ext.click(x, y)

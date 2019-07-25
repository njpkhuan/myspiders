# -*- coding: utf-8 -*-
import linecache
import sys
import urllib
from urllib import request
from scrapy import Request
import scrapy

from myspiders.spiders.chaojiying import Chaojiying_Client

from myspiders.spiders.VerifyCodeRecognition import VerifyCodeRecognition


class BankquerySpider(scrapy.Spider):
    name = 'bankquery'
    allowed_domains = ['hebbank.com']
    start_urls = ['https://www.hebbank.com/corporbank/otherBankQueryWeb.do', ]
    # 文件地址
    success_path = "../result/banks.txt"
    error_path = "../result/errors.txt"
    error_path_2 = "../result/errors2.txt"
    code_path = "../result/a.png"
    source_path = "../result/city.txt"

    def start_requests(self):
        yield Request("https://www.hebbank.com/corporbank/otherBankQueryWeb.do",
                      meta={'cookiejar': 1, "current_line": 1},
                      dont_filter=True,
                      callback=self.parse3)

    def parse(self, response):
        # 读取最大行数
        line_num = len(open(self.source_path, "r").readlines())
        # 当前读取行数
        current_line = response.meta['current_line']
        # 判断文件是否读取完毕
        if current_line > line_num:
            sys.exit()
        # 读取当前行数据  数据格式:  省号   票据类型号   城市号
        position = linecache.getline(self.source_path, current_line)
        # 累加器+1
        current_line = current_line + 1
        # 将当前行数据切分  [省号,票据类型号,城市号]
        pos = position.split("\t")
        # 判断当前行是否是空数据  []
        if len(pos) == 1:
            # 迭代下一行数据
            yield Request("https://www.hebbank.com/corporbank/otherBankQueryWeb.do",
                          meta={'cookiejar': 1, "current_line": current_line},
                          dont_filter=True,
                          callback=self.parse)
        # 获取银行类型号
        bankType = pos[1].strip()
        # 获取城市号
        cityCode = pos[2].strip()[:-2]
        # 指定验证码URL
        url = "https://www.hebbank.com/corporbank/VerifyImage?update=0.8890144688545829"
        # 下载验证码并保存到本地
        res = urllib.request.urlretrieve(url, filename=self.code_path)
        # 获取验证码session地址
        new_session = res[1]['Set-Cookie'].split(';')[0]
        # # 解析验证码:用第三方工具"超级鹰"
        # chaojiying = Chaojiying_Client('njpkhuan', 'huan9420', '899120')
        # # 读取验证码本地地址
        # im = open(self.code_path, 'rb').read()
        # # 解析验证码并接收结果
        # res = chaojiying.PostPic(im, 1902)
        # 使用百度OCR文本识别
        v = VerifyCodeRecognition()
        captcha_value = v.recognize_image()
        # 判断验证码是否解析成功
        if captcha_value is not None:
            # 拼凑查询承兑行验证码
            url = "https://www.hebbank.com/corporbank/webBankQueryAjax.do?checkCode=" + captcha_value + "&bankType=" + bankType + "&cityCode=" + cityCode
            # 打印URL
            print(url)
            # 查询承兑行信息
            yield scrapy.Request(
                # 指定URL
                url,
                # 指定session
                cookies={new_session.split('=')[0]: new_session.split('=')[1]},
                # 指定参数
                meta={"current_line": current_line},
                # 指定回调函数
                callback=self.parse_page,
                # 指定禁止过滤
                dont_filter=True
            )
        else:
            # 打开错误输出文件
            error = open(self.error_path, "ab")
            # 将错误信息写到文件中 数据格式：bankType  cityCode
            error.write(position.encode("utf-8"))
            # 关闭文件流
            error.close()
            # 迭代下一行数据
            yield Request("https://www.hebbank.com/corporbank/otherBankQueryWeb.do",
                          meta={'cookiejar': 1, "current_line": current_line},
                          dont_filter=True,
                          callback=self.parse3)

    # 解析查询结果
    def parse_page(self, response):
        # 接收当前行号
        current_line = response.meta['current_line']
        # 获取承兑行信息
        bankInfo = response.xpath("//*[@id='bankName']/@value").extract()
        # 判断数据是否存在
        if bankInfo:
            # 打开输出文件
            content = open(self.success_path, "ab")
            # 获取当前行数据
            pos = linecache.getline(self.source_path, current_line - 1)
            # 将 数据格式： 省号   票据类型号   城市号写入到结果文件中
            content.write(("num:" + pos + "\r\n").encode("utf-8"))
            # 将查询到的数据写入到文件中
            for b in bankInfo:
                content.write((b + "\r\n").encode("utf-8"))
        else:
            # 获取当前行数据
            position = linecache.getline(self.source_path, current_line - 1)
            # 将当前行数据切分  [省号,票据类型号,城市号]
            pos = position.split("\t")
            # 获取银行类型号
            bankType = pos[1].strip()
            # 获取城市号
            cityCode = pos[2].strip()[:-2]
            # 打开错误输出文件
            content = open(self.error_path, "ab")
            # 将错误信息写入到文件中
            content.write(position.encode("utf-8"))
        content.close()
        # 迭代下一行数据
        yield Request("https://www.hebbank.com/corporbank/otherBankQueryWeb.do",
                      meta={'cookiejar': 1, "current_line": current_line},
                      dont_filter=True,
                      callback=self.parse)

    def parse2(self, response):
        # 银行类型
        bankTypes = []
        # 省份
        provinces = []
        # 开始获取银行类型
        context = response.xpath("//*[@id='bankTypeSelect']/option/@value")
        bank = context.extract()
        for b in bank:
            bankTypes.append(b.strip())
        print(bank)

        # 开始获取省份
        context = response.xpath("//*[@id='provinceSelect']/option/@value")
        provinces = context.extract()

        # 开始获取城市
        for province in provinces:
            for bankType in bankTypes:
                yield scrapy.FormRequest(
                    url="https://www.hebbank.com/corporbank/cityQueryAjax.do?",
                    formdata={"provinceCode": province, "bankType": bankType},
                    meta={"province": province, "bankType": bankType},
                    callback=self.parse_page2
                )

    def parse_page2(self, response):
        citys = []
        province = response.meta['province']
        bankType = response.meta['bankType']
        # 开始获取城市
        context = response.xpath("//*[@id='cityCode']/@value").extract()
        # 过滤掉空的城市
        if len(context) == 0:
            return
        else:
            citys = context
        f = open(self.source_path, "ab")
        for city in citys:
            if bankType == "-1":
                if city != "857000":
                    f.write((province + "\t" + bankType + "\t" + city + "\r\n").encode("utf-8"))
        f.close()

    def parse3(self, response):
        # 读取最大行数
        line_num = len(open(self.error_path, "r").readlines())
        # 当前读取行数
        current_line = response.meta['current_line']
        # 判断文件是否读取完毕
        if current_line > line_num:
            sys.exit()
        # 读取当前行数据  数据格式:  省号   票据类型号   城市号
        position = linecache.getline(self.error_path, current_line)
        # 累加器+1
        current_line = current_line + 1
        # 将当前行数据切分  [省号,票据类型号,城市号]
        pos = position.split("\t")
        # 判断当前行是否是空数据  []
        if len(pos) < 3:
            # 迭代下一行数据
            yield Request("https://www.hebbank.com/corporbank/otherBankQueryWeb.do",
                          meta={'cookiejar': 1, "current_line": current_line},
                          dont_filter=True,
                          callback=self.parse3)
        # 获取银行类型号
        bankType = pos[1].strip()
        # 获取城市号
        cityCode = pos[2].strip()[:-2]
        # 指定验证码URL
        url = "https://www.hebbank.com/corporbank/VerifyImage?update=0.8890144688545829"
        # 下载验证码并保存到本地
        res = urllib.request.urlretrieve(url, filename=self.code_path)
        # 获取验证码session地址
        new_session = res[1]['Set-Cookie'].split(';')[0]
        # 解析验证码:用第三方工具"超级鹰"
        # chaojiying = Chaojiying_Client('njpkhuan', 'l9*P2&7UzRRs', '899120')
        # 读取验证码本地地址
        # im = open(self.code_path, 'rb').read()
        # 解析验证码并接收结果
        # res = chaojiying.PostPic(im, 1902)

        # 使用百度OCR文本识别
        v = VerifyCodeRecognition()
        captcha_value = v.recognize_image()
        # 判断验证码是否解析成功
        if captcha_value is not None:
            # 拼凑查询承兑行验证码
            url = "https://www.hebbank.com/corporbank/webBankQueryAjax.do?checkCode=" + captcha_value + "&bankType=" + bankType + "&cityCode=" + cityCode
            # 打印URL
            print(url)
            # 查询承兑行信息
            yield scrapy.Request(
                # 指定URL
                url,
                # 指定session
                cookies={new_session.split('=')[0]: new_session.split('=')[1]},
                # 指定参数
                meta={"current_line": current_line},
                # 指定回调函数
                callback=self.parse_page3,
                # 指定禁止过滤
                dont_filter=True
            )
        else:
            # 打开错误输出文件
            error = open(self.error_path_2, "ab")
            # 将错误信息写到文件中 数据格式：bankType  cityCode
            error.write((position).encode("utf-8"))
            # 关闭文件流
            error.close()
            # 迭代下一行数据
            yield Request("https://www.hebbank.com/corporbank/otherBankQueryWeb.do",
                          meta={'cookiejar': 1, "current_line": current_line},
                          dont_filter=True,
                          callback=self.parse3)

        # 解析查询结果

    def parse_page3(self, response):
        # 接收当前行号
        current_line = response.meta['current_line']
        # 获取承兑行信息
        bankInfo = response.xpath("//*[@id='bankName']/@value").extract()
        # 判断数据是否存在
        if bankInfo:
            # 打开输出文件
            content = open(self.success_path, "ab")
            # 获取当前行数据
            pos = linecache.getline(self.error_path, current_line - 1)
            # 将 数据格式： 省号   票据类型号   城市号写入到结果文件中
            content.write(("num:" + pos + "\r\n").encode("utf-8"))
            # 将查询到的数据写入到文件中
            for b in bankInfo:
                content.write((b + "\r\n").encode("utf-8"))
        else:
            # 获取当前行数据
            position = linecache.getline(self.error_path, current_line - 1)
            # 打开错误输出文件
            content = open(self.error_path_2, "ab")
            # 将错误信息写入到文件中
            content.write((position).encode("utf-8"))
        content.close()
        # 迭代下一行数据
        yield Request("https://www.hebbank.com/corporbank/otherBankQueryWeb.do",
                      meta={'cookiejar': 1, "current_line": current_line},
                      dont_filter=True,
                      callback=self.parse3)

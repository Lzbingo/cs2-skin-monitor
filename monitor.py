#!/usr/bin/env python3
import requests
import os
import json
import smtplib
from email.mime.text import MimeText
from datetime import datetime
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BuffSkinMonitor:
    def __init__(self):
        # 从环境变量获取配置
        self.skin_name = os.getenv('SKIN_NAME', '熊刀')
        self.target_price = float(os.getenv('TARGET_PRICE', '400'))
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.qq.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '465'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.notify_email = os.getenv('NOTIFY_EMAIL', '')
        
        # Buff API配置
        self.buff_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://buff.163.com/',
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.buff_headers)
    
    def search_skin_id(self, skin_name):
        """
        搜索熊刀的商品ID
        """
        try:
            search_url = "https://buff.163.com/api/market/goods"
            params = {
                'game': 'csgo',
                'page_num': '1',
                'search': skin_name,
            }
            
            response = self.session.get(search_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data['code'] == 'OK' and data['data']['items']:
                    # 寻找最匹配的熊刀
                    for item in data['data']['items']:
                        if '熊刀' in item['name'] or 'Ursus' in item['name']:
                            return {
                                'goods_id': item['id'],
                                'name': item['name'],
                                'short_name': item['short_name']
                            }
            
            logger.error(f"未找到皮肤: {skin_name}")
            return None
            
        except Exception as e:
            logger.error(f"搜索皮肤ID失败: {e}")
            return None
    
    def get_buff_price(self, goods_id):
        """
        获取Buff上的最低售价
        """
        try:
            price_url = "https://buff.163.com/api/market/goods/sell_order"
            params = {
                'game': 'csgo',
                'goods_id': goods_id,
                'page_num': '1',
            }
            
            response = self.session.get(price_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data['code'] == 'OK' and data['data']['items']:
                    # 获取最低价格的订单
                    lowest_order = data['data']['items'][0]
                    price = float(lowest_order['price'])
                    return price
            
            logger.error(f"获取价格失败，商品ID: {goods_id}")
            return None
            
        except Exception as e:
            logger.error(f"获取Buff价格失败: {e}")
            return None
    
    def get_current_price(self):
        """
        主函数：获取当前熊刀价格
        """
        logger.info(f"开始搜索皮肤: {self.skin_name}")
        
        # 第一步：搜索皮肤获取商品ID
        skin_info = self.search_skin_id(self.skin_name)
        if not skin_info:
            logger.error("无法找到熊刀信息")
            return None
        
        logger.info(f"找到皮肤: {skin_info['name']} (ID: {skin_info['goods_id']})")
        
        # 第二步：通过商品ID获取价格
        current_price = self.get_buff_price(skin_info['goods_id'])
        
        if current_price:
            logger.info(f"熊刀当前价格: ¥{current_price}")
            return current_price
        else:
            return None
    
    def send_notification(self, current_price, skin_name):
        """发送价格提醒邮件"""
        try:
            subject = f'🚨 熊刀价格提醒！当前价格: ¥{current_price}'
            body = f"""
            您好！
            
            好消息！您监控的熊刀当前价格为: ¥{current_price}
            已低于您设置的目标价格: ¥{self.target_price}
            
            🎯 达到购买时机！
            
            购买链接: https://buff.163.com/market/csgo
            监控时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            ---
            Buff熊刀价格监控机器人 自动发送
            """
            
            msg = MimeText(body, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = self.notify_email
            
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"价格提醒邮件已发送！当前价格: ¥{current_price}")
            return True
            
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return False
    
    def run(self):
        """执行监控"""
        logger.info(f"开始监控熊刀价格，目标价格: ¥{self.target_price}")
        
        current_price = self.get_current_price()
        
        if current_price is None:
            logger.error("无法获取价格，任务结束")
            return
        
        # 记录价格历史
        history_file = 'price_history.json'
        history_data = []
        
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                try:
                    history_data = json.load(f)
                except:
                    history_data = []
        
        history_data.append({
            'timestamp': datetime.now().isoformat(),
            'price': current_price,
            'skin': self.skin_name,
            'source': 'Buff'
        })
        
        # 只保留最近100条记录
        if len(history_data) > 100:
            history_data = history_data[-100:]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        
        # 检查价格是否达到目标
        if current_price <= self.target_price:
            logger.info(f"🎯 价格达到目标！当前价格 ¥{current_price} <= 目标价格 ¥{self.target_price}")
            self.send_notification(current_price, self.skin_name)
        else:
            logger.info(f"价格未达目标，当前价格 ¥{current_price} > 目标价格 ¥{self.target_price}")

if __name__ == "__main__":
    monitor = BuffSkinMonitor()
    monitor.run()

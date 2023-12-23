# encoding:utf-8
import re
from concurrent.futures import ThreadPoolExecutor
import itchat
import requests
from bs4 import BeautifulSoup
from itchat.content import *
import logging
import google.generativeai as genai
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
genai.configure(api_key=os.environ['API_KEY'], transport="rest")
model = genai.GenerativeModel('gemini-pro')

def ripPost(url:str):
    response=requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    elements = [
        element.text for element in soup.find_all(["title", "h1", "h2", "h3", "li", "p", "a"])
        if len(element.text) > 5
    ]
    txt = ' '.join(elements).replace('  ','')
    if len('\n'.join(txt)) == 0:
        txt = re.sub(r'\\x[0-9a-fA-F]{2}', '',
                           soup.find('meta', {'name': 'description'}).attrs['content'])
    return txt

@itchat.msg_register([TEXT, SHARING])
def handler_single_msg(msg):
    weChat().handle(msg)
    return None

@itchat.msg_register([TEXT, SHARING], isGroupChat=True)
def handler_group_msg(msg):
    weChat().handle_group(msg)
    return None

class weChat():
    def __init__(self):
        pass
    def startup(self):
        # login by scan QRCode
        itchat.auto_login(hotReload=True)
        # start message listener
        itchat.run()

    def handle(self, msg):
        if msg['MsgType']==49:
            thread_pool.submit(self._do_send, ripPost(msg['Url'])+'\nTLDR;用中文总结要点', msg['FromUserName'])
            return
        if msg['Text'].startswith('！') or msg['Text'].startswith('! '):
            thread_pool.submit(self._do_send, msg['Text'],msg['FromUserName'])
        else:
            thread_pool.submit(self.send,'自动回复中，如需要和G聊天，请以感叹号加空格开头，如『! 请自我介绍』',msg['FromUserName'])

    def handle_group(self, msg):
        group_name = msg['User'].get('NickName', None)
        if msg['MsgType']==49 and group_name in os.environ['GROUP'].replace('，',',').split(','):
            thread_pool.submit(self._do_send, ripPost(msg['Url'])+'\nTLDR;用中文总结要点', msg['FromUserName'])
            return
        elif not msg['IsAt']:
            return
        query = msg['Content'][len(msg['ActualNickName']) + 1:]
        if query is not None:
            thread_pool.submit(self._do_send_group, query, msg)

    def send(self, msg, receiver):
        itchat.send(msg, toUserName=receiver)

    def _do_send(self, query,reply_user_id):
        if query == '':
            return
        try:
            reply_text = self.reply(query)
            if reply_text is not None:
                self.send('G:' + reply_text,reply_user_id)
        except Exception as e:
            log.exception(e)

    def _do_send_group(self, query, msg):
        if not query:
            return
        group_id = msg['User']['UserName']
        reply_text = self.reply(query)
        if reply_text is not None:
            self.send('@' + msg['ActualNickName'] + ' ' + reply_text.strip(), group_id)

    def reply(self,queryText):
        return model.generate_content(queryText).text

if __name__=='__main__':
    thread_pool = ThreadPoolExecutor(max_workers=8)
    log = logging.getLogger('itchat')
    log.setLevel(logging.DEBUG)
    wechat = weChat()
    wechat.startup()
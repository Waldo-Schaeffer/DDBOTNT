# -- coding: utf-8 --**
import yaml #pip install pyyaml
import json, requests, math, time, sys, base64
import os, logging  #日志系统
import pymysql
from dbutils.pooled_db import PooledDB
# 忽略mysql警告
from warnings import filterwarnings
filterwarnings('ignore', category=pymysql.Warning)

#日志系统
if not os.path.exists('logs'):
    os.makedirs('logs')
log_name = 'logs/' + time.strftime("%Y-%m-%d", time.localtime()) + '.log'  # 记录日志名
logging.basicConfig(format='%(asctime)s %(message)s', encoding='utf-8',
                     level=logging.ERROR, force=True)
"""
使用方法：

改日志文件名（比如换日期）：
logging.basicConfig(filename=log_name, format='%(asctime)s %(message)s', 
                        encoding='utf-8', level=logging.INFO, force=True)

输出日志：
logging.info('要输出的内容')

"""

def yaml_to_json(filepath):
    """
    读取 YAML 文件并将其转换为 JSON 对象。

    参数:
    filepath (str): YAML 文件的路径

    返回:
    dict: 代表 JSON 对象的 Python 字典
    """
    # 读取 YAML 文件
    with open(filepath, 'r', encoding='utf-8') as file:
        yaml_content = yaml.safe_load(file)

    # 转换为 JSON 格式（这里其实是 Python 的 dict 格式，但可被视为 JSON 结构）
    json_content = json.dumps(yaml_content, indent=4)

    # 打印 JSON 结果，可选
    #print(json_content)

    # 直接返回字典
    return yaml_content

class QQBotInfo:
    # todo 在调用QQ函数的时候，增加类似B站的容错，这样就可以保证QQ服务器不在127.0.0.1的时候，也能稳定运行
    def __init__(self, base_url, api_key):
        """
        初始化QQ机器人信息类。

        参数:
        base_url (str): API 请求的基础 URL
        api_key (str): 用于API请求的秘钥
        """
        self.base_url = base_url
        self.session = requests.Session()  # 创建session实例
        self.session.headers.update({
            'Authorization': f'{api_key}',
            'Content-Type': 'application/json'
        })

    def send_bot_api_request(self, api_name, method="GET", params=None, data=None):
        """
        向B站API发送统一的HTTP请求。
        参数:
        api_name (str): API的名称。
        method (str): 请求使用的方法，如'GET'、'POST'等。
        params (dict, optional): URL参数，用于GET请求。
        data (dict, optional): 请求体数据，用于POST请求。
        返回:
        dict: API响应转换成的字典。
        """
        url = f"{self.base_url}/{api_name}"
        method = method.upper()  # 转换为大写字母
        if method not in ["GET","POST"]:
            raise ValueError("提供的 HTTP 方法不受支持，目前只支持POST和GET")
        while True:
            # 发送请求和处理连接错误
            try:
                # 使用session发送请求
                if method == "GET":
                    response = self.session.get(url, params=params)
                elif method == "POST":
                    response = self.session.post(url, json=data)
            except requests.exceptions.ConnectionError as e:
                print("连接错误，可能是服务器关闭了连接，10秒后重试")
                print(f"错误详情：{e}")
                time.sleep(10)
                continue
            except requests.RequestException as e:
                print(f"请求发送失败：{e}，10秒后重试")
                time.sleep(10)
                continue
            
            try:
                res_json = response.json()
            except json.JSONDecodeError:
                if response.status_code == 403:
                    sys.exit("程序出错，请检查headers中的Authorization的值，和QQ设置面板中的api key是否一致")
                elif response.status_code >= 400:
                    print(url,method,params,data)
                    sys.exit(f"服务器错误,LLONEBOT返回错误代码：{response.status_code}")
                else:
                    print("无法解析JSON，响应内容为:", response.text)  # 打印响应内容
                    print(url,method,params,data)
                    sys.exit()
            #200 {"status":"failed","retcode":200,"data":null,"message":"Error: Timeout: NTEvent EventName:NodeIKernelMsgService/sendMsg ListenerName:NodeIKernelMsgListener/onMsgInfoListUpdate EventRet:\n{}\n","wording":"Error: Timeout: NTEvent EventName:NodeIKernelMsgService/sendMsg ListenerName:NodeIKernelMsgListener/onMsgInfoListUpdate EventRet:\n{}\n","echo":null}
            #200 {"status":"ok","retcode":0,"data":{"message_id":-2146736417},"message":"","wording":"","echo":null}
            
            if res_json["status"].lower() in ["ok","failed"] :
                return res_json
            elif response.status_code == 200:
                return res_json
            else:
                print("这个返回的值为什么会触发这个if分支呢？：", res_json)
                return res_json
    
    def send_group_message(self, raw_message):
        """
        发送群消息。

        参数:
        raw_message (str): 发送的消息原始内容

        返回:
        response: 发送消息的响应对象
        """
        url = f"{self.base_url}/send_group_msg"
        response = self.send_bot_api_request(api_name="send_group_msg", method="POST", data=raw_message)  # 使用json参数而不是data
        return response

    def get_bot_account_info(self):
        """
        获取机器人账号的基本信息。

        返回:
        - dict: 包含机器人账号信息的字典，例如用户名、用户ID、状态等。
        """
        return self.send_bot_api_request(api_name="get_login_info")

    def get_qq_friends_list(self):
        """
        获取QQ机器人的好友列表。

        返回:
        - list: 包含好友详细信息的列表，每个元素是一个字典，包含好友的名称、ID等信息。
        """
        return self.send_bot_api_request(api_name="get_friend_list")

    def get_qq_groups_list(self):
        """
        获取QQ机器人所在的群列表。

        返回:
        - list: 包含群组详细信息的列表，每个元素是一个字典，包含群组的名称、ID等信息。
        """
        return self.send_bot_api_request(api_name="get_group_list")

    def 发送下播通知(self, group_id, anchor_name, cover_visual_url):
        """
        发送下播提醒到指定的QQ群。

        参数:
        - group_id (int): QQ群号，消息发送的目标群。
        - anchor_name (str): 主播的昵称，将在消息中提及。
        - cover_visual_url (str): 直播间封面图的URL，用于在消息中显示图像。

        功能描述:
        该函数构造一个包括主播的昵称和封面图像URL的消息，
        并发送到指定的QQ群中，用于提醒群成员直播已经结束。
        """
        #cover_visual_url = 'https://i0.hdslb.com/bfs/live/526d56bbf23304860701061f8b789b5f0ff6e3a7.png' if cover_visual_url == '' else cover_visual_url
        if cover_visual_url == '':
            cover_visual = ''
        else:
            cover_visual = f"[CQ:image,file={cover_visual_url}]"
        raw_message = {
            "group_id": group_id,
            "message": f"{anchor_name}直播结束了\r\n{cover_visual}"
        }
        
        return self.send_group_message(raw_message)
    
    def 发送开播通知(self, group_id, anchor_name, live_title, room_number, cover_visual_url,at_list=None, at_all=False):
        """
        发送开播提醒到指定的QQ群。

        参数:
        - group_id (int): QQ群号，消息发送的目标群。
        - anchor_name (str): 主播的昵称，将在消息中提及。
        - live_title (str): 直播间的标题，描述直播内容。
        - room_number (int): 直播间的房间号，可以用于生成直播间的链接。
        - cover_visual_url (str): 直播间封面图的URL，用于在消息中显示图像。

        功能描述:
        该函数构造一个包括主播的昵称、直播标题、直播房间号和封面图像URL的消息，
        并发送到指定的QQ群中，用于提醒群成员关注直播。
        """
        if cover_visual_url == '':
            cover_visual = ''
        else:
            cover_visual = f"[CQ:image,file={cover_visual_url}]"
        message_content = f"{anchor_name}正在直播【{live_title}】\r\nhttps://live.bilibili.com/{room_number}\r\n{cover_visual}"
        if at_all:
            message_content = "[CQ:at,qq=all] " + message_content
        elif at_list:
            message_content = ''.join([f"[CQ:at,qq={qq}] " for qq in json.loads(at_list)]) + message_content

        raw_message = {
            "group_id": group_id,
            "message": message_content
        }
        
        return self.send_group_message(raw_message)

class BilibiliMain:
    def __init__(self, session):
        """
        初始化 BilibiliMain 类。

        参数:
        session (requests.Session): 预配置的会话对象，用于进行所有API请求。
        """
        self.session = session
        self.base_url = "https://api.bilibili.com"

    def send_bilibili_api_request(self, endpoint, method, params=None, data=None):
        """
        向B站API发送统一的HTTP请求。
        参数:
        endpoint (str): API的终点URL。
        method (str): 请求使用的方法，如'GET'、'POST'等。
        params (dict, optional): URL参数，用于GET请求。
        data (dict, optional): 请求体数据，用于POST请求。
        返回:
        dict: API响应转换成的字典。
        """
        url = f"{self.base_url}{endpoint}"
        method = method.upper()  # 转换为大写字母
        if method not in ["GET","POST"]:
            raise ValueError("提供的 HTTP 方法不受支持，目前只支持POST和GET")
        while True:
            # 发送请求和处理连接错误
            try:
                if method == "GET":
                    response = self.session.get(url, params=params)
                elif method == "POST":
                    response = self.session.post(url, data=data)
            except requests.exceptions.ConnectionError as e:
                print("连接错误，可能是服务器关闭了连接，10秒后重试")
                print(f"错误详情：{e}")
                time.sleep(10)
                continue
            except requests.RequestException as e:
                print(f"请求发送失败：{e}，10秒后重试")
                time.sleep(10)
                continue
            
            # 处理B站服务器返回数据和B站服务器故障解决方案
            try:
                res_json = response.json()
            except json.JSONDecodeError:
                if response.status_code in [502, 500]:
                    print(f"服务器错误,B站返回错误代码：{response.status_code}，60秒后重试")
                    time.sleep(60)
                    continue
                else:
                    print("无法解析JSON，响应内容为:", response.text)  # 打印响应内容
                    print(url,method,params,data)
                    sys.exit()
            
            # 处理API响应
            if res_json['code'] == 0:
                return res_json
            elif res_json['code'] in [-504, -502, -500]:  # 使用in判断多个错误代码
                print(f"服务调用错误，错误代码：{res_json['code']}，3秒后重试")
                time.sleep(3)
                continue
            elif res_json['code'] == -101:
                sys.exit("B站返回账号未登陆-101，请检查配置文件，机器人已退出")
            elif res_json['code'] == -412:
                print(f"请求B站过于频繁，ip被ban了：{res_json}，300秒后重试")
                time.sleep(300)
                continue
            elif res_json['code'] == -400:
                pass
                time.sleep(3)
                continue
                #{'code': -400, 'message': "Key: 'MultiGetRoomNewsReq.RoomIds' Error:Field validation for 'RoomIds' failed on the 'required' tag", 'ttl': 1, 'data': {'title': '哔哩哔哩直播 - 我的关注', 'pageSize': 10, 'totalPage': 12, 'list': [], 'count': 119, 'never_lived_count': 10, 'live_count': 0, 'never_lived_faces': []}}
            else:
                print(url,params,data)
                sys.exit(f"异常情况，请将B站返回信息提交issus，B站返回信息：{res_json}")
                

    def send_bilibili_live_api_request(self, endpoint, method, params=None, data=None):
        """
        向B站API发送统一的HTTP请求。
        参数:
        endpoint (str): API的终点URL。
        method (str): 请求使用的方法，如'GET'、'POST'等。
        params (dict, optional): URL参数，用于GET请求。
        data (dict, optional): 请求体数据，用于POST请求。
        返回:
        dict: API响应转换成的字典。
        """
        url = f"https://api.live.bilibili.com{endpoint}"
        method = method.upper()  # 转换为大写字母
        if method not in ["GET","POST"]:
            raise ValueError("提供的 HTTP 方法不受支持，目前只支持POST和GET")
        while True:
            # 发送请求和处理连接错误
            try:
                if method == "GET":
                    response = self.session.get(url, params=params)
                elif method == "POST":
                    response = self.session.post(url, data=data)
            except requests.exceptions.ConnectionError as e:
                print("连接错误，可能是服务器关闭了连接，10秒后重试")
                print(f"错误详情：{e}")
                time.sleep(10)
                continue
            except requests.RequestException as e:
                print(f"请求发送失败：{e}，10秒后重试")
                time.sleep(10)
                continue
            
            # 处理B站服务器返回数据和B站服务器故障解决方
            try:
                res_json = response.json()
            except json.JSONDecodeError:
                if response.status_code in [502, 500]:
                    print(f"服务器错误,B站返回错误代码：{response.status_code}，60秒后重试")
                    time.sleep(60)
                    continue
                else:
                    print("无法解析JSON，响应内容为:", response.text)
                    print(url, method, params, data)
                    sys.exit()
            
            # 处理API响应
            if res_json['code'] == 0:
                return res_json
            elif res_json['code'] in [-504, -502, -500]:  # 使用in判断多个错误代码
                print(f"服务调用错误，错误代码：{res_json['code']}，3秒后重试")
                time.sleep(3)
                continue
            elif res_json['code'] == -101:
                sys.exit("B站返回账号未登陆-101，请检查配置文件，机器人已退出")
            elif res_json['code'] == -412:
                print(f"请求B站过于频繁，ip被ban了：{res_json}，300秒后重试")
                time.sleep(300)
                continue
            elif res_json['code'] == -400:
                time.sleep(3)
                continue
            else:
                sys.exit(f"异常情况，请将B站返回信息提交issus，B站返回信息：{res_json}")


    def get_account_info(self):
        """
        获取当前B站账号的个人信息。

        返回:
        dict: 包含账号个人信息的字典，例如用户名、用户UID、头像URL、用户等级等。
        """
        return self.send_bilibili_api_request("/x/web-interface/nav", "GET")

    def get_follow_list(self, vmid):
        """
        获取当前B站账号的关注列表。

        返回:
        list: 包含关注的用户信息的列表，每个元素是一个字典，包含关注用户的名称、ID等信息。
        """
        pn = 1
        ps = 50
        follow_info = []
        max_page = 1

        while pn <= max_page:
            endpoint = f"/x/relation/followings?vmid={vmid}&pn={pn}&ps={ps}&order=desc"
            response = self.send_bilibili_api_request(endpoint, "GET")
            
            if response["code"] == 0:
                if pn == 1:  # 初始化最大页数
                    total = response["data"]["total"]
                    max_page = math.ceil(total / ps)
                follow_info.extend(response["data"]["list"])
            else:
                print(f"获取关注列表信息失败，B站返回信息：{response}")
                break
            pn += 1
            time.sleep(1)  # 确保不过快发送请求以避免被封

        return follow_info
    
    
    def 批量关注(self, 要关注的up主的uid列表):
        
        """
        处理一个包含多个字典的列表，每个字典至少包含 'uid' 键。
        提取所有唯一的uid，并调用 关注B站UP主 函数。

        参数:
        session: 传递给 关注B站UP主 函数的会话对象
        missing_mids: 包含字典的列表，每个字典中应包含 'uid' 键

        返回:
        None
        """
        # 使用集合来自动剔除重复的uid
        unique_uids = set(item['uid'] for item in 要关注的up主的uid列表)
        
        # 遍历唯一的uid集合并调用关注B站UP主函数
        results = []
        for uid in unique_uids:
            result = self.关注B站UP主(uid)
            results.append(result)
            time.sleep(1)   #防止关注的太快被ban
        return results
        
    def 关注B站UP主(self, uid):
        """
        关注B站的UP主。
        参数:
        uid (int): 要关注的UP主的用户ID。
        返回:
        dict: 服务器返回的JSON响应。
        """
        csrf_token = self.session.cookies.get('bili_jct', '')
        data = {
            'fid': uid,
            'act': 1,  # act设置为1代表关注
            'csrf': csrf_token
        }
        endpoint = '/x/relation/modify'
        return self.send_bilibili_api_request(endpoint, "POST", data=data)
    
    def 通过uid获取直播间信息(self, missing_live_mids):
        """
        从给定的UID列表中获取并提取直播间信息。

        参数:
        missing_live_mids: 包含至少包含 'uid' 键的字典列表。

        返回:
        list: 包含每个成功请求的直播间信息的列表，或在出现错误时返回空列表。
        """
        results = []
        base_url = "/xlive/general-interface/v1/guard/GuardActive"
        watchtime = 0
        room_id = 0

        while room_id == 0 and watchtime == 0:
            for item in missing_live_mids:
                uid = item['uid']
                params = {"ruid": uid, "platform": "pc"}
                data = self.send_bilibili_live_api_request(base_url, "GET", params=params)

                if data and data['code'] == 0:
                    user_data = data['data']
                    watchtime = user_data["watch_time"]
                    rusername = user_data["rusername"]
                    room_id = user_data["room_id"]
                    room_url = f"https://live.bilibili.com/{room_id}"

                    addcache = {
                        "uid": uid,
                        "mid": uid,
                        "name": rusername,
                        "room_id": room_id,
                        "room_url": room_url
                    }
                    if room_id != 0 or watchtime != 0:
                        results.append(addcache)
                elif data and data['code'] == -412:
                    print("请求被ban了：", data)
                    time.sleep(300)
                    continue
                elif data and data['code'] == -504:
                    print("服务调用超时，3秒后重试")
                    time.sleep(3)
                    continue
                else:
                    sys.exit("请求出错了：", data)
                    return []

            if watchtime == 0:
                time.sleep(2)

        return results
    
    def 获取关注的开播信息(self):
        """
        获取当前B站账号的直播关注列表。

        返回:
        - dict: 包含关注的用户信息的列表以及其他统计数据。
        """
        results = []
        page = 1
        page_size = 10
        follow_total_page = 1
        # https://api.live.bilibili.com/xlive/web-ucenter/user/following?page=1&page_size=9&ignoreRecord=1&hit_ab=true
        base_url = "/xlive/web-ucenter/user/following"

        while page <= follow_total_page:
            params = {
                "page": page,
                "page_size": page_size,
                "ignoreRecord": 1,
                "hit_ab": True
            }
            response = self.send_bilibili_live_api_request(base_url, "GET", params=params)

            if response["code"] == 0:
                if page == 1:  # 初始化分页信息
                    follow_total_page = response["data"]["totalPage"]
                    follow_count = response["data"]["count"]
                    never_lived_count = response["data"]["never_lived_count"]
                    live_count = response["data"]["live_count"]

                for item in response["data"]["list"]:
                    results.append({
                        "uid": item["uid"],
                        "roomid": item["roomid"],
                        "name": item["uname"],
                        "title": item["title"],
                        "room_cover": item["room_cover"],
                        "live_status": item["live_status"],
                        "record_live_time": item["record_live_time"]
                    })

                page += 1
                if page > follow_total_page:
                    break
            elif response["code"] == -412:
                print(f"ip被ban，休息5分钟。错误信息：{response}")
                time.sleep(300)
                continue
            elif response["code"] == -504:
                print(f"服务调用超时，3秒后重试。错误信息：{response}")
                time.sleep(3)
                continue
            else:
                print(f"请求出错，错误信息：{response}")
                sys.exit(0)
            
            time.sleep(1)  # 适当等待避免频繁请求
        
        return {
            "count": follow_count,
            "live_count": live_count,
            "never_lived_count": never_lived_count,
            "list": results
        }
    
    def 获取开播主播信息(self, 现在开播的主播人数):
        """
        获取当前B站账号的直播开播列表+指定人数。

        返回:
        - dict: 包含关注的用户信息的列表以及其他统计数据。
        """
        results = {}
        page = 1
        page_size = 10
        follow_total_page = 1
        required_pages = 0  # 需要拉取的总页数
        base_url = "/xlive/web-ucenter/user/following"
        first_time_live_count = None  # 用于存储第一次拉取的live_count

        while True:  # 使用无限循环来确保能够重新开始
            while page <= required_pages or page <= follow_total_page:
                params = {
                    "page": page,
                    "page_size": page_size,
                    "ignoreRecord": 1,
                    "hit_ab": True
                }
                response = self.send_bilibili_live_api_request(base_url, "GET", params=params)

                if response["code"] == 0:
                    current_live_count = response["data"]["live_count"]
                    if page == 1:  # 初始化分页信息和必要的拉取页数
                        follow_total_page = response["data"]["totalPage"]
                        follow_count = response["data"]["count"]
                        never_lived_count = response["data"]["never_lived_count"]
                        first_time_live_count = current_live_count
                        required_pages = math.ceil((现在开播的主播人数 + first_time_live_count) / page_size) + 1

                    if current_live_count != first_time_live_count:
                        print("live_count 发生变化，重新开始拉取信息。")
                        results.clear()
                        page = 1
                        required_pages = 0  # 重置必要的拉取页数
                        first_time_live_count = None
                        continue  # 跳出for循环，开始下一个while循环

                    for item in response["data"]["list"]:
                        uid = item["uid"]
                        if uid in results:
                            print("发现重复的uid，重新开始拉取信息。")
                            results.clear()
                            page = 1
                            required_pages = 0  # 重置必要的拉取页数
                            first_time_live_count = None
                            continue  # 跳出for循环，开始下一个while循环
                        else:
                            results[uid] = {
                                "uid": item["uid"],
                                "roomid": item["roomid"],
                                "name": item["uname"],
                                "title": item["title"],
                                "room_cover": item["room_cover"],
                                "live_status": item["live_status"],
                                "record_live_time": item["record_live_time"]
                            }

                    page += 1
                    if page > required_pages and page > follow_total_page:
                        break
                elif response["code"] == -412:
                    print(f"ip被ban，休息5分钟。错误信息：{response}")
                    time.sleep(300)
                    continue
                elif response["code"] == -504:
                    print(f"服务调用超时，3秒后重试。错误信息：{response}")
                    time.sleep(3)
                    continue
                else:
                    print(f"请求出错，错误信息：{response}")
                    sys.exit(0)
                
                time.sleep(1)  # 适当等待避免频繁请求
            
            if page > required_pages and page > follow_total_page:  # 成功完成所有必要页的拉取
                break
        
        return {
            "count": follow_count,
            "live_count": first_time_live_count,  # 使用第一次拉取的live_count
            "never_lived_count": never_lived_count,
            "list": list(results.values())  # 将字典的值转换为列表
        }

class SQLManager(object):
    # 初始化实例方法
    
    def __init__(self, config):
        self.conn = None
        self.cursor = None
        self.POOL = PooledDB(
            creator=pymysql,
            maxconnections=5000,  # 连接池允许的最大连接数，0和None表示不限制连接数
            mincached=2,  # 初始化时，链接池中至少创建的空闲的链接，0表示不创建
            maxcached=0,  # 链接池中最多闲置的链接，0和None不限制
            maxshared=50,  # 链接池中最多共享的链接数量，0和None表示全部共享
            blocking=True,  # 连接池中如果没有可用连接后，是否阻塞等待。True，等待；False，不等待然后报错
            maxusage=None,  # 一个链接最多被重复使用的次数，None表示无限制
            setsession=[],  # 开始会话前执行的命令列表。如：["set datestyle to ...", "set time zone ..."]
            ping=0,
            # ping MySQL服务端，检查是否服务可用。
            # 如：0 = None = never,
            # 1 = default = whenever it is requested,
            # 2 = when a cursor is created,
            # 4 = when a query is executed,
            # 7 = always 
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"] or 4000,
            user=DB_CONFIG["user"],
            password=DB_CONFIG["passwd"],
            charset=DB_CONFIG["charset"]
        )
        try:
            self.connect(config["db"])
            print("数据库连接成功")
        except Exception as e:
            sys.exit(f"连接数据库失败: {e}")
    # 连接数据库
    def connect(self, db_name):
        self.conn = self.POOL.connection()
        self.cursor = self.conn.cursor(cursor=pymysql.cursors.DictCursor)
        # 创建数据库,不存在才创建
        try:
            self.modify("create database if not exists %s" % DB_CONFIG["db"])
            self.modify("use %s" % DB_CONFIG["db"])
        except pymysql.Error as e:
            raise Exception(f"数据库测试失败: {e}")
            sys.exit(0)
    # 查询多条数据
    def getList(self, sql, args=None):
        self.cursor.execute(sql, args)
        result = self.cursor.fetchall()
        return result
    # 查询单条数据
    def getOne(self, sql, args=None):
        self.cursor.execute(sql, args)
        result = self.cursor.fetchone()
        return result
    # 执行单条SQL语句
    def modify(self, sql, args=None):
        self.cursor.execute(sql, args)
        self.conn.commit()
    # 我如果要批量执行多个创建操作，虽然只建立了一次数据库连接但是还是会多次提交，
    # 可不可以改成一次连接，一次提交呢？可以，只需要用上pymysql的executemany()方法就可以了。
    # 执行多条SQL语句
    def multiModify(self, sql, args=None):
        self.cursor.executemany(sql, args)
        self.conn.commit()
    # 创建单条记录的语句
    def create(self, sql, args=None):
        self.cursor.execute(sql, args)
        self.conn.commit()
        last_id = self.cursor.lastrowid
        return last_id
    # 关闭数据库cursor和连接
    def close(self):
        self.cursor.close()
        self.conn.close()
    # 最后，我们每次操作完数据库之后都要手动关闭，可不可以写成自动关闭的呢？
    # 联想到我们之前学过的文件操作，使用with语句可以实现缩进结束自动关闭文件句柄的例子。
    # 我们来把我们的数据库连接类SQLLogManager类再优化下，使其支持with语句操作。
    # 进入with语句自动执行
    def __enter__(self):
        return self
    # 退出with语句块自动执行
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # 初始化数据库表
    def createDB(self):
        # 创建数据库表 api_log ,不存在才创建
        '''sqlCreateLog = """CREATE TABLE IF NOT EXISTS `api_log` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `create_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP comment '创建时间',
            `update_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP comment '更新时间',
            `username` VARCHAR(255) NOT NULL comment '用户名',
            `time` TIMESTAMP NOT NULL comment '时间',
            `api_name` VARCHAR(255) NOT NULL comment 'API请求名',
            primary key(id),
            INDEX `idx_time` (`time`),
            INDEX `idx_count` (`time`,`username`)
            )ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4;"""
        self.modify(sqlCreateLog)'''
        
        pass
        return True

    def UpdateUserInfo(self, data):
        #插入或者更新直播表
        sql_user_info = """INSERT INTO `userinfo` (
        `uid`, `mid`, `name`, `room_id`, `room_url`)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            `name`=VALUES(`name`),
            `room_id`=VALUES(`room_id`),
            `room_url`=VALUES(`room_url`);"""
        args = (data[0], data[1], data[2], data[3], data[4])

        return self.create(sql_user_info, args)


    def UpdateLiveTimeStamp(self, data):
        #插入或者更新直播表
        sql_live_data = """INSERT INTO `livetimestamp` (
        `uid`, `room_id`, `live_status`, `last_live_timestamp`, `cover_image_url`, `cover_image_base64`, `remarks`)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            `live_status`=VALUES(`live_status`),
            `last_live_timestamp`=VALUES(`last_live_timestamp`),
            `last_offline_timestamp`=VALUES(`last_offline_timestamp`),
            `cover_image_url`=VALUES(`cover_image_url`),
            `cover_image_base64`=VALUES(`cover_image_base64`),
            `remarks`=VALUES(`remarks`);"""
        args = (data[0], data[1], data[2], data[3], data[4], data[5], data[6])  
        # 注意匹配参数顺序
        #print(sql_live_data, args)
        return self.create(sql_live_data, args)

    def UpdateOfflineTimeStamp(self, data):
        #插入或者更新直播表
        sql_live_data = """INSERT INTO `livetimestamp` (
        `uid`, `room_id`, `live_status`, `last_offline_timestamp`, `cover_image_url`, `cover_image_base64`, `remarks`)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            `live_status`=VALUES(`live_status`),
            `last_live_timestamp`=VALUES(`last_live_timestamp`),
            `last_offline_timestamp`=VALUES(`last_offline_timestamp`),
            `cover_image_url`=VALUES(`cover_image_url`),
            `cover_image_base64`=VALUES(`cover_image_base64`),
            `remarks`=VALUES(`remarks`);"""
        args = (data[0], data[1], data[2], data[3], data[4], data[5], data[6],)  
        # 注意匹配参数顺序
        #print(sql_live_data, args)
        return self.create(sql_live_data, args)

    def GetLiveTimeStamp(self, data):
        #插入或者更新直播表
        sql_live_data = """SELECT `uid`, `room_id`, `live_status`, `last_live_timestamp`, `last_offline_timestamp`, `cover_image_url`, `cover_image_base64`, `remarks` FROM `livetimestamp` WHERE `uid` = %s and `room_id` = %s"""
        args = (data[0], data[1])  
        # 注意匹配参数顺序
        #print(sql_live_data, args)
        return self.getOne(sql_live_data, args)

    def GetLiveTimeStamp(self, data):
        #查询直播信息
        sql_select_data = 'SELECT `uid`, `room_id`, `live_status`, `last_live_timestamp`, `last_offline_timestamp`, `cover_image_url`, `cover_image_base64`, `remarks` FROM `livetimestamp` WHERE `uid` = %s and `room_id` = %s;'
        args = (data[0], data[1])
        
        return self.getOne(sql_select_data, args)
    
    def LoadLiveRoomInfo(self):
        sql_select_data = 'SELECT `uid`, `mid`, `name`, `room_id`, `room_url` FROM `userinfo` WHERE 1;'
        try:
            bilibili_live_room_info = self.getList(sql_select_data)
            return bilibili_live_room_info
        except Exception as e:
            # 记录或处理异常
            print("Error during data import:", str(e))
            return None
    
    def LoadConcernstate(self):
        """
        从数据库中导入所有缓存数据。
        返回:
            list: 包含所有缓存记录的列表，每条记录是一个包含用户名、API名称和请求时间的元组。
        """
        try:
            sql_select_data = 'SELECT `group_id`, `uid`, `push_mode`, `at_all`, `at_someone`, `filter_not_type`, `offline_notify`, `title_change_notify` FROM `concernstatev2` WHERE 1;'
            return self.getList(sql_select_data)
        except Exception as e:
            # 记录或处理异常
            print("Error during data import:", str(e))
            return None

class DDBOTMain():
    def 查群号(Q群列表,群关注列表):
        # 从群信息中提取所有的群号，创建一个索引
        群号索引 = set(群信息['group_id'] for 群信息 in Q群列表)
        # 生成器表达式
        
        # 遍历关注数据，检查每个群号是否在群号索引中
        # 并保持群号、主播uid(group_id, uid)作为唯一键
        缺少的群号列表 = [群号 for 群号 in 群关注列表 if 群号['group_id'] not in 群号索引]
        
        return 缺少的群号列表
        
    def 查关注(群关注列表, B站关注列表):
        # 从B站关注列表中将所有的mid全都加到一个list中创建索引编译查找
        B站关注的mids = {item['mid'] for item in B站关注列表}
        # 集合推导式
        
        # 收集所有不在 B站关注列表 中的 群关注列表
        缺少账号关注的群关注列表 = [item for item in 群关注列表 if item['uid'] not in B站关注的mids]
        
        return 缺少账号关注的群关注列表
        
    # 别问，问就是这俩函数不是一个人写的，别管生成器表达式和集合推导式的问题，你就说这两种写法能不能用吧
    # 这些注释也不是一个人写的，我是第四个人吧（大概）
    
    def 查房间号缺失情况(群关注列表, 本地直播间号缓存):
        # 提取出所有 本地直播间号缓存 中的 mid
        UP主的UID索引 = {item['mid'] for item in 本地直播间号缓存}
        
        # 筛选出所有推送方法（push_mode）中包含"live"的 群关注列表
        直播推送列表 = [item for item in 群关注列表 if 'live' in item['push_mode']]
        
        # 根据 uid ，找出群关注列表中不在 本地直播间号缓存的数据
        缺少直播间号的群关注列表 = [item for item in 直播推送列表 if item['uid'] not in UP主的UID索引]
        
        return 缺少直播间号的群关注列表
    
    def 批量更新房间号信息(user_list, DB_CONFIG):
        """
        批量更新用户信息到数据库。
        参数:
        user_list (list): 包含用户信息的列表，每个元素是一个包含必要信息的字典。
        返回:
        list: 包含每次操作返回的数据库结果的列表，如果没有执行任何更新，返回空列表。
        """
        results = []  # 初始化一个空列表来存储每次操作的结果
        if len(user_list) > 0:
            DB = SQLManager(DB_CONFIG)
            for user in user_list:
                # 提取字典中的所有值
                user_info = [user['uid'], user['mid'], user['name'], user['room_id'], user['room_url']]
                # 调用UpdateUserInfo函数，传递提取的信息
                try:
                    Concernstate_info = DB.UpdateUserInfo(user_info)
                    results.append(Concernstate_info)  # 将结果添加到列表中
                except Exception as e:
                    print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                          '更新数据库直播信息出错！', e)
                    results.append(None)  # 如果出现异常，添加None到结果列表
        return results  # 返回包含所有结果的列表
    
    def 提取关注的主播(B站直播列表, 群关注列表):
        # 创建一个 群关注mids索引，用于快速检查uid是否存在
        
        #print("B站直播列表:", B站直播列表)
        #print("群关注列表:", 群关注列表)
        
        群关注mids索引 = set(item['uid'] for item in 群关注列表)
        
        # 从B站直播列表中，根据uid提取群员关注的UP主
        B站关注的主播列表 = [user for user in B站直播列表 if user['uid'] in 群关注mids索引]
        
        # 对 B站关注的主播列表 按照 uid 进行排序，uid 小的在前
        排序好后的B站关注的主播列表 = sorted(B站关注的主播列表, key=lambda x: x['uid'])

        return 排序好后的B站关注的主播列表
    
    def 提取开播的主播(B站直播列表):
        pass
        # 筛选出 B站直播列表 中 live_status为1的用户
        开播用户 = [ 用户 for 用户 in B站直播列表 if 用户['live_status'] == 1]
        
        # 对开播用户按照uid进行排序，uid小的在前
        排序好的开播主播 = sorted(开播用户, key=lambda x: x['uid'])
        
        return 排序好的开播主播
    
    def 下播判定(机器人缓存, B站实时数据):
        # 提取实时的B站开播数据的uid作为索引
        实时开播主播uid索引 = set(user['uid'] for user in B站实时数据)
        
        # 从 机器人缓存 中筛选出不在 实时开播主播uid 的用户
        
        开播用户列表 = [ 用户 for  用户 in 机器人缓存 if 用户['uid'] not in 实时开播主播uid索引]
        
        # 对 开播用户列表 按照 uid 进行排序， uid 小的在前
        开播用户 = sorted(开播用户列表, key=lambda x: x['uid'])
        
        return 开播用户

    def 推送判定(B站直播列表, 群推送列表):
        # 创建一个 B站直播uids索引，并创建一个字典来存储 B站直播信息
        B站直播uids索引 = {item['uid']: item for item in B站直播列表}
        
        # 从群推送列表中，根据uid寻找需要推送的群号，并合并 B站直播信息
        下播推送列表 = []
        for user in 群推送列表:
            uid = user['uid']
            if uid in B站直播uids索引:
                # 将 B站直播信息合并到群推送列表的条目中
                推送条目 = user.copy()
                推送条目.update(B站直播uids索引[uid])
                下播推送列表.append(推送条目)
        
        return 下播推送列表
    
    def 下播开启判定(下播推送列表):
        return [user for user in 下播推送列表 if user['offline_notify'] == 'live']
    
    def encode_image_to_base64(url):
        response = requests.get(url)
        return f"data:{response.headers['Content-Type']};base64," + base64.b64encode(response.content).decode()
        
    def 更新数据库直播缓存(直播数据, 开播时间戳, DB_CONFIG):
        returns = []
        DB = SQLManager(DB_CONFIG)
        for entry in 直播数据:
            data = []
            uid = entry['uid']
            roomid = entry['roomid']
            live_status = 'live' if entry['live_status'] == 1 else 'offline'
            last_live_timestamp = 开播时间戳 if entry['live_status'] == 1 else entry['record_live_time']
            room_cover_url = entry['room_cover']
            if room_cover_url == '':
                room_cover_base64 = ''
            else:
                room_cover_base64 = DDBOTMain.encode_image_to_base64(room_cover_url)
            data = [uid, roomid, live_status, last_live_timestamp, room_cover_url, room_cover_base64, ""]
            if entry['live_status'] == 1:
                returns.append(DB.UpdateLiveTimeStamp(data))
            else:
                returns.append(DB.UpdateOfflineTimeStamp(data))
        
        return returns

if __name__ == '__main__':
    
    logging.info("正在初始化配置文件")
    yaml_file_path = 'application.yaml'
    application = yaml_to_json(yaml_file_path)
    print("配置文件初始化完成，正在连接到QQNT，请稍后")
    QQNTBOT = QQBotInfo(application["bot"]["send"]["url"], application["bot"]["send"]["accesstoken"])
    
    QQ_Account_Info = QQNTBOT.get_bot_account_info()
    logging.info("Bot Account Info:"+ str(QQ_Account_Info))
    if QQ_Account_Info["status"] == "ok":
        if QQ_Account_Info["data"]["user_id"] >9999:
            qid = QQ_Account_Info["data"]["user_id"]
            qname = QQ_Account_Info["data"]["nickname"]
            print(f"连接QQNT成功，欢迎您{qid} {qname}")
    else:
        sys.exit("连接失败，正在退出DDBOTNT")
    
    QQ_Friends_List = QQNTBOT.get_qq_friends_list()["data"][:]
    logging.info("Friends List:"+ str(QQ_Friends_List))
    print("QQ好友列表初始化完成，一共", len(QQ_Friends_List),"个好友")
    
    QQ_Groups_List = QQNTBOT.get_qq_groups_list()["data"][:]
    logging.info("Groups List:"+ str(QQ_Groups_List))
    print("QQ群列表初始化完成，一共", len(QQ_Groups_List),"个群")
    
    logging.info("正在初始化B站会话")
    Bilibili_Session = requests.Session()
    Bilibili_Session.headers.update({
        'User-Agent': 'Mozilla/5.1 (X11; UOS V20; SM3) DDBOTNT/5.2 (KHTML, like Gecko) Firefox/99.100'
    })
    Bilibili_Session.cookies.update({
        'SESSDATA' : application["bilibili"]["SESSDATA"],
        'bili_jct': application["bilibili"]["bili_jct"],
        'buvid3': application["bilibili"]["buvid3"]
    })
    
    Bilibili = BilibiliMain(Bilibili_Session)
    Bilibili_Account_Info = Bilibili.get_account_info()
    logging.info("账号信息:"+ str(Bilibili_Account_Info))
    Mid = Bilibili_Account_Info["data"]["mid"]
    VipLevel = Bilibili_Account_Info["data"]["vip_label"]["text"]
    CurrentLevel = Bilibili_Account_Info["data"]["level_info"]["current_level"]
    Uname = Bilibili_Account_Info["data"]["uname"]
    print(f"B站启动成功，当前使用账号：{Uname} UID:{Mid} {VipLevel} LV{CurrentLevel}")
    Bilibili_Follow_List = Bilibili.get_follow_list(vmid=Bilibili_Account_Info["data"]["mid"])
    
    logging.info("关注列表:"+ str(Bilibili_Follow_List))
    print("关注列表加载完成，一共",len(Bilibili_Follow_List),"位用户")
    
    logging.info("正在初始化数据库")
    DB_CONFIG = {
        "host": application["dbConfig"]["host"],
        "port": application["dbConfig"]["port"],
        "user": application["dbConfig"]["user"],
        "passwd": application["dbConfig"]["passwd"],
        "db": application["dbConfig"]["db"],
        "charset": application["dbConfig"]["charset"]
    }
    
    DB = SQLManager(DB_CONFIG)
    try:
        Concernstate = DB.LoadConcernstate()
    except Exception as e:
        logging.info(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))+
                '读取本地群关注信息数据库出错！', e)
        sys.exit(0)
    if Concernstate is None:
        sys.exit("本地数据库返回群关注信息错误")
    else:
        pass
    
    try:
        Live_Room_Info = DB.LoadLiveRoomInfo()
    except Exception as e:
        logging.info(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))+
                '读取本地直播间号缓存信息数据库出错！', e)
        sys.exit(0)
    if Live_Room_Info is None:
        sys.exit("本地数据库返回直播间号错误")
    else:
        pass
        
    logging.info("正在核对关注列表和群列表")
    missing_groups = DDBOTMain.查群号(QQ_Groups_List, Concernstate)
    if len(missing_groups) > 0:
        print("检测到异常，机器人不在下列群中：",missing_groups)
        logging.info("检测到异常，机器人不在下列群中："+ str(missing_groups))
        sys.exit("请手动删除数据库中的数据后再启动机器人，以后会优化的")#todo
    else:
        logging.info("关注列表和群列表核对完毕，关注列表所在群没有异常")
    
    missing_mids = DDBOTMain.查关注(Concernstate, Bilibili_Follow_List)
    if len(missing_mids) > 0:
        print("检测到异常，这些用户不在关注列表中：", missing_mids)
        logging.info("检测到异常，这些用户不在关注列表中："+ str(missing_mids))
        print("执行关注代码，让B站账号去关注这些缺失的uid")
        logging.info("执行关注代码，让B站账号去关注这些缺失的uid")
        Bilibili.批量关注(missing_mids)
        print("执行关注代码成功，已将这些用户添加到关注列表中")
        logging.info("执行关注代码成功，已将这些用户添加到关注列表中")
    else:
        logging.info("关注列表和账号关注核对完毕，关注列表均在关注列表中")
        
    missing_live_mids = DDBOTMain.查房间号缺失情况(Concernstate, Live_Room_Info)
    
    if len(missing_live_mids) > 0:
        print("检测到异常，这些用户的房间号缺失：",missing_live_mids)
        logging.info("检测到异常，这些用户的房间号缺失："+ str(missing_live_mids))
        需要添加的直播间信息 = Bilibili.通过uid获取直播间信息(missing_live_mids)
        logging.info("执行关注代码后的查询房间号输出：", str(需要添加的直播间信息))
        if len(需要添加的直播间信息) > 0:
            res = DDBOTMain.批量更新房间号信息(需要添加的直播间信息, DB_CONFIG)
            logging.info(str(res))
    else:
        logging.info("关注直播的房间号核对完毕，所有需要关注直播推送的直播间信息对照没有缺失")
    
    # todo 检测推送状态为live的V有无房间号为0
    print("现在还没有自检程序，以后会有的")
    print("自检完毕，DDBOTNT启动完成")
    print("DDBOTNT唯一指定管理员：804954374")
    print("D宝，一款真正人性化的单推BOT")
    
    B站直播列表 = Bilibili.获取关注的开播信息()
    B站直播列表时间戳 = int(time.time())
    
    logging.info("正在从总直播状态列表中，提取需要推送的UP直播状态信息")
    
    DDBOT关注的主播缓存 = DDBOTMain.提取关注的主播(B站直播列表['list'], Concernstate)
    
    #todo 更新数据表livetimestamp
    logging.info("DDBOT关注的主播缓存"+ str(DDBOT关注的主播缓存))
    要更新数据库的主播缓存 = []
    for item in DDBOT关注的主播缓存:
        if item['live_status'] == 1 and (DB.GetLiveTimeStamp((item['uid'], item['roomid']))['live_status'] == "live"):
            # TODO: 添加未来处理直播中状态的代码
            pass
        else:
            logging.info("已添加的要更新数据库的主播："+ str(item))
            要更新数据库的主播缓存.append(item)
    DDBOTMain.更新数据库直播缓存(要更新数据库的主播缓存, B站直播列表时间戳, DB_CONFIG)
    logging.info("数据库缓存同步完成")
    
    DDBOT开播的主播缓存 = DDBOTMain.提取开播的主播(DDBOT关注的主播缓存)
    
    logging.info("目前开播的直播间有："+ str(DDBOT开播的主播缓存))
    
    print("直播推送初始化完毕")
    logging.info("直播推送初始化完毕")
    
    while 1:
        当前B站开播的主播汇总 = Bilibili.获取开播主播信息(len(DDBOT开播的主播缓存))
        B站直播列表时间戳 = int(time.time())
        当前B站开播的主播人数 = 当前B站开播的主播汇总["live_count"]
        当前B站开播的主播列表 = 当前B站开播的主播汇总["list"]
        logging.info(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))+ "当前B站开播的主播列表:\n" + str(当前B站开播的主播列表))
        当前群关注的B站主播列表 = DDBOTMain.提取关注的主播(当前B站开播的主播列表, Concernstate)
        当前群关注的B站开播主播列表 =  DDBOTMain.提取开播的主播(当前群关注的B站主播列表)
        logging.info(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))+ "当前群关注的B站开播主播列表:" +str(当前群关注的B站开播主播列表))
        Q群推送列表 = []
        下播的主播 = DDBOTMain.下播判定(DDBOT开播的主播缓存, 当前群关注的B站开播主播列表)
        开播的主播 = DDBOTMain.下播判定(当前群关注的B站开播主播列表, DDBOT开播的主播缓存)
        
        
        
        if len(下播的主播) > 0:
            print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), "检测到新下播的主播：",下播的主播)
            logging.info(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))+ "检测到新下播的主播："+ str(下播的主播))
            DDBOTMain.更新数据库直播缓存(下播的主播, B站直播列表时间戳, DB_CONFIG)
            print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), "数据库缓存同步完成")
            logging.info(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))+ "数据库缓存同步完成")
            需要进行下播推送的群队列 = DDBOTMain.推送判定(下播的主播, Concernstate)
            print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), "需要进行下播推送的群队列：", 需要进行下播推送的群队列)
            logging.info(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))+ "需要进行下播推送的群队列："+ str(需要进行下播推送的群队列))
            已经开启下播推送的群队列 = DDBOTMain.下播开启判定(需要进行下播推送的群队列)
            if len(已经开启下播推送的群队列) > 0:
                print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), "已经开启下播推送的群队列",已经开启下播推送的群队列)
                logging.info(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))+ "已经开启下播推送的群队列"+str(已经开启下播推送的群队列))
                #try:
                for item in 已经开启下播推送的群队列:
                    Res = QQNTBOT.发送下播通知(
                        group_id=item['group_id'],
                        anchor_name=item['name'],
                        cover_visual_url=item['room_cover']
                    )
                    time.sleep(2) 
                    
                '''except Exception as e:
                    print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())),
                            '推送下播消息提醒的队列出错了！', e)
                    print(item,已经开启下播推送的群队列)'''
        
        if len(开播的主播) > 0:
            print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), "检测到新开播的主播：",开播的主播)
            logging.info("检测到新开播的主播："+ str(开播的主播))
            DDBOTMain.更新数据库直播缓存(开播的主播, B站直播列表时间戳, DB_CONFIG)
            print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), "数据库缓存同步完成")
            logging.info(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))+ "数据库缓存同步完成")
            需要进行开播推送的群队列 = DDBOTMain.推送判定(开播的主播, Concernstate)
            if len(需要进行开播推送的群队列) > 0:
                print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), "需要进行开播推送的群队列：",需要进行开播推送的群队列)
                logging.info(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))+ "需要进行开播推送的群队列："+ str(需要进行开播推送的群队列))
                #try:
                for item in 需要进行开播推送的群队列:
                    Res = QQNTBOT.发送开播通知(
                        group_id=item['group_id'],
                        anchor_name=item['name'],
                        live_title=item['title'],
                        room_number=item['roomid'],
                        cover_visual_url=item['room_cover'],
                        at_list=item['at_someone'],
                        at_all=True if item['at_all'] == "live" else False
                    )
                    time.sleep(2)
                '''except Exception as e:
                    print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())),
                            '推送开播消息提醒的队列出错了！', e)
                    print(item,需要进行开播推送的群队列)'''
                
        DDBOT开播的主播缓存 = 当前群关注的B站开播主播列表
        
        休眠间隔 = int(application["bilibili"]["interval"][:-1])
        logging.info(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))+ f"没有检测到主播状态有变化，等待{休眠间隔}秒")
        
        
        time.sleep(休眠间隔)
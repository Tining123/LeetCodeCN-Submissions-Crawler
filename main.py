# -*- coding: utf-8 -*-
#/usr/bin/env python3
"""
这是一个将力扣中国(leetcode-cn.com)上的【个人提交】的submission自动爬到本地并push到github上的爬虫脚本。
请使用相同目录下的config.json设置 用户名，密码，本地储存目录等参数。
致谢@fyears， 本脚本的login函数来自https://gist.github.com/fyears/487fc702ba814f0da367a17a2379e8ba
仓库地址：https://github.com/JiayangWu/LeetCodeCN-Submissions-Crawler
如果爬虫失效的情况，请在原仓库提出issue。
"""

import unicodedata
import sys, os, time
from ProblemList import GetProblemId
import requests, json
from bs4 import BeautifulSoup
import json
import re

#~~~~~~~~~~~~以下是无需修改的参数~~~~~~~~~~~~~~~~·
requests.packages.urllib3.disable_warnings() #为了避免弹出一万个warning，which is caused by 非验证的get请求

leetcode_url = 'https://leetcode-cn.com/'

sign_in_url = 'accounts/login/'
sign_in_url = leetcode_url + sign_in_url
submissions_url = 'submissions/'
submissions_url = leetcode_url + submissions_url

path = "/Users/wujiayang/Downloads/LeetCodeCN-Submissions-Crawler-master-2/config.json"

with open(path, "r") as f: #读取用户名，密码，本地存储目录
    temp = json.loads(f.read())   
    USERNAME = temp['username']
    PASSWORD = temp['password']
    OUTPUT_DIR = temp['outputDir']
    TIME_CONTROL = 3600 * 24 * temp['time']
#~~~~~~~~~~~~以上是无需修改的参数~~~~~~~~~~~~~~~~·

#~~~~~~~~~~~~以下是可以修改的参数~~~~~~~~~~~~~~~~·
START_PAGE = 0  # 从哪一页submission开始爬起，0是最新的一页
sleep_time = 5  # in second，登录失败时的休眠时间
#~~~~~~~~~~~~以上是可以修改的参数~~~~~~~~~~~~~~~~·

def login(email, password): # 本函数修改自https://gist.github.com/fyears/487fc702ba814f0da367a17a2379e8ba，感谢@fyears
    client = requests.session()
    client.encoding = "utf-8"

    while True:
        try:
            client.get(sign_in_url, verify=False)

            login_data = {'login': email, 
                'password': password
            }
            
            result = client.post(sign_in_url, data = login_data, headers = dict(Referer = sign_in_url))
            
            if result.ok:
                print ("Login successfully!")
                break
        except:
            print ("Login failed! Wait till next round!")
            time.sleep(sleep_time)

    return client

def scraping(client):
    page_num = START_PAGE
    visited = set()

    file_format = {"C++": ".cpp", "Python3": ".py", "Python": ".py", "MySQL": ".sql", "Go": ".go", "Java": ".java",
                   "C": ".c", "JavaScript": ".js", "PHP": ".php", "C#": ".cs", "Ruby": ".rb", "Swift": ".swift",
                   "Scala": ".scl", "Kotlin": ".kt", "Rust": ".rs"}
    
    while True:
        print ("Now for page:", str(page_num))
        submissions_url = "https://leetcode-cn.com/api/submissions/?offset=" + str(page_num) + "&limit=20&lastkey="

        h = client.get(submissions_url, verify=False)
        t = time.time()
        invalidset = set()
        html = json.loads(h.text)
        if not html.get("submissions_dump"):
            print ("Warning! No previous submission is detected, please make sure you are logging in the correct account AND you once submitted codes on leetcode-cn.com")
            break
            
        for idx, submission in enumerate((html["submissions_dump"])):
            Status = submission['status_display']
            Title = submission['title'].replace(" ","")
            Lang = submission['lang']
            
            if Status != "Accepted":
                print (Title + " was not Accepted, continue for the next submission")
                continue

            if t - submission['timestamp'] > TIME_CONTROL: #时间管理，本行代表只记录最近的TIME_CONTROL天内的提交记录
                return

            try:
                Pid = GetProblemId(Title)
                if Pid == "0" or Title in invalidset:
                    print (Title + " failed! Due to unknown Pid! ")
                    if Title not in invalidset: #第一次没找到
                        with open("Log.txt", "a") as log:
                            log.write("Unknown PID happened for " + Title)

                        invalidset.add(Title)
                else:
                    if Pid not in visited:
                        visited.add(Pid) #保障每道题只记录最新的AC解
                        if Pid[0].isdigit(): # 如果题目是传统的数字题号
                            Pid = int(Pid)
                            newpath = OUTPUT_DIR + "/" + '{:0=4}'.format(Pid) + "." + Title #存放的文件夹名
                            filename = '{:0=4}'.format(Pid) + "-" + Title + file_format[Lang] #存放的文件名
                        else: # 如果题目是新的面试题
                            newpath = OUTPUT_DIR + "/" + Pid + "." + Title
                            filename = Pid + "-" + Title + file_format[Lang] #存放的文件名
                        newpath = 'save'
                        if not os.path.exists(newpath):
                            os.mkdir(newpath)
                        
                        totalpath = os.path.join(newpath, filename) #把文件夹和文件组合成新的地址

                        code = get_code(submission, client)
                        
                        with open('save/' + filename, "w") as f: #开始写到本地
                            f.write(code)
                            print ("Writing ends!", totalpath)
                            
            except FileNotFoundError as e:
                print("Output directory doesn't exist")
                
            except Exception as e:
                print(e, " Unknwon bug happened, please raise an issue with your log to the writer.")

        time.sleep(1)           
        page_num += 20

def git_push():
    today = time.strftime('%Y-%m-%d',time.localtime(time.time()))
    os.chdir(OUTPUT_DIR)
    instructions = ["git add .","git status", "git commit -m \""+ today + "\"", "git push -u origin master"]
    for ins in instructions:
        os.system(ins)
        print ("~~~~~~~~~~~~~" + ins + " finished! ~~~~~~~~")

def get_code(submission, client):
        headers = {
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36'
        }   
        param = {'operationName': "mySubmissionDetail", "variables": {"id": submission["id"]},
                 'query': "query mySubmissionDetail($id: ID\u0021) {  submissionDetail(submissionId: $id) {    id    code    runtime    memory    statusDisplay    timestamp    lang    passedTestCaseCnt    totalTestCaseCnt    sourceUrl    question {      titleSlug      title      translatedTitle      questionId      __typename    }    ... on GeneralSubmissionNode {      outputDetail {        codeOutput        expectedOutput        input        compileError        runtimeError        lastTestcase        __typename      }      __typename    }    __typename  }}"
                        }

        param_json = json.dumps(param).encode("utf-8")
        response = client.post("https://leetcode-cn.com/graphql/", data = param_json, headers = headers)
        submission_details = response.json()["data"]["submissionDetail"]

        return submission_details["code"]

def main():
    email = USERNAME
    password = PASSWORD

    print('login')
    client = login(email, password)

    print('start scrapping')
    scraping(client)
    print('end scrapping')

    git_push()
    print('Git push finished')

if __name__ == '__main__':
    main()


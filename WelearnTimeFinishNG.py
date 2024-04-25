import sys
import requests
import json
import time
import random
import threading
from tqdm import tqdm

thread_max = 64 #最大线程数设置

forceQuit = False
currentThreads = 0
learningTimeNow = 0
learningTimeQueued = 0
finishedCourcesList = []
errorCourcesList = []
messageListFromThreads = []
progressBar = tqdm()
session = requests.Session()

def printline():
    print('-'*51)
# 获取账户密码
try:  # 直接从命令行中获取
    username, password = sys.argv[1], sys.argv[2]
except:
    loginmode=input('请选择登录方式: \n  1.账号密码登录\n  2.Cookie登录\n\n请输入数字1或2: ')
    printline()
    if loginmode=='1':
        username = input('请输入账号: ')
        password = input('请输入密码: ')
        # 登录模块
        response = requests.get(
            'https://welearn.sflep.com/user/prelogin.aspx?loginret=http%3a%2f%2fwelearn.sflep.com%2fuser%2floginredirect.aspx', allow_redirects=False)
        rturl = response.headers['Location'].replace(
            'https://sso.sflep.com/idsvr', '')
        data = {
            'rturl': rturl,
            'account': username,
            'pwd': password,
        }
        res = session.post(
            "https://sso.sflep.com/idsvr/account/login", data=data)
        url = 'https://sso.sflep.com/idsvr'+rturl
        res = session.get(url)
        if "我的主页" in res.text:
            print("登录成功!!")
        else:
            input("登录失败!!")
            exit(0)
    elif loginmode=='2':
        try:
            cookie = dict(map(lambda x:x.split('=',1),input('请粘贴Cookie: ').split(";")))
        except:
            input('Cookie输入错误!!!')
            exit(0)
        for k,v in cookie.items():
              session.cookies[k]=v
    else:
        input('输入错误!!')
        exit(0)
printline()
def startstudy(learntime,x):
    global learningTimeNow, currentThreads, learningTimeQueued, errorCourcesList, finishedCourcesList
    currentThreads += 1
    messageListFromThreads.append('加入队列    [ ' + x['location'] + ' ]')
    time.sleep(random.random() * 10)
    scoid = x['id']
    url = 'https://welearn.sflep.com/Ajax/SCO.aspx'
    req1 = session.post(url,data={'action':'getscoinfo_v7','uid':uid,'cid':cid,'scoid':scoid},headers={'Referer':'https://welearn.sflep.com/student/StudyCourse.aspx' })
    if('学习数据不正确' in req1.text):
        req1 = session.post(url,data={'action':'startsco160928','uid':uid,'cid':cid,'scoid':scoid},headers={'Referer':'https://welearn.sflep.com/student/StudyCourse.aspx' })
        req1 = session.post(url,data={'action':'getscoinfo_v7','uid':uid,'cid':cid,'scoid':scoid},headers={'Referer':'https://welearn.sflep.com/student/StudyCourse.aspx' })
        if('学习数据不正确' in req1.text):
            currentThreads -= 1
            errorCourcesList.append(x['location'])
            messageListFromThreads.append('学习数据不正确    [ ' + x['location'] + ' ]')
            return 0
    back = json.loads(req1.text)['comment']
    if('cmi' in back):
        back = json.loads(back)['cmi']
        cstatus = back['completion_status']
        progress = back['progress_measure']
        session_time = back['session_time']
        total_time = back['total_time']
        crate = back['score']['scaled']
    else:
        cstatus = 'not_attempted'
        progress = session_time = total_time = '0'
        crate = ''
    url = 'https://welearn.sflep.com/Ajax/SCO.aspx'
    req1 = session.post(url,data={'action':'keepsco_with_getticket_with_updatecmitime','uid':uid,'cid':cid,'scoid':scoid,'session_time':session_time,'total_time':total_time},headers={'Referer':'https://welearn.sflep.com/student/StudyCourse.aspx' })
    learningTimeQueued += learntime
    messageListFromThreads.append('任务开始    [ ' + x['location'] + ' ]')
    for nowtime in range(1,learntime + 1):
        time.sleep(1)
        learningTimeNow += 1
        if(nowtime % 60 == 0):
            # messageListFromThreads.append('心跳数据 [' + x['location'] + ']')
            url = 'https://welearn.sflep.com/Ajax/SCO.aspx'
            req1 = session.post(url,data={'action':'keepsco_with_getticket_with_updatecmitime','uid':uid,'cid':cid,'scoid':scoid,'session_time':session_time,'total_time':total_time},headers={'Referer':'https://welearn.sflep.com/student/StudyCourse.aspx' })
        if(forceQuit):
            learningTimeQueued -= learntime - nowtime
            time.sleep(random.random() * currentThreads * 0.3)
            break
    url = 'https://welearn.sflep.com/Ajax/SCO.aspx'
    req1 = session.post(url,data={'action':'savescoinfo160928','cid':cid,'scoid':scoid,'uid':uid,'progress':progress,'crate':crate,'status':'unknown','cstatus':cstatus,'trycount':'0'},headers={'Referer':'https://welearn.sflep.com/Student/StudyCourse.aspx'})
    currentThreads -= 1
    finishedCourcesList.append((x['location'], learntime,))
    messageListFromThreads.append('任务完成    [' + x['location'] + ']')

class NewThread(threading.Thread):
    def __init__(self,learntime,x):
        threading.Thread.__init__(self)
        self.deamon = True
        self.learntime = learntime
        self.x = x
    def run(self):
        try:
            startstudy(self.learntime,self.x)
        except:
            currentThreads -= 1
            errorCourcesList.append(self.x['location'])
            messageListFromThreads.append('线程错误    [ ' + self.x['location'] + ' ]')

last_learningTimeNow = 0
def wait_running(max_cnt = 0):
    global progressBar, currentThreads, last_learningTimeNow
    progressBar.set_description("线程数：%d|已刷：%02d:%02d:%02d" % (currentThreads , learningTimeNow // 3600, learningTimeNow % 3600 // 60, learningTimeNow % 60))
    progressBar.total = learningTimeQueued
    progressBar.update(learningTimeNow - last_learningTimeNow)
    last_learningTimeNow = learningTimeNow
    while(len(messageListFromThreads) > 0):
        progressBar.write(messageListFromThreads.pop(0))
    while (currentThreads > max_cnt):
        progressBar.total = learningTimeQueued
        progressBar.set_description("线程数：%d|已刷：%02d:%02d:%02d" % (currentThreads , learningTimeNow // 3600, learningTimeNow % 3600 // 60, learningTimeNow % 60))
        progressBar.update(learningTimeNow - last_learningTimeNow)
        last_learningTimeNow = learningTimeNow
        while(len(messageListFromThreads) > 0):
            progressBar.write(messageListFromThreads.pop(0))
        time.sleep(0.05)
try:
    while True:
        url = 'https://welearn.sflep.com/ajax/authCourse.aspx?action=gmc'
        req = session.get(url,headers={'Referer':'https://welearn.sflep.com/student/index.aspx'})
        try:
            back = json.loads(req.text)['clist']
        except:
            print('登录失败，请检查账号密码或Cookie是否正确！！')
            exit(0)
        i = 1
        for x in back:
            print('[id:{:>2d}]  完成度 {:>2d}%  {}'.format(i,x['per'],x['name']))
            i+=1
        i = int(input('\n请输入需要刷时长的课程id（id为上方[]内的序号）: '))

        cid = str(back[i - 1]['cid'])
        url = 'https://welearn.sflep.com/student/course_info.aspx?cid=' + cid
        req = session.get(url,headers={'Referer':'https://welearn.sflep.com/student/index.aspx'})
        uid = req.text[req.text.find('"uid":') + 6:req.text.find('"',req.text.find('"uid":') + 7) - 2]
        classid = req.text[req.text.find('classid=') + 8:req.text.find('&',req.text.find('classid=') + 9)]


        url = 'https://welearn.sflep.com/ajax/StudyStat.aspx'
        req = session.get(url,params={'action':'courseunits','cid':cid,'uid':uid},headers={'Referer':'https://welearn.sflep.com/student/course_info.aspx'})
        back = json.loads(req.text)['info']

        print('\n\n[id: 0]  按顺序刷全部单元学习时长')
        i = 0
        unitsnum = len(back)
        for x in back:
            i+=1
            print('[id:{:>2d}]  {}  {}'.format(i,x['unitname'],x['name']))
        unitidx = int(input('\n\n请选择要刷时长的单元id（id为上方[]内的序号，输入0为刷全部单元）： '))


        inputdata = input('\n\n\n模式1:每个练习增加指定学习时长，请直接输入时间\n如:希望每个练习增加30秒，则输入 30\n\n模式2:每个练习增加随机时长，请输入时间上下限并用英文逗号隔开\n如:希望每个练习增加10～30秒，则输入 10,30\n\n\n请严格按照以上格式输入: ')
        if(',' in inputdata):
            inputtime = eval(inputdata)
            mode = 2
        else:
            inputtime = int(inputdata)
            mode = 1


        if(unitidx == 0):
            i = 0
        else:
            i = unitidx - 1
            unitsnum = unitidx
        progressBar.total = 0
        for unit in range(i,unitsnum):
            url = 'https://welearn.sflep.com/ajax/StudyStat.aspx?action=scoLeaves&cid=' + cid + '&uid=' + uid + '&unitidx=' + str(unit) + '&classid=' + classid
            req = session.get(url,headers={'Referer':'https://welearn.sflep.com/student/course_info.aspx?cid=' + cid})
            back = json.loads(req.text)['info']
            for x in back:
                if(mode == 1):
                    learntime = inputtime
                else:
                    learntime = random.randint(inputtime[0],inputtime[1])
                wait_running(thread_max - 1)
                nt = NewThread(learntime,x)
                nt.start()
                time.sleep(0.1)
        wait_running(0)

        if (unitidx == 0):
            break
        else:
            print('回到选课处！！\n\n\n\n')
except KeyboardInterrupt:
    forceQuit = True
    progressBar.write('正在退出所有线程...')
    wait_running(0)
    print('\n已停止所有线程')
progressBar.close()
printline()
print("出错课程：")
for x in errorCourcesList:
    print(x)
print()
print("已完成课程：")
for x in finishedCourcesList:
    print("时长：", str(x[1] // 60) + "分" + str(x[1] % 60) + "秒    [", x[0])
print()

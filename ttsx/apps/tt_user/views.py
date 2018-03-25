from django.shortcuts import render,redirect
from django.http import HttpResponse,JsonResponse
from django.views.generic.base import View
from .models import User
import re
from django.core.mail import send_mail
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer,SignatureExpired
from celery_tasks.tasks import send_user_active
from django.contrib.auth import authenticate,login,logout
# Create your views here.
# def register(request):
#     # 获取请求方法，判断是GET/POST请求
#     if request.method == 'GET':
#         # 处理GET请求，返回注册页面
#         return render(request, 'register.html')
#     else:
#         # 处理POST请求，实现注册逻辑
#         return HttpResponse("这里实现注册逻辑")

class RegisterViews(View):
    """类视图：处理注册"""
    def get(self,request):
        """处理GET请求，返回注册页面"""
        return render(request, 'register.html',{'title':'注册'})

    def post(self,request):
        # 接收数据
        dict = request.POST
        uname = dict.get('user_name')
        upwd = dict.get('pwd')
        cpwd = dict.get('cpwd')
        uemail = dict.get('email')
        uallow = dict.get('allow')
        # 处理数据
        if not uallow:
            return render(request,'register.html',{'eerors_msg':'请同意协议'})
        if not all([uname,upwd,cpwd,uemail]):
            return render(request,'register.html',{'eerors_msg':'请将信息填完整'})

        # 用户错误提示的数据
        context = {
            'uname': uname,
            'upwd': upwd,
            'cpwd': cpwd,
            'email': uemail,
            'err_msg': '',
            'title': '注册处理'
        }

        if cpwd != upwd:
            return render(request,'register.html',{'eerors_msg':'两次密码不一致'})
        if User.objects.filter(username=uname).count()>0:
            return render(request,'register.html',{'eerors_msg':'用户已经存在'})
        if not re.match(r'[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}',uemail):
            return render(request,'register.html',{'eerors_msg':'邮箱格式不正确'})
        # 创建用户对象
        user = User.objects.create_user(uname,uemail,upwd)
        user.is_active = False
        user.save()
        # # 将账号信息进行加密
        # serializer = Serializer(settings.SECRET_KEY, 60 * 60 * 2)
        # value = serializer.dumps({'id': user.id})  # 返回bytes
        # value = value.decode()  # 转成字符串，用于拼接地址
        # # 向用户发送邮件
        # msg ='<a href="http://127.0.0.1:8000/user/active/%s">点击激活</a>'%value
        # send_mail('天天生鲜账号激活','',settings.EMAIL_FROM,[uemail],html_message=msg)

        send_user_active.delay(user.id,user.email)

        # 给出响应
        """处理POST请求，实现注册逻辑"""

        return HttpResponse("请在俩小时内激活")

def active(request,value):
    serializer = Serializer(settings.SECRET_KEY)
    try:
        dict = serializer.loads(value)
        userid = dict.get('id')
        # 激活账户
        user = User.objects.get(pk=userid)
        user.is_active = True
        user.save()
        #转向登陆页面
        return redirect('/user/login')
    except SignatureExpired as e:
        return HttpResponse('激活已经过期')

def exists(request):
    '判断用户名或邮箱是否存在'
    uname=request.GET.get('uname')
    if uname is not None:
        #查询用户名是否存在
        result=User.objects.filter(username=uname).count()
    return JsonResponse({'result':result})

class LoginView(View):
    def get(self,request):
        uname=request.COOKIES.get('uname','')
        return render(request,'login.html',{'title':'登录','uname':uname})
    def post(self,request):
        #接收数据
        dict=request.POST
        uname=dict.get('username')
        pwd=dict.get('pwd')
        remember=dict.get('remember')

        #构造返回值
        context={
            'title':'登录处理',
            'uname':uname,
            'pwd':pwd,
            'err_msg': '请填写完成信息'
        }

        #验证是否填写数据
        if not all([uname,pwd]):
            return render(request,'login.html',context)

        #验证用户名、密码是否正确
        user=authenticate(username=uname,password=pwd)
        if user is None:
            context['err_msg']='用户名或密码错误'
            return render(request,'login.html',context)

        #判断用户是否激活
        if not user.is_active:
            context['err_msg']='请到邮箱中激活账户'
            return render(request,'login.html',context)

        #记录状态
        login(request,user)

        response=redirect('/user/info')

        #是否记住用户名
        if remember is not None:
            response.set_cookie('uname',uname,expires=60*60*24*7)
        else:
            response.delete_cookie('uname')

        # 转向用户中心
        return response

def logout_user(request):
    logout(request)
    return redirect('/user/login')




import shutil
import sys
import os
import subprocess
import tempfile
import codecs
from fastrunner.utils import loader
import yaml,copy,json
from fastrunner import models
from httprunner.api import HttpRunner
from django.core.exceptions import ObjectDoesNotExist,MultipleObjectsReturned
from fastrunner.utils.loader import parse_summary
from fastrunner.utils.parser import Format
import traceback
from fastrunner.utils.loader import save_summary
from fastrunner.utils.tree import getNodeIdList

EXEC = sys.executable
#TODO：所有的runcase的地方，都需要增加try catch，并且前台输出后台运行的相关报错
'''为什么要做日志输入打印内容？
httprunner升级到2.0之后，有专门的的parse函数，先去整体解析所有的api，如果出现某个变量未定义，还未真正执行case的时候，就报错退出了。
httprunner的1.5版本不存在该问题
'''

if 'uwsgi' in EXEC:
    EXEC = "/usr/bin/python3"

class DebugCode(object):

    def __init__(self, code):
        self.__code = code
        self.resp = None
        self.temp = tempfile.mkdtemp(prefix='FasterRunner')

    def run(self):
        """ dumps debugtalk.py and run
        """
        try:
            file_path = os.path.join(self.temp, "debugtalk.py")
            loader.FileLoader.dump_python_file(file_path, self.__code)
            self.resp = decode(subprocess.check_output([EXEC, file_path], stderr=subprocess.STDOUT, timeout=60))

        except subprocess.CalledProcessError as e:
            self.resp = decode(e.output)

        except subprocess.TimeoutExpired:
            self.resp = 'RunnerTimeOut'

        shutil.rmtree(self.temp)


def decode(s):
    try:
        return s.decode('utf-8')

    except UnicodeDecodeError:
        return s.decode('gbk')

class RunMetaCls(type):
    def __new__(cls, name, bases, attrs, **kwargs):
        super_new = super().__new__

        parents = [b for b in bases if isinstance(b,Run)]
        if not parents:
            return super_new(cls,name,bases,attrs)

        new_class = super_new(cls, name, bases, attrs, **kwargs)
        attr_meta = attrs.pop('Meta',None)
        if(attr_meta == None):
            return new_class
        '''
        TODO:这里预留位置，用来加载：
            子类中MetaCls内部类定义的
                执行顺序：正序还是倒序，顺序还是随机？
                测试用例执行完成后，是否删除刚刚执行的目录
                执行类型，是api还是case还是suite？
                    根据当前执行类型的考虑，有以下几种执行类型的值：
                        debugapi 在api编辑页面中请求 单个调试api
                        singleapi 在apiapi菜单页面中 单个执行api
                        debugapiinstep 在步骤集或者案例中，调试和执行单个步骤
                        apitree 执行api集合
                        stepsettree 执行步骤集集合
                        testcasetree 执行测试用例集合
                
        '''
        return new_class

class Run():
    '''
    TODO:
        在每个函数前增加一个装饰器，对errormsg进行校验，如果errormsg有值，要跳出并报错
    '''
    '''
    TODO:
        存在一个诡异的问题，httprunner源码在处理validate中的内容的时候，如果字符串中带$，会当做LazyString处理
        虽然还不太理解LaztString的含义，但是如果validate中包含了$，就会导致用例执行完返回response时，django无法正确处理这个LazyString对象
        暂时能想到的方法是，如果validate中包含了$，其来源很可能是output或者extract中的数据，这样可以手动解析一下，不让其真实的案例中包含$
    '''
    '''
    _suiteQuerySet
    _project  项目ID
    _relation  如果执行的是tree，对应的是tree的ID
    _projectPath  实例化路径
    _configId  传入的配置ID
    ApiIdList  需要执行的API ID的集合
    StepsSetIdList  需要执行的步骤集 ID的集合
    TestCaseIdList  需要执行的用例 ID的集合
    ApiList  需要执行的API body的集合，以字典形式存储
        {
            'apiname1':apiBody1,
            'apiname2':apiBody2
        }
    StepsSetList  需要执行的步骤集 body的集合
    TestCaseList  需要执行的用例 body的集合
    _ApiPath  api文件存放的路径
    _StepsSetPath 步骤集文件存放的路径，实际和testcasepath一直
    _TestCasesPath 单个测试用例存放的路径
    _TestSuitesPath 测试用例集合存放的路径
    '''
    def __init__(self,**kwargs):
        #公共信息提取出来，每个案例/API都会用得到的变量
        self._projectId = kwargs.get('project')
        self._relation = kwargs.get('relation','')
        self._projectPath = kwargs['projectPath']
        self._configId = kwargs['config']
        self._type = kwargs.get('type')

        self.ApiList = {}
        self.StepsSetList = {}
        self.TestCaseList = {}

    def getConfig(self):
        if (self._configId != ''):
            try:
                configQuerySet = models.Config.objects.get(project = self._projectId,id=self._configId)
            except ObjectDoesNotExist:
                self.warningMsg = '无法查询对应的config配置，请手动检查'
                return
            except MultipleObjectsReturned:
                self.warningMsg = "查找到多条重复配置数据，请手动检查"
                return

            self.config = eval(configQuerySet.body)

    def getApiIdList(self):
        pass

    def getApiBodyList(self):
        pass

    def serializeApi(self):
        if(len(self.ApiList) == 0):
            return
        self._ApiPath = os.path.join(self._projectPath,'api')
        for ApiName,Apibody in self.ApiList.items():
            file=codecs.open(os.path.join(self._ApiPath,ApiName+'.yml'),'a+','utf-8')
            file.write(yaml.dump(Apibody,allow_unicode=True,default_flow_style=False))
            file.flush()
            file.close()


    def serializeSteps(self):
        pass
    def serializeCases(self):
        pass
    def serializeSuites(self):
        pass

    def serializeDebugtalk(self):
        try:
            queryset = models.Debugtalk.objects.get(project__id=self._projectId)
        except ObjectDoesNotExist:
            return
        except MultipleObjectsReturned:
            self.warningMsg = "查找到多条重复debugtalk.py文件，请手动检查"
            return

        self.debugtalk = queryset.code

        file = codecs.open(os.path.join(self._projectPath, 'debugtalk.py'), 'a+','utf-8')
        file.write(self.debugtalk)
        file.flush()
        file.close()

    def generateMapping(self):
        try:
            queryset = models.Variables.objects.filter(project_id=self._projectId)
        except ObjectDoesNotExist:
            self._mapping=None
            return

        self._mapping = {}
        for each in queryset:
            self._mapping[each.key] = each.value

    def convertListToDict(self,dictInList, type):
        if (type == 'variables'):
            if (len(dictInList) == 0):
                return ''
            tmp = {}
            for each in dictInList:
                for key, value in each.items():
                    tmp[key] = value
            return tmp

    def convertListToList(self,dict, type):
        if (type == 'extract'):
            if (len(dict) == 0):
                return ''
            tmp = []
            for each in dict:
                for key, value in each.items():
                    tmp.append({key: value})
            return tmp


class runTestCase(object):
    
    def __init__(self,**kwargs):
        self._project = kwargs['project']
        self._relation = kwargs['relation']
        self._projectPath = kwargs['projectPath']
        self._configId = kwargs['config']
        self._type = kwargs['type']
        '''
            debugapi 编辑页面单个调试api 
            singleapi api菜单页面中单个执行api
            singlestep 步骤集或测试用例菜单页面单个执行api
            apitree  执行多个api集合，这里传入的是tree中的id
            stepssettree  执行多个步骤集集合，这里传入的是tree中的id
            testcasestree  执行多个案例集合，这里传入的是tree中的id             
        '''


class RunSingleApi(Run):
    #debugapi 在apiList和apiBody页面中请求 单个调试api
    def __init__(self,**kwargs):
        #debug调试单个案例时，传入的是整个API Body，不需要获取API ID，只需要直接解析请求内容即可
        super().__init__(**kwargs)
        self.getConfig()
        self.getApiBodyList(kwargs['apiBody'])


    def getApiBodyList(self,api):
        if(self._type == 'debugapi'):
            self.ApiList[api['name']] = {
                'name': api.get('name', ''),
                'variables': self.convertListToDict(api.get('variables', []), 'variables'),
                'request': {
                    'url': api.get('request', {}).get('url', ''),
                    'method': api.get('request', {}).get('method', ''),
                    'headers': api.get('request', {}).get('headers', ''),
                    'params': api.get('request', {}).get('params', ''),
                    'data': api.get('request', {}).get('data', ''),
                    'json': api.get('request', {}).get('json', '')
                },
                'extract': api.get('extract', []),
                'validate': api.get('validate', [])
            }
        elif(self._type == 'singleapi'):
            try:
                querySet = models.API.objects.get(id=api['apiId'],isdeleted=0)
            except ObjectDoesNotExist:
                self.errorMsg = "没有找到要执行的案例"
                return
            except MultipleObjectsReturned:
                self.errorMsg = "查找到多条重复ID的API，请手动检查"
                return

            self.ApiList[querySet.name,eval(querySet.body)]
            self._projectId = querySet.project_id

    def serializeTestCase(self):
        #该函数只适用于单个步骤的调试
        if (len(self.ApiList) == 0):
            self.errormsg = "没有发现要执行的API，请检查逻辑是否存在问题"
            return
        self.TestCaseList=[]
        if(hasattr(self,'config')):
            self.TestCaseList.append({'config':self.config})
        for apiName,apiBody in self.ApiList.items():
            self.TestCaseList.append({'test':{'name':apiName,'api':'api'+'/'+apiName+'.yml'}})
        self.casePath = os.path.join(self._projectPath, 'testcases')
        if (os.path.exists(os.path.join(self.casePath, 'apitreetest' + '.yml'))):
            return
        file = codecs.open(os.path.join(self.casePath, 'debugapi' + '.yml'), 'a+', 'utf-8')
        file.write(yaml.dump(self.TestCaseList,allow_unicode=True, default_flow_style=False))
        file.flush()

    def run(self):
        runner = HttpRunner(failfast=False)
        runner.run(self.casePath, mapping=self._mapping)
        self.summary = parse_summary(runner.summary)























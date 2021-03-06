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
from fastrunner.utils.loader import parse_summary,new_parse_summary
from fastrunner.utils.parser import Format
import traceback
from fastrunner.utils.loader import save_summary
from fastrunner.utils.tree import getNodeIdList
from fastrunner.utils.parser import Format, Parse,SuiteFormat,SuiteBodyFormat,TestSuiteFormat,suiteFormat,caseFormat
import collections




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
        # attr_meta = attrs.pop('Meta',None)
        # if(attr_meta == None):
        #     return new_class
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

        """
        以下所有List内容均为list内部嵌套字典形式，
        所有实例化函数都以此为标准进行操作，
        这样就可以将实例化操作全部提取成父类函数了如
        apiList：
            {'login':loginBody},
            {'logout':logoytBody},
            {'save':saveBody},
        """
        self.ApiList = {}
        self.TestCaseList = {}
        self.TestSuiteList = {}

        self.getConfig()


    def getConfig(self):
        if (self._configId != ''):
            try:
                configQuerySet = models.Config.objects.get(id=self._configId)
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
            queryset = None
        except MultipleObjectsReturned:
            self.warningMsg = "查找到多条重复debugtalk.py文件，请手动检查"
            queryset = None

        self.debugtalk = queryset.code if(queryset != None) else ""

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


class RunSingleApi(Run, metaclass=RunMetaCls):
    #debugapi 在apiBody页面中请求 单个调试api
    #singleapi 在apiList页面中请求 单个执行api
    def __init__(self,**kwargs):
        #debug调试单个案例时，传入的是整个API Body，不需要获取API ID，只需要直接解析请求内容即可
        super().__init__(**kwargs)
        self.getApiBody(apibody=kwargs.get('apiBody',None),apiId=kwargs.get('apiId',None))


    def getApiBody(self,apibody = None,apiId=None):
        if(self._type == 'debugapi'):
            self.ApiList[apibody['name']] = {
                'name': apibody.get('name', ''),
                'variables': self.convertListToDict(apibody.get('variables', []), 'variables'),
                'request': {
                    'url': apibody.get('request', {}).get('url', ''),
                    'method': apibody.get('request', {}).get('method', ''),
                    'headers': apibody.get('request', {}).get('headers', ''),
                    'params': apibody.get('request', {}).get('params', ''),
                    'data': apibody.get('request', {}).get('data', ''),
                    'json': apibody.get('request', {}).get('json', '')
                },
                'extract': apibody.get('extract', []),
                'validate': apibody['validate']
                }
        elif(self._type == 'singleapi'):
            try:
                querySet = models.API.objects.get(id=apiId,isdeleted=0)
            except ObjectDoesNotExist:
                self.errorMsg = "没有找到要执行的案例"
                return
            except MultipleObjectsReturned:
                self.errorMsg = "查找到多条重复ID的API，请手动检查"
                return

            self.ApiList[querySet.name] = eval(querySet.body)
            self._projectId = querySet.project_id

    def serializeTestCase(self):
        if (len(self.ApiList) == 0):
            self.errormsg = "没有发现要执行的API，请检查逻辑是否存在问题"
            return

        for apiName,apiBody in self.ApiList.items():
            self.TestCaseList[apiName] = [{'test':apiBody}]
        self.casePath = os.path.join(self._projectPath, 'testcases')
        for caseName,caseBody in self.TestCaseList.items():
            if (os.path.exists(os.path.join(self.casePath, caseName + '.yml'))):
                return
            file = codecs.open(os.path.join(self.casePath, caseName + '.yml'), 'a+', 'utf-8')
            file.write(yaml.dump(caseBody,allow_unicode=True, default_flow_style=False))
            file.flush()

    def serializeTestSuite(self):
        if (len(self.TestCaseList) == 0):
            self.errormsg = "没有发现要执行的API，请检查逻辑是否存在问题"
            return
        tmpTestSuiteList ={}
        if(hasattr(self,'config')):
            tmpTestSuiteList['config'] = self.config
            self.parameters = tmpTestSuiteList['config'].get('parameters',None)

        tmpTestSuiteList['testcases'] = {}
        for caseName,caseBody in self.TestCaseList.items():
            tmpTestSuiteList['testcases'].update({
                caseName:{
                    'testcase':'testcases/'+ caseName+'.yml',
                }})
            if(hasattr(self,'parameters') and getattr(self,'parameters') != None ):
                tmpTestSuiteList['testcases'][caseName].update(
                    {
                        'parameters': self.parameters
                    }
                )
        suiteName = list(tmpTestSuiteList['testcases'].keys())[0]
        self.TestSuiteList[suiteName] = tmpTestSuiteList
        self.suitePath = os.path.join(self._projectPath, 'testsuites')
        for suiteName,suiteBody in self.TestSuiteList.items():
            if (os.path.exists(os.path.join(self.suitePath, suiteName + '.yml'))):
                return
            file = codecs.open(os.path.join(self.suitePath, suiteName + '.yml'), 'a+', 'utf-8')
            file.write(yaml.dump(suiteBody,allow_unicode=True, default_flow_style=False))
            file.flush()

    def run(self):
        runner = HttpRunner(failfast=False)
        runner.run(self.suitePath, mapping=self._mapping)
        self.summary = parse_summary(runner.summary)

class RunTree(Run, metaclass=RunMetaCls):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        if(kwargs['type'] == 'apiTree'):
            self.getAllApi()
        if (kwargs['type'] == 'suiteTree'):
            self.getAllSuite()
            self.getAllApi()
        if (kwargs['type'] == 'caseTree'):
            self.getAllCase()
            self.getAllSuite()
            self.getAllApi()

    def getAllCase(self):
        try:
            self.CaseList = {}
            tree = models.Relation.objects.get(project__id=self._projectId, type=2)
            body = eval(tree.tree)
            nodeList = getNodeIdList(self._relation, body) if len(self._relation) != '' else []
            CaseList = models.TestCase.objects.filter(relation__in=nodeList, project=self._projectId, isdeleted=0)
        except ObjectDoesNotExist:
            self.errormsg = '没有找到对应节点的用例，请手动检查'

        self.needTransApiToSuite = []
        for eachCase in CaseList:
            self.CaseList[eachCase.name] = eval(eachCase.body)
            for eachCaseStep in self.CaseList[eachCase.name]:
                if ('api' in eachCaseStep.keys()):
                    self.needTransApiToSuite.append(copy.deepcopy(eachCaseStep))

    def getAllSuite(self):
        self.SuiteList = {}
        if (self._type == 'suiteTree'):
            try:
                tree = models.Relation.objects.get(project__id=self._projectId, type=3)
                body = eval(tree.tree)
                nodeList = getNodeIdList(self._relation, body) if len(self._relation) != '' else []
                SuiteList = models.TestSuite.objects.filter(relation__in=nodeList, project=self._projectId, isdeleted=0)
            except ObjectDoesNotExist:
                self.errormsg = '没有找到对应节点的用例，请手动检查'

            for eachSuite in SuiteList:
                self.SuiteList[eachSuite.name] = eval(eachSuite.body)
                for eachStep in self.SuiteList[eachSuite.name]:
                    eachStep['api'] = 'api/'+eachStep['api']+'.yml'
        elif(self._type == 'caseTree'):
            SuiteIdList = []
            for eachCaseName,eachCaseBody in self.CaseList.items():
                for eachStep in eachCaseBody:
                    if('api' in eachStep.keys()):
                        if(eachCaseName in self.SuiteList.keys()):
                            self.SuiteList[eachCaseName].append(eachStep)
                        else:
                            self.SuiteList[eachCaseName] = [eachStep,]
                    if('testcase' in eachStep.keys()):
                        # SuiteIdList.append(eachStep['id'])
                        try:
                            suite = models.TestSuite.objects.get(id=eachStep['id'], project=self._projectId,
                                                                        isdeleted=0)
                        except ObjectDoesNotExist:
                            self.errormsg = '没有找到对应节点的用例，请手动检查'

                        for each in eval(suite.body):
                            self.SuiteList[eachCaseName].append(each)
                for eachStep in self.SuiteList[eachCaseName]:
                    eachStep['api'] = 'api/' + eachStep['api'] + '.yml'



            # try:
            #     SuiteList = models.TestSuite.objects.filter(id__in=SuiteIdList, project=self._projectId, isdeleted=0)
            # except ObjectDoesNotExist:
            #     self.errormsg = '没有找到对应节点的用例，请手动检查'
            #
            # for eachSuite in SuiteList:
            #     self.SuiteList[eachSuite.name] = eval(eachSuite.body)
            #     for eachStep in self.SuiteList[eachSuite.name]:
            #         eachStep['api'] = 'api/' + eachStep['api'] + '.yml'
            #
            # for each in self.needTransApiToSuite:
            #     tmpname = each['api']
            #     each['api'] = 'api/' + each['api'] + '.yml'
            #     self.SuiteList[tmpname] = [each,]



    def getAllApi(self):
        if(self._type == 'apiTree'):
            try:
                tree = models.Relation.objects.get(project__id=self._projectId, type=1)
                body = eval(tree.tree)
                nodeList = getNodeIdList(self._relation, body) if len(self._relation) != '' else []
                APIList = models.API.objects.filter(relation__in=nodeList, project=self._projectId, isdeleted=0)
            except ObjectDoesNotExist:
                self.errormsg = '没有找到对应节点的用例，请手动检查'

            for each in APIList:
                self.ApiList[each.name] = eval(each.body)
        elif(self._type == 'suiteTree'):
            ApiIdList = []
            for eachSuite in self.SuiteList.values():
                for eachApi in eachSuite:
                    ApiIdList.append(eachApi['id'])
            try:
                APIList = models.API.objects.filter(id__in=ApiIdList, project=self._projectId, isdeleted=0)
            except ObjectDoesNotExist:
                self.errormsg = '没有找到对应节点的用例，请手动检查'
            for each in APIList:
                self.ApiList[each.name] = eval(each.body)
        elif (self._type == 'caseTree'):
            ApiIdList = []
            for eachSuite in self.SuiteList.values():
                for eachApi in eachSuite:
                    ApiIdList.append(eachApi['id'])
            for eachCase in self.CaseList.values():
                for eachCaseStep in eachCase:
                    if ('api' in eachCaseStep.keys()):
                        ApiIdList.append(eachCaseStep['id'])
            try:
                APIList = models.API.objects.filter(id__in=ApiIdList, project=self._projectId, isdeleted=0)
            except ObjectDoesNotExist:
                self.errormsg = '没有找到对应节点的用例，请手动检查'

            for each in APIList:
                self.ApiList[each.name] = eval(each.body)

    def serializeApi(self):
        if(len(self.ApiList) == 0):
            return
        self._ApiPath = os.path.join(self._projectPath,'api')
        for ApiName,Apibody in self.ApiList.items():
            file=codecs.open(os.path.join(self._ApiPath,ApiName+'.yml'),'a+','utf-8')
            file.write(yaml.dump(Apibody,allow_unicode=True,default_flow_style=False))
            file.flush()
            file.close()

    def serializeTestCase(self):
        if (len(self.ApiList) == 0):
            self.errormsg = "没有发现要执行的API，请检查逻辑是否存在问题"
            return
        if (self._type == 'apiTree'):
            tmpApiTreeList = []
            for apiName,apiBody in self.ApiList.items():
                tmpApiTreeList.append({'test':apiBody})
            self.TestCaseList['apitreetest'] = tmpApiTreeList
        elif(self._type == 'suiteTree'):
            for suiteName, suiteBody in self.SuiteList.items():
                for eachsStep in suiteBody:
                    if(suiteName not in self.TestCaseList.keys()):
                        self.TestCaseList[suiteName] = ([{'test': eachsStep}])
                        continue
                    self.TestCaseList[suiteName].append({'test': eachsStep})
        elif (self._type == 'caseTree'):
            for suiteName, suiteBody in self.SuiteList.items():
                for eachsStep in suiteBody:
                    if (suiteName not in self.TestCaseList.keys()):
                        self.TestCaseList[suiteName] = ([{'test': eachsStep}])
                        continue
                    self.TestCaseList[suiteName].append({'test': eachsStep})
        self.casePath = os.path.join(self._projectPath, 'testcases')
        for caseName, caseBody in self.TestCaseList.items():
            if (os.path.exists(os.path.join(self.casePath, caseName + '.yml'))):
                return
            file = codecs.open(os.path.join(self.casePath, caseName + '.yml'), 'a+', 'utf-8')
            file.write(yaml.dump(caseBody, allow_unicode=True, default_flow_style=False))
            file.flush()

    def serializeTestSuite(self):
        if (len(self.TestCaseList) == 0):
            self.errormsg = "没有发现要执行的Case，请检查逻辑是否存在问题"
            return
        tmpTestSuiteList ={}
        if(hasattr(self,'config')):
            self.parameters = self.config.pop('parameters') if('parameters' in self.config.keys()) else None
            tmpTestSuiteList['config'] = self.config
        if(self._type in ('apiTree','suiteTree')):
            for caseName, caseBody in self.TestCaseList.items():
                tmpTestSuiteList['testcases'] = {}
                tmpTestSuiteList['testcases'].update({
                    caseName: {
                        'testcase': 'testcases/' + caseName + '.yml',
                    }})
                if (hasattr(self, 'parameters') and getattr(self, 'parameters') != None):
                    tmpTestSuiteList['testcases'][caseName].update(
                        {
                            'parameters': self.parameters
                        }
                    )
                self.TestSuiteList[caseName] =  copy.deepcopy(tmpTestSuiteList)
        elif(self._type == 'caseTree'):
            for caseName, caseBody in self.CaseList.items():
                self.TestSuiteList[caseName] = {
                    'testcases':{caseName:{
                        'testcase': 'testcases/' + caseName + '.yml'
                        }
                    }
                }

                # tmpApiContent = {
                #     'testcase': 'testcases/' + eachStep['api'] + '.yml'
                # }
                #
                #
                # tmpTestSuiteList['testcases'] = collections.OrderedDict()
                # for eachStep in caseBody:
                #     if('api' in eachStep):
                #         tmpName = eachStep['api']
                #         tmpApiContent = {
                #                 'testcase': 'testcases/' + eachStep['api'] + '.yml'
                #             }
                #         tmpApiContent.update(eachStep)
                #         del tmpApiContent['api']
                #         tmpTestSuiteList['testcases'].update({
                #             eachStep['api']: tmpApiContent})
                #     if ('testcase' in eachStep):
                #         tmpName = eachStep['testcase']
                #         tmpTestSuiteList['testcases'].update({
                #             eachStep['testcase']: {
                #                 'testcase': 'testcases/' + eachStep['testcase'] + '.yml',
                #             }})
                #     if (hasattr(self, 'parameters') and getattr(self, 'parameters') != None):
                #         tmpTestSuiteList['testcases'][tmpName].update(
                #             {
                #                 'parameters': self.parameters
                #             }
                #         )
                # self.TestSuiteList[caseName] =  copy.deepcopy(tmpTestSuiteList)
        self.suitePath = os.path.join(self._projectPath, 'testsuites')
        for suiteName,suiteBody in self.TestSuiteList.items():
            if (os.path.exists(os.path.join(self.suitePath, suiteName + '.yml'))):
                return
            file = codecs.open(os.path.join(self.suitePath, suiteName + '.yml'), 'a+', 'utf-8')
            filecontent = yaml.dump(suiteBody,allow_unicode=True, default_flow_style=False)
            file.write(yaml.dump(suiteBody,allow_unicode=True, default_flow_style=False))
            file.flush()

    def run(self):
        runner = HttpRunner(failfast=False)
        runner.run(self.suitePath, mapping=self._mapping)
        self.summary = parse_summary(runner.summary)

    def getNodeIdList(self,nodeId, treeBody):
        def getAllChildId(self, treeList):
            nodeList = []
            for each in treeList:
                nodeList.append(each['id'])
                if (isinstance(each['children'], list) and len(each['children']) > 0):
                    nodeList.extend(getAllChildId(each['children']))
            return nodeList

        nodeList = []
        for each in treeBody:
            if (isinstance(nodeId, list)):
                for eachNode in nodeId:
                    if (each['id'] == int(eachNode)):
                        nodeList.append(each['id'])
                        if (len(each['children']) > 0):
                            nodeList.extend(getAllChildId(each['children']))
                        break
                    else:
                        nodeList.extend(getNodeIdList(nodeId, each['children']))
            else:
                if (each['id'] == int(nodeId)):
                    nodeList.append(each['id'])
                    if (len(each['children']) > 0):
                        nodeList.extend(getAllChildId(each['children']))
                    break
                else:
                    nodeList.extend(getNodeIdList(nodeId, each['children']))
        return nodeList

class RunSingleApiInStep(Run, metaclass=RunMetaCls):
    def __init__(self,**kwargs):
        #在stepbody或者casebody页面，调试api时，传入的内容是原api的id和修改后需要覆盖的casebody
        super().__init__(**kwargs)
        self.getApiBody(kwargs.get('apiId'))
        self.getStepBody(kwargs.get('apiBody',None),kwargs.get('index',None))


    def getApiBody(self,apiId):
        try:
            querySet = models.API.objects.get(id=apiId,isdeleted=0)
        except ObjectDoesNotExist:
            self.errorMsg = "没有找到要执行的案例"
            return
        except MultipleObjectsReturned:
            self.errorMsg = "查找到多条重复ID的API，请手动检查"
            return

        self.ApiList[querySet.name] = eval(querySet.body)
        self._projectId = querySet.project_id

    def getStepBody(self,stepBody,index):
        self.StepsSetList = {}
        if(stepBody != None):
            self.StepsSetList[stepBody['name']] = {
                'name': stepBody.get('name', ''),
                'srcName': stepBody.get('srcName', ''),
                'variables': stepBody.get('variables', []).get('variables', []),
                'request': {
                    'url': stepBody.get('url'),
                },
                'extract': stepBody.get('extract', []).get('extract', []),
                'validate': stepBody.get('validate', []).get('validate', [])
            }
        else:
            suite = suiteFormat(project=self._projectId, relation=self._relation)
            suite.getSpecStep(index)
            self.StepsSetList[suite.stepBody['api']] = {
                'name': suite.stepBody.get('api', ''),
                'srcName': suite.stepBody.get('api', ''),
                'variables': suite.stepBody.get('variables', []),
                'extract': suite.stepBody.get('extract', []),
                'validate': suite.stepBody.get('validate', [])
            }

    def serializeTestCase(self):
        #该函数只适用于单个步骤的调试
        if (len(self.ApiList) == 0):
            self.errormsg = "没有发现要执行的API，请检查逻辑是否存在问题"
            return
        for apiName,apiBody in self.StepsSetList.items():
            apiBody.update({'api': 'api' + '/' + apiBody['srcName'] + '.yml'})
            self.TestCaseList.update({apiName:[{'test':apiBody}]})
        self.casePath = os.path.join(self._projectPath, 'testcases')
        for caseName,caseBody in self.TestCaseList.items():
            if (os.path.exists(os.path.join(self.casePath, caseName + '.yml'))):
                return
            file = codecs.open(os.path.join(self.casePath, caseName + '.yml'), 'a+', 'utf-8')
            file.write(yaml.dump(caseBody,allow_unicode=True, default_flow_style=False))
            file.flush()

    def serializeTestSuite(self):
        if (len(self.TestCaseList) == 0):
            self.errormsg = "没有发现要执行的API，请检查逻辑是否存在问题"
            return
        tmpTestSuiteList ={}
        if(hasattr(self,'config')):
            tmpTestSuiteList['config'] = self.config
            self.parameters = tmpTestSuiteList['config'].get('parameters',None)

        tmpTestSuiteList['testcases'] = {}
        for caseName,caseBody in self.TestCaseList.items():
            tmpTestSuiteList['testcases'].update({
                caseName:{
                    'testcase':'testcases/'+ caseName+'.yml',
                }})
            if(hasattr(self,'parameters') and getattr(self,'parameters') != None ):
                tmpTestSuiteList['testcases'][caseName].update(
                    {
                        'parameters': self.parameters
                    }
                )
        suiteName = list(tmpTestSuiteList['testcases'].keys())[0]
        self.TestSuiteList[suiteName] = tmpTestSuiteList
        self.suitePath = os.path.join(self._projectPath, 'testsuites')
        for suiteName,suiteBody in self.TestSuiteList.items():
            if (os.path.exists(os.path.join(self.suitePath, suiteName + '.yml'))):
                return
            file = codecs.open(os.path.join(self.suitePath, suiteName + '.yml'), 'a+', 'utf-8')
            file.write(yaml.dump(suiteBody,allow_unicode=True, default_flow_style=False))
            file.flush()


    def run(self):
        runner = HttpRunner(failfast=False)
        runner.run(self.suitePath, mapping=self._mapping)
        self.summary = parse_summary(runner.summary)


class RunSingleApiInCase(Run, metaclass=RunMetaCls):
    #TODO：要和上面的类合并一下，先这样吧
    def __init__(self,**kwargs):
        #在stepbody或者casebody页面，调试api时，传入的内容是原api的id和修改后需要覆盖的casebody
        super().__init__(**kwargs)
        if('apiId' in kwargs.keys()):
            self.type='api'
            self.getApiBody(kwargs.get('apiId'))
            self.getStepBody(kwargs.get('apiBody',None),kwargs.get('index',None))
        elif('suiteId' in kwargs.keys()):
            self.type="suite"
            self.getSuiteBody(kwargs.get('suiteId'))
            self.getApiBody(self.tmpApiList)

    def getSuiteBody(self,suiteId):
        self.suite = suiteFormat(id=suiteId)
        self.tmpApiList = []
        self.tmpStepList=[]
        for each in self.suite.tests:
            self.tmpApiList.append(each['id'])
            each.update({'api': 'api' + '/' + each['api'] + '.yml'})
            self.tmpStepList.append({'test':each})

    def getApiBody(self,apiIdList):
        apiList = []
        if(type(apiIdList).__name__ != 'list'):
            apiList = [apiIdList,]
        else:
            for value in self.tmpApiList:
                apiList.append(value)

        for each in apiList:
            try:
                querySet = models.API.objects.get(id=each,isdeleted=0)
            except ObjectDoesNotExist:
                self.errorMsg = "没有找到要执行的案例"
                return
            except MultipleObjectsReturned:
                self.errorMsg = "查找到多条重复ID的API，请手动检查"
                return

            self.ApiList[querySet.name] = eval(querySet.body)
            self._projectId = querySet.project_id

    def getStepBody(self,stepBody,index):
        self.StepsSetList = {}
        if(stepBody != None):
            self.StepsSetList[stepBody['name']] = {
                'name': stepBody.get('name', ''),
                'srcName': stepBody.get('srcName', ''),
                'variables': stepBody.get('variables', []).get('variables', []),
                'request': {
                    'url': stepBody.get('url'),
                },
                'extract': stepBody.get('extract', []).get('extract', []),
                'validate': stepBody.get('validate', []).get('validate', [])
            }
        else:
            suite = caseFormat(project=self._projectId, relation=self._relation)
            suite.getSpecStep(index)
            self.StepsSetList[suite.stepBody['api']] = {
                'name': suite.stepBody.get('api', ''),
                'srcName': suite.stepBody.get('api', ''),
                'variables': suite.stepBody.get('variables', []),
                'extract': suite.stepBody.get('extract', []),
                'validate': suite.stepBody.get('validate', [])
            }

    def serializeTestCase(self):
        #该函数只适用于单个步骤的调试
        if (len(self.ApiList) == 0):
            self.errormsg = "没有发现要执行的API，请检查逻辑是否存在问题"
            return

        if(self.type=='api'):
            for apiName,apiBody in self.StepsSetList.items():
                apiBody.update({'api': 'api' + '/' + apiBody['srcName'] + '.yml'})
                self.TestCaseList.update({apiName:[{'test':apiBody}]})
            self.casePath = os.path.join(self._projectPath, 'testcases')
        elif(self.type=='suite'):
            self.TestCaseList.update({self.suite.getName(): self.tmpStepList})

        self.casePath = os.path.join(self._projectPath, 'testcases')
        for caseName, caseBody in self.TestCaseList.items():
            if (os.path.exists(os.path.join(self.casePath, caseName + '.yml'))):
                return
            file = codecs.open(os.path.join(self.casePath, caseName + '.yml'), 'a+', 'utf-8')
            file.write(yaml.dump(caseBody, allow_unicode=True, default_flow_style=False))
            file.flush()

    def serializeTestSuite(self):
        if (len(self.TestCaseList) == 0):
            self.errormsg = "没有发现要执行的API，请检查逻辑是否存在问题"
            return
        tmpTestSuiteList ={}
        if(hasattr(self,'config')):
            tmpTestSuiteList['config'] = self.config
            self.parameters = tmpTestSuiteList['config'].get('parameters',None)

        tmpTestSuiteList['testcases'] = {}
        for caseName,caseBody in self.TestCaseList.items():
            tmpTestSuiteList['testcases'].update({
                caseName:{
                    'testcase':'testcases/'+ caseName+'.yml',
                }})
            if(hasattr(self,'parameters') and getattr(self,'parameters') != None ):
                tmpTestSuiteList['testcases'][caseName].update(
                    {
                        'parameters': self.parameters
                    }
                )
        suiteName = list(tmpTestSuiteList['testcases'].keys())[0]
        self.TestSuiteList[suiteName] = tmpTestSuiteList
        self.suitePath = os.path.join(self._projectPath, 'testsuites')
        for suiteName,suiteBody in self.TestSuiteList.items():
            if (os.path.exists(os.path.join(self.suitePath, suiteName + '.yml'))):
                return
            file = codecs.open(os.path.join(self.suitePath, suiteName + '.yml'), 'a+', 'utf-8')
            file.write(yaml.dump(suiteBody,allow_unicode=True, default_flow_style=False))
            file.flush()


    def run(self):
        runner = HttpRunner(failfast=False)
        runner.run(self.suitePath, mapping=self._mapping)
        self.summary = parse_summary(runner.summary)








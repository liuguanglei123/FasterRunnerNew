import json
from enum import Enum
from fastrunner.models import FileBinary
import copy
from fastrunner import models

class FileType(Enum):
    """
    文件类型枚举
    """
    string = 1
    int = 2
    float = 3
    bool = 4
    list = 5
    dict = 6
    file = 7


class Format(object):
    """
    解析标准HttpRunner脚本 前端->后端
    """

    def __init__(self, body, level='test'):
        """
        body => {
                    header: header -> [{key:'', value:'', desc:''},],
                    request: request -> {
                        form: formData - > [{key: '', value: '', type: 1, desc: ''},],
                        json: jsonData -> {},-
                        params: paramsData -> [{key: '', value: '', type: 1, desc: ''},]
                        files: files -> {"fields","binary"}
                    },
                    extract: extract -> [{key:'', value:'', desc:''}],
                    validate: validate -> [{expect: '', actual: '', comparator: 'equals', type: 1},],
                    variables: variables -> [{key: '', value: '', type: 1, desc: ''},],
                    hooks: hooks -> [{setup: '', teardown: ''},],
                    url: url -> string
                    method: method -> string
                    name: name -> string
                }
        """

        try:
            self.name = body.pop('name')

            self.__headers = body['header'].pop('header')
            self.__params = body['request']['params'].pop('params')
            self.__data = body['request']['form'].pop('data')
            self.__json = body['request'].pop('json')
            self.__files = body['request']['files'].pop('files')
            self.__variables = body['variables'].pop('variables')
            self.__setup_hooks = body['hooks'].pop('setup_hooks')
            self.__teardown_hooks = body['hooks'].pop('teardown_hooks')

            self.__desc = {
                "header": body['header'].pop('desc'),
                "data": body['request']['form'].pop('desc'),
                "files": body['request']['files'].pop('desc'),
                "params": body['request']['params'].pop('desc'),
                "variables": body['variables'].pop('desc'),
            }

            if level is 'test':
                self.url = body.pop('url')
                self.method = body.pop('method')

                self.__times = body.pop('times')
                self.__extract = body['extract'].pop('extract')
                self.__validate = body.pop('validate').pop('validate')
                self.__desc['extract'] = body['extract'].pop('desc')

            elif level is 'config':
                self.base_url = body.pop('base_url')
                self.__parameters = body['parameters'].pop('parameters')
                self.__desc["parameters"] = body['parameters'].pop('desc')

            self.__level = level
            self.testcase = None

            self.project = body.pop('project')
            self.relation = body.pop('nodeId')

        except KeyError:
            # project or relation
            pass

    def parse(self):
        """
        返回标准化HttpRunner "desc" 字段运行需去除
        """

        if self.__level is 'test':
            test = {
                "name": self.name,
                "times": self.__times,
                "request": {
                    "url": self.url,
                    "method": self.method
                },
                "desc": self.__desc
            }

            if self.__extract:
                test["extract"] = self.__extract
            if self.__validate:
                test['validate'] = self.__validate

        elif self.__level is 'config':
            test = {
                "name": self.name,
                "request": {
                    "base_url": self.base_url,
                },
                "desc": self.__desc
            }

            if self.__parameters:
                test['parameters'] = self.__parameters

        if self.__headers:
            test["request"]["headers"] = self.__headers
        if self.__params:
            test["request"]["params"] = self.__params
        if self.__data:
            test["request"]["data"] = self.__data
        if self.__json:
            test["request"]["json"] = self.__json
        if self.__files:
            test["request"]["files"] = self.__files
        if self.__variables:
            test["variables"] = self.__variables
        if self.__setup_hooks:
            test['setup_hooks'] = self.__setup_hooks
        if self.__teardown_hooks:
            test['teardown_hooks'] = self.__teardown_hooks

        self.testcase = test


class Parse(object):
    """
    标准HttpRunner脚本解析至前端 后端->前端
    """

    def __init__(self, body, level='test'):
        """
        body: => {
                "name": "get token with $user_agent, $os_platform, $app_version",
                "request": {
                    "url": "/api/get-token",
                    "method": "POST",
                    "headers": {
                        "app_version": "$app_version",
                        "os_platform": "$os_platform",
                        "user_agent": "$user_agent"
                    },
                    "json": {
                        "sign": "${get_sign($user_agent, $device_sn, $os_platform, $app_version)}"
                    },
                    "extract": [
                        {"token": "content.token"}
                    ],
                    "validate": [
                        {"eq": ["status_code", 200]},
                        {"eq": ["headers.Content-Type", "application/json"]},
                        {"eq": ["content.success", true]}
                    ],
                    "setup_hooks": [],
                    "teardown_hooks": []
                }
        """
        self.name = body.get('name')
        self.__request = body.get('request')  # header files params json data
        self.__variables = body.get('variables')
        self.__setup_hooks = body.get('setup_hooks', [])
        self.__teardown_hooks = body.get('teardown_hooks', [])
        self.__desc = body.get('desc')

        if level is 'test':
            self.__times = body.get('times', 1)  # 如果导入没有times 默认为1
            self.__extract = body.get('extract')
            self.__validate = body.get('validate')

        elif level is "config":
            self.__parameters = body.get("parameters")

        self.__level = level
        self.testcase = None

    @staticmethod
    def __get_type(content):
        """
        返回data_type 默认string
        """
        var_type = {
            "str": 1,
            "int": 2,
            "float": 3,
            "bool": 4,
            "list": 5,
            "dict": 6,
        }

        key = str(type(content).__name__)

        if key in ["list", "dict"]:
            content = json.dumps(content)
        else:
            content = str(content)
        return var_type[key], content

    def parse_http(self):
        """
        标准前端脚本格式
        """
        init = [{
            "key": "",
            "value": "",
            "desc": ""
        }]

        init_p = [{
            "key": "",
            "value": "",
            "desc": "",
            "type": 1
        }]

        #  初始化test结构
        test = {
            "name": self.name,
            "header": init,
            "request": {
                "data": init_p,
                "params": init_p,
                "json_data": ''
            },
            "variables": init_p,
            "hooks": [{
                "setup": "",
                "teardown": ""
            }]
        }

        if self.__level is 'test':
            test["times"] = self.__times
            test["method"] = self.__request['method']
            test["url"] = self.__request['url']
            test["validate"] = [{
                "expect": "",
                "actual": "",
                "comparator": "equals",
                "type": 1
            }]
            test["extract"] = init

            if self.__extract:
                test["extract"] = []
                for content in self.__extract:
                    for key, value in content.items():
                        test['extract'].append({
                            "key": key,
                            "value": value,
                            "desc": self.__desc["extract"][key]
                        })

            if self.__validate:
                test["validate"] = []
                for content in self.__validate:
                    for key, value in content.items():
                        obj = Parse.__get_type(value[1])
                        test["validate"].append({
                            "expect": obj[1],
                            "actual": value[0],
                            "comparator": key,
                            "type": obj[0]
                        })

        elif self.__level is "config":
            test["base_url"] = self.__request["base_url"]
            test["parameters"] = init

            if self.__parameters:
                test["parameters"] = []
                for content in self.__parameters:
                    for key, value in content.items():
                        test["parameters"].append({
                            "key": key,
                            "value": Parse.__get_type(value)[1],
                            "desc": self.__desc["parameters"][key]
                        })

        if self.__request.get('headers'):
            test["header"] = []
            for key, value in self.__request.pop('headers').items():
                test['header'].append({
                    "key": key,
                    "value": value,
                    "desc": self.__desc["header"][key]
                })

        if self.__request.get('data'):
            test["request"]["data"] = []
            for key, value in self.__request.pop('data').items():
                obj = Parse.__get_type(value)

                test['request']['data'].append({
                    "key": key,
                    "value": obj[1],
                    "type": obj[0],
                    "desc": self.__desc["data"][key]
                })

        if self.__request.get('files'):
            for key, value in self.__request.pop("files").items():
                size = FileBinary.objects.get(name=value).size
                test['request']['data'].append({
                    "key": key,
                    "value": value,
                    "size": size,
                    "type": 5,
                    "desc": self.__desc["files"][key]
                })

        if self.__request.get('params'):
            test["request"]["params"] = []
            for key, value in self.__request.pop('params').items():
                test['request']['params'].append({
                    "key": key,
                    "value": value,
                    "type": 1,
                    "desc": self.__desc["params"][key]
                })

        if self.__request.get('json'):
            test["request"]["json_data"] = \
                json.dumps(self.__request.pop("json"), indent=4,
                           separators=(',', ': '), ensure_ascii=False)
        if self.__variables:
            test["variables"] = []
            for content in self.__variables:
                for key, value in content.items():
                    obj = Parse.__get_type(value)
                    test["variables"].append({
                        "key": key,
                        "value": obj[1],
                        "desc": self.__desc["variables"][key],
                        "type": obj[0]
                    })

        if self.__setup_hooks or self.__teardown_hooks:
            test["hooks"] = []
            if len(self.__setup_hooks) > len(self.__teardown_hooks):
                for index in range(0, len(self.__setup_hooks)):
                    teardown = ""
                    if index < len(self.__teardown_hooks):
                        teardown = self.__teardown_hooks[index]
                    test["hooks"].append({
                        "setup": self.__setup_hooks[index],
                        "teardown": teardown
                    })
            else:
                for index in range(0, len(self.__teardown_hooks)):
                    setup = ""
                    if index < len(self.__setup_hooks):
                        setup = self.__setup_hooks[index]
                    test["hooks"].append({
                        "setup": setup,
                        "teardown": self.__teardown_hooks[index]
                    })

        self.testcase = test

def getApiFromSuite(queryset):
    apilist = []
    try:
        body = eval(queryset.body)
        for test in body['tests']:
            apilist.append(test['id'])
    except Exception as err:
        return []

    return apilist

def getApiFromtestCase(queryset):
    apilist = []
    try:
        body = eval(queryset.body)
        for test in body['tests']:
            apilist.append(test['id'])
    except Exception as err:
        return []

    return apilist

class SuiteFormat(object):

    def __init__(self,body,level="testsuite",optType='add'):
        self.__level = level
        self.__optType = optType
        if(level == "testsuite"):
            self.__initapi__(body)

    def __initapi__(self,body):
        self.tests = []
        for each in body:
            tmp = {}
            tmp['id'] = each['id']
            tmp['api'] = each['name']
            if(self.__optType == "update"):
                tmp['srcindex'] = each.get('srcindex', 0)
                if(each.get('flag','') == 'add'):
                    tmp['flag'] = each.get('flag','')
            self.tests.append(tmp)

'''之前设计了一个类SuiteFormat，这个类设计失败了，在逐渐完善的过程中，发现一开始设计的结构不满足使用要求，所以新创建了一个类，以前的suiteformat，要逐渐迁移到这个新的类上'''
class SuiteBodyFormat(object):
    def __init__(self,body,level="testsuite"):
        self.srcbody = eval(body)
        self.level = level
        self.testStructure = {
            'name': '',
            'id': '',
            'request': {
                'method': '',
                'url': '',
                'headers': {},
                'data': '',
                'json': {},
                'params': {},
                'files': '',
                'validate': [],
                'variables': [],
                'extract': [],
                'setup_hooks': [],
                'teardown_hooks':[]
            },
            'srcAPI':{}
        }

        self.body = {
            'name': '',
            'tests': []
        }

    @staticmethod
    def __get_type(content):
        """
        返回data_type 默认string
        """
        var_type = {
            "str": 1,
            "int": 2,
            "float": 3,
            "bool": 4,
            "list": 5,
            "dict": 6,
        }

        key = str(type(content).__name__)

        if key in ["list", "dict"]:
            content = json.dumps(content)
        else:
            content = str(content)
        return var_type[key], content

    def parseSingleApi(self,index):
        srcindex = 0
        for each in self.srcbody['tests']:
            srcindex += 1
            if(index == srcindex):
                self.singleAPI = copy.deepcopy(self.testStructure)
                self.singleAPI['name'] = each.get('api','')
                self.singleAPI['id'] = each.get('id', '')
                self.singleAPI['request']['method'] = each.get('method', '')
                self.singleAPI['request']['url'] = each.get('url', '')
                self.singleAPI['request']['headers'] = each.get('headers', {})
                self.singleAPI['request']['data'] = each.get('data', '')
                self.singleAPI['request']['json'] = each.get('json', {})
                self.singleAPI['request']['params'] = each.get('params', {})
                self.singleAPI['request']['files'] = each.get('files', '')
                self.singleAPI['request']['validate'] = each.get('validate', [])
                self.singleAPI['request']['variables'] = each.get('variables', [])
                self.singleAPI['request']['extract'] = each.get('extract', [])
                self.singleAPI['request']['hooks'] = each.get('hooks',[])
            else:
                continue

    def setSrcApi(self,apiBody):
        self.singleSrcAPI = {}
        for each in ['method','url']:
            self.singleSrcAPI[each] = apiBody['request'].get(each,'')

        for each in ['headers','json','param','data']:
            self.singleSrcAPI[each] = apiBody['request'].get(each,{})

        for each in ['validate','extract','variables','setup_hooks','teardown_hooks']:
            self.singleSrcAPI[each] = apiBody.get('validate',[])

    def parse_http(self):
        self.parse_http_src()
        self.parse_http_new()

    def parse_http_new(self):
        tmp = []
        if self.singleAPI['request'].get('headers'):
            for key, value in self.singleAPI['request'].pop('headers').items():
                tmp.append({
                    "key": key,
                    "value": value,
                })
            self.singleAPI['request']['headers'] = tmp

    def parse_http_src(self):
        """
        标准前端脚本格式
        """
        #  初始化test结构

        self.srcAPI = {
            'headers':[],
            'params':[],
            'data':[],
            'json':'',
            'extract':[],
            'validate':[],
            'variables': [],
            'setup_hooks': [],
            'teardown_hooks': [],
        }
        if self.singleSrcAPI.get('headers'):
            for key, value in self.singleSrcAPI.pop('headers').items():
                self.srcAPI['headers'].append({
                    "key": key,
                    "value": value,
                })

        if self.singleSrcAPI.get('data'):
            for key, value in self.singleSrcAPI.pop('data').items():
                obj = self.__get_type(value)
                self.srcAPI['data'].append({
                    'key':key,
                    'value':obj[1],
                    'type':obj[0],
                })

        '''if self.__request.get('files'):
            for key, value in self.__request.pop("files").items():
                size = FileBinary.objects.get(name=value).size
                test['request']['data'].append({
                    "key": key,
                    "value": value,
                    "size": size,
                    "type": 5,
                    "desc": self.__desc["files"][key]
                })'''

        if self.singleSrcAPI.get('params'):
            for key, value in self.singleSrcAPI.pop('params').items():
                self.srcAPI['params'].append({
                    "key": key,
                    "value": value,
                    "type": 1,
                })

        if self.singleSrcAPI.get('json'):
            self.srcAPI["json_data"] = json.dumps(self.singleSrcAPI.pop("json"), indent=4,
                           separators=(',', ': '), ensure_ascii=False)

        if self.singleSrcAPI.get('variables'):
            for content in self.singleSrcAPI['variables']:
                for key, value in content.items():
                    obj = self.__get_type(value)
                    self.srcAPI["variables"].append({
                        "key": key,
                        "value": obj[1],
                        "type": obj[0]
                    })

        if self.singleSrcAPI.get('setup_hooks') or self.singleSrcAPI.get('teardown_hooks'):
            pass

        self.singleAPI['srcAPI'] = self.srcAPI

        '''if len(self.__setup_hooks) > len(self.__teardown_hooks):
                for index in range(0, len(self.__setup_hooks)):
                    teardown = ""
                    if index < len(self.__teardown_hooks):
                        teardown = self.__teardown_hooks[index]
                    test["hooks"].append({
                        "setup": self.__setup_hooks[index],
                        "teardown": teardown
                    })
            else:
                for index in range(0, len(self.__teardown_hooks)):
                    setup = ""
                    if index < len(self.__setup_hooks):
                        setup = self.__setup_hooks[index]
                    test["hooks"].append({
                        "setup": setup,
                        "teardown": self.__teardown_hooks[index]
                    })

        self.testcase = test'''


class TestSuiteFormat(object):

    def __init__(self,body,level="testsuite"):
        self.__level = level
        self.__singleTestStructure = {
            'name': '',
            'id': '',
            'body': {
                'method': '',
                'url': '',
                'headers': {},
                'data': {},
                'json': '',
                'params': {},
                'validate': [],
                'variables': [],
                'extract': [],
                'setup_hooks': [],
                'teardown_hooks': []
            },
            'srcAPI': {
                'method': '',
                'url': '',
                'headers':{},
                'params':{},
                'data':{},
                'json':'',
                'extract':[],
                'validate':[],
                'variables': [],
                'setup_hooks': [],
                'teardown_hooks': []
            }
        }

        self.body = {
            'name': '',
            'tests': []
        }

        self.__srcbody = eval(body)
        self.init_APIList()


    def init_APIList(self):
        self.body['name'] = self.__srcbody.get('name','')
        self.body['tests'] = copy.deepcopy(self.__srcbody.get('tests', []))
        srcindex = 0
        for each in self.body['tests']:
            srcindex += 1
            each['srcindex'] = srcindex


    def init_singleAPIBody(self,apiBody):
        #初始化api定义数据
        self.singleAPIBody = copy.deepcopy(self.__singleTestStructure)

        self.singleAPIBody['srcAPI']['name'] = apiBody.get('name', '')

        for each in ['method', 'url','json']:
            self.singleAPIBody['srcAPI'][each] = apiBody['request'].get(each, '')

        for each in ['headers', 'param', 'data']:
            self.singleAPIBody['srcAPI'][each]  = apiBody['request'].get(each, {})

        for each in ['validate', 'extract', 'variables', 'setup_hooks', 'teardown_hooks']:
            self.singleAPIBody['srcAPI'][each] = apiBody.get(each, [])

        #初始化重定义数据
        self.singleAPIBody['name'] = self.__specIndexAPI.get('api', '')
        self.singleAPIBody['id'] = self.__specIndexAPI.get('id', '')
        self.singleAPIBody['srcindex'] = self.__specIndexAPI.get('srcindex')
        self.singleAPIBody['body']['headers'] = self.__specIndexAPI.get('headers', {})
        self.singleAPIBody['body']['data'] = self.__specIndexAPI.get('data', {})
        self.singleAPIBody['body']['json'] = self.__specIndexAPI.get('json', '')
        self.singleAPIBody['body']['params'] = self.__specIndexAPI.get('params', {})
        self.singleAPIBody['body']['validate'] = self.__specIndexAPI.get('validate', [])
        self.singleAPIBody['body']['variables'] = self.__specIndexAPI.get('variables', [])
        self.singleAPIBody['body']['extract'] = self.__specIndexAPI.get('extract', [])
        self.singleAPIBody['body']['setup_hooks'] = self.__specIndexAPI.get('setup_hooks', [])
        self.singleAPIBody['body']['teardown_hooks'] = self.__specIndexAPI.get('teardown_hooks', [])

    def getAPIId(self,index):
        for each in self.body['tests']:
            if(index == each['srcindex']):
                self.__specIndexAPI = each
                self.specAPIid = each['id']
            else:
                continue

    @staticmethod
    def __get_type(content):
        """
        返回data_type 默认string
        """
        var_type = {
            "str": 1,
            "int": 2,
            "float": 3,
            "bool": 4,
            "list": 5,
            "dict": 6,
        }

        key = str(type(content).__name__)

        if key in ["list", "dict"]:
            content = json.dumps(content)
        else:
            content = str(content)
        return var_type[key], content

    #将headers params data等转换成列表，方便前台进行展示
    def parse_http(self):
        suiteStep = {
            'header': [],
            'request':{
                'data': [],
                'params': [],
                'json_data': '',
            },
            'variables': [],
            'hooks': [],
            'validate': [],
            'extract': [],
        }
        apiStep = {
            'header': [],
            'request': {
                'data': [],
                'params': [],
                'json_data': '',
            },
            'variables': [],
            'hooks': [],
            'validate': [],
            'extract': [],
        }
        self.testcase = {
            'suiteStep':suiteStep,
            'apiStep':apiStep
        }
        self.testcase['name'] = self.singleAPIBody['srcAPI']['name']
        self.testcase['method'] = self.singleAPIBody['srcAPI']['method']
        self.testcase['url'] = self.singleAPIBody['srcAPI']['url']
        self.testcase['srcindex'] = self.singleAPIBody['srcindex']

        if self.singleAPIBody['srcAPI'].get('headers'):
            for key, value in self.singleAPIBody['srcAPI'].pop('headers').items():
                apiStep['header'].append({
                    "key": key,
                    "value": value,
                })

        if self.singleAPIBody['body'].get('headers'):
            for key, value in self.singleAPIBody['body'].pop('headers').items():
                suiteStep['header'].append({
                    "key": key,
                    "value": value,
                })

        if self.singleAPIBody['srcAPI'].get('data'):
            for key, value in self.singleAPIBody['srcAPI'].pop('data').items():
                obj = self.__get_type(value)
                apiStep['request']['data'].append({
                    "key": key,
                    "value": obj[1],
                    "type": obj[0],
                })

        if self.singleAPIBody['body'].get('data'):
            for key, value in self.singleAPIBody['body'].pop('data').items():
                obj = self.__get_type(value)
                suiteStep['request']['data'].append({
                    "key": key,
                    "value": obj[1],
                    "type": obj[0],
                })

        if self.singleAPIBody['srcAPI'].get('params'):
            for key, value in self.singleAPIBody['srcAPI'].pop('params').items():
                apiStep['request']['params'].append({
                    "key": key,
                    "value": value,
                    "type": 1,
                })

        if self.singleAPIBody['body'].get('params'):
            for key, value in self.singleAPIBody['body'].pop('params').items():
                suiteStep['request']['params'].append({
                    "key": key,
                    "value": value,
                    "type": 1,
                })

        if self.singleAPIBody['srcAPI'].get('json'):
            apiStep['request']["json_data"] = \
                json.dumps(self.singleAPIBody['srcAPI'].pop("json"), indent=4,
                           separators=(',', ': '), ensure_ascii=False)

        if self.singleAPIBody['body'].get('json'):
            suiteStep['request']["json_data"] = \
                json.dumps(self.singleAPIBody['body'].pop("json"), indent=4,
                           separators=(',', ': '), ensure_ascii=False)

        if self.singleAPIBody['srcAPI'].get('variables'):
            for content in self.singleAPIBody['srcAPI']['variables']:
                for key, value in content.items():
                    obj = self.__get_type(value)
                    apiStep["variables"].append({
                        "key": key,
                        "value": obj[1],
                        "type": obj[0]
                    })

        if self.singleAPIBody['body'].get('variables'):
            for content in self.singleAPIBody['body']['variables']:
                for key, value in content.items():
                    obj = self.__get_type(value)
                    suiteStep["variables"].append({
                        "key": key,
                        "value": obj[1],
                        "type": obj[0]
                    })

        if self.singleAPIBody['srcAPI'].get('setup_hooks') or self.singleAPIBody['srcAPI'].get('teardown_hooks'):
            pass

        if self.singleAPIBody['body'].get('setup_hooks') or self.singleAPIBody['body'].get('teardown_hooks'):
            pass

        if self.singleAPIBody['srcAPI'].get('extract'):
            for content in self.singleAPIBody['srcAPI']['extract']:
                for key, value in content.items():
                    apiStep["extract"].append({
                        "key": key,
                        "value": value,
                    })

        if self.singleAPIBody['body'].get('extract'):
            for content in self.singleAPIBody['body']['extract']:
                for key, value in content.items():
                    suiteStep["extract"].append({
                        "key": key,
                        "value": value,
                    })

        if self.singleAPIBody['srcAPI'].get('validate'):
            for content in self.singleAPIBody['srcAPI'].get('validate'):
                for key, value in content.items():
                    obj = self.__get_type(value[1])
                    apiStep["validate"].append({
                        "expect": obj[1],
                        "actual": value[0],
                        "comparator": key,
                        "type": obj[0]
                    })

        if self.singleAPIBody['body'].get('validate'):
            for content in self.singleAPIBody['body'].get('validate'):
                for key, value in content.items():
                    obj = self.__get_type(value[1])
                    suiteStep["validate"].append({
                        "expect": obj[1],
                        "actual": value[0],
                        "comparator": key,
                        "type": obj[0]
                    })

    def updateStep(self,SuiteStepBody):
        for each in self.body.get('tests',[]):
            if(each['srcindex'] == SuiteStepBody['srcindex']):
                each['headers'] = SuiteStepBody['header'].get('header',{})
                each['extract'] = SuiteStepBody['extract'].get('extract',{})
                each['validate'] = SuiteStepBody['validate'].get('validate',{})
                each['variables'] = SuiteStepBody['variables'].get('variables',{})
                break
            else:
                continue

        for each in self.body.get('tests',[]):
            del each['srcindex']

class testCaseFormat(object):

    def __init__(self,**kwargs):
        self.__project = kwargs.get('project','')
        self.__relation = kwargs.get('relation','')
        self.__optType = kwargs.get('optType','')
        if(self.__optType == "add" or self.__optType == "update"):
            self.__name = kwargs['name']


    def addTestCase(self,testBody):
        self.tests = []
        for each in testBody:
            tmp = {}
            tmp['id'] = each['id']
            tmp['api'] = each['name']
            self.tests.append(tmp)


    def getList(self,queryset):
        returnvalue = {
            'id': '',
            'name': '',
            'maxindex': 0,
            'tests': [],
            'empty': True,
        }
        returnvalue['empty'] = False
        returnvalue['id'] = queryset.id
        returnvalue['name'] = queryset.name

        containedApi = getApiFromtestCase(queryset)
        index = 0 #index是从1开始计算的，第一个案例的顺序值是1，第二个是2
        for each in containedApi:
            try:
                apiQueryset = models.API.objects.get(project=self.__project,id=each)
            except:
                continue
            index = index + 1
            returnvalue['tests'].append(
                {
                    'index':index,
                    'srcindex': index,
                    'id':apiQueryset.id,
                    'method':apiQueryset.method,
                    'name':apiQueryset.name,
                    'url':apiQueryset.url,
                    'flag':'' #接口返回的所有flag都是空的，前台如果进行加减操作，会对flag字段进行操作，置为add或者reduce
                })
        returnvalue['maxindex'] = index
        self.allStep =  returnvalue

    def updateList(self,srcBody,newBody):
        self.srcBody = eval(srcBody.body)
        self.srcTest = copy.deepcopy(self.srcBody['tests'])
        for index,each in enumerate(self.srcTest):
            each['srcindex'] = index + 1

        tmpTests = []
        for each in newBody:
            tmp = {}
            tmp['id'] = each['id']
            tmp['api'] = each['name']
            tmp['srcindex'] = each.get('srcindex', 0)
            if (each.get('flag', '') == 'add'):
                tmp['flag'] = each.get('flag', '')
            tmpTests.append(tmp)

        tmpNewBody = []
        for each_new in tmpTests:
            if (each_new.get('flag', '') == 'add'):
                del each_new['srcindex']
                if each_new.get('flag'):
                    del each_new['flag']
                tmpNewBody.append(each_new)
                continue
            for each_src in self.srcTest:
                if (each_src.get('srcindex', -1) == each_new.get('srcindex', -2) and each_new['srcindex'] != 0):
                    del each_src['srcindex']
                    if each_new.get('flag'):
                        del each_new['flag']
                    tmpNewBody.append(each_src)
                    break

        tmp_body = {
            'name': self.srcBody['name'],
            'def': self.srcBody['name'],
            'tests': tmpNewBody
        }
        self.newbody = json.dumps(tmp_body)


    def getSingleStep(self, index):
        for each in self.allStep['tests']:
            if (index == each['srcindex']):
                self.__specIndexAPI = each
                self.specAPIid = each['id']
            else:
                continue

        apiQueryset = models.API.objects.get(project=self.__project, id=self.specAPIid)
        apiBody = eval(apiQueryset.body)
        self.singleAPIBody = {
            'name': '',
            'id': '',
            'body': {
                'method': '',
                'url': '',
                'headers': {},
                'data': {},
                'json': '',
                'params': {},
                'validate': [],
                'variables': [],
                'extract': [],
                'setup_hooks': [],
                'teardown_hooks': []
            },
            'srcAPI': {
                'method': '',
                'url': '',
                'headers': {},
                'params': {},
                'data': {},
                'json': '',
                'extract': [],
                'validate': [],
                'variables': [],
                'setup_hooks': [],
                'teardown_hooks': []
            }
        }

        self.singleAPIBody['srcAPI']['name'] = apiBody.get('name', '')

        for each in ['method', 'url', 'json']:
            self.singleAPIBody['srcAPI'][each] = apiBody['request'].get(each, '')

        for each in ['headers', 'param', 'data']:
            self.singleAPIBody['srcAPI'][each] = apiBody['request'].get(each, {})

        for each in ['validate', 'extract', 'variables', 'setup_hooks', 'teardown_hooks']:
            self.singleAPIBody['srcAPI'][each] = apiBody.get(each, [])

        # 初始化重定义数据
        self.singleAPIBody['name'] = self.__specIndexAPI.get('api', '')
        self.singleAPIBody['id'] = self.__specIndexAPI.get('id', '')
        self.singleAPIBody['srcindex'] = self.__specIndexAPI.get('srcindex')
        self.singleAPIBody['body']['headers'] = self.__specIndexAPI.get('headers', {})
        self.singleAPIBody['body']['data'] = self.__specIndexAPI.get('data', {})
        self.singleAPIBody['body']['json'] = self.__specIndexAPI.get('json', '')
        self.singleAPIBody['body']['params'] = self.__specIndexAPI.get('params', {})
        self.singleAPIBody['body']['validate'] = self.__specIndexAPI.get('validate', [])
        self.singleAPIBody['body']['variables'] = self.__specIndexAPI.get('variables', [])
        self.singleAPIBody['body']['extract'] = self.__specIndexAPI.get('extract', [])
        self.singleAPIBody['body']['setup_hooks'] = self.__specIndexAPI.get('setup_hooks', [])
        self.singleAPIBody['body']['teardown_hooks'] = self.__specIndexAPI.get('teardown_hooks', [])


    def parse_http(self):
        suiteStep = {
            'header': [],
            'request': {
                'data': [],
                'params': [],
                'json_data': '',
            },
            'variables': [],
            'hooks': [],
            'validate': [],
            'extract': [],
        }
        apiStep = {
            'header': [],
            'request': {
                'data': [],
                'params': [],
                'json_data': '',
            },
            'variables': [],
            'hooks': [],
            'validate': [],
            'extract': [],
        }
        self.testcase = {
            'suiteStep': suiteStep,
            'apiStep': apiStep
        }
        self.testcase['name'] = self.singleAPIBody['srcAPI']['name']
        self.testcase['method'] = self.singleAPIBody['srcAPI']['method']
        self.testcase['url'] = self.singleAPIBody['srcAPI']['url']
        self.testcase['srcindex'] = self.singleAPIBody['srcindex']

        if self.singleAPIBody['srcAPI'].get('headers'):
            for key, value in self.singleAPIBody['srcAPI'].pop('headers').items():
                apiStep['header'].append({
                    "key": key,
                    "value": value,
                })

        if self.singleAPIBody['body'].get('headers'):
            for key, value in self.singleAPIBody['body'].pop('headers').items():
                suiteStep['header'].append({
                    "key": key,
                    "value": value,
                })

        if self.singleAPIBody['srcAPI'].get('data'):
            for key, value in self.singleAPIBody['srcAPI'].pop('data').items():
                obj = self.__get_type(value)
                apiStep['request']['data'].append({
                    "key": key,
                    "value": obj[1],
                    "type": obj[0],
                })

        if self.singleAPIBody['body'].get('data'):
            for key, value in self.singleAPIBody['body'].pop('data').items():
                obj = self.__get_type(value)
                suiteStep['request']['data'].append({
                    "key": key,
                    "value": obj[1],
                    "type": obj[0],
                })

        if self.singleAPIBody['srcAPI'].get('params'):
            for key, value in self.singleAPIBody['srcAPI'].pop('params').items():
                apiStep['request']['params'].append({
                    "key": key,
                    "value": value,
                    "type": 1,
                })

        if self.singleAPIBody['body'].get('params'):
            for key, value in self.singleAPIBody['body'].pop('params').items():
                suiteStep['request']['params'].append({
                    "key": key,
                    "value": value,
                    "type": 1,
                })

        if self.singleAPIBody['srcAPI'].get('json'):
            apiStep['request']["json_data"] = \
                json.dumps(self.singleAPIBody['srcAPI'].pop("json"), indent=4,
                           separators=(',', ': '), ensure_ascii=False)

        if self.singleAPIBody['body'].get('json'):
            suiteStep['request']["json_data"] = \
                json.dumps(self.singleAPIBody['body'].pop("json"), indent=4,
                           separators=(',', ': '), ensure_ascii=False)

        if self.singleAPIBody['srcAPI'].get('variables'):
            for content in self.singleAPIBody['srcAPI']['variables']:
                for key, value in content.items():
                    obj = self.__get_type(value)
                    apiStep["variables"].append({
                        "key": key,
                        "value": obj[1],
                        "type": obj[0]
                    })

        if self.singleAPIBody['body'].get('variables'):
            for content in self.singleAPIBody['body']['variables']:
                for key, value in content.items():
                    obj = self.__get_type(value)
                    suiteStep["variables"].append({
                        "key": key,
                        "value": obj[1],
                        "type": obj[0]
                    })

        if self.singleAPIBody['srcAPI'].get('setup_hooks') or self.singleAPIBody['srcAPI'].get('teardown_hooks'):
            pass

        if self.singleAPIBody['body'].get('setup_hooks') or self.singleAPIBody['body'].get('teardown_hooks'):
            pass

        if self.singleAPIBody['srcAPI'].get('extract'):
            for content in self.singleAPIBody['srcAPI']['extract']:
                for key, value in content.items():
                    apiStep["extract"].append({
                        "key": key,
                        "value": value,
                    })

        if self.singleAPIBody['body'].get('extract'):
            for content in self.singleAPIBody['body']['extract']:
                for key, value in content.items():
                    suiteStep["extract"].append({
                        "key": key,
                        "value": value,
                    })

        if self.singleAPIBody['srcAPI'].get('validate'):
            for content in self.singleAPIBody['srcAPI'].get('validate'):
                for key, value in content.items():
                    obj = self.__get_type(value[1])
                    apiStep["validate"].append({
                        "expect": obj[1],
                        "actual": value[0],
                        "comparator": key,
                        "type": obj[0]
                    })

        if self.singleAPIBody['body'].get('validate'):
            for content in self.singleAPIBody['body'].get('validate'):
                for key, value in content.items():
                    obj = self.__get_type(value[1])
                    suiteStep["validate"].append({
                        "expect": obj[1],
                        "actual": value[0],
                        "comparator": key,
                        "type": obj[0]
                    })
    @staticmethod
    def __get_type(content):
        """
        返回data_type 默认string
        """
        var_type = {
            "str": 1,
            "int": 2,
            "float": 3,
            "bool": 4,
            "list": 5,
            "dict": 6,
        }

        key = str(type(content).__name__)

        if key in ["list", "dict"]:
            content = json.dumps(content)
        else:
            content = str(content)
        return var_type[key], content

    def updateStep(self,newTestCaseBody):
        for each in self.allStep.get('tests',[]):
            if(each['srcindex'] == newTestCaseBody['srcindex']):
                each['headers'] = newTestCaseBody['header'].get('header',{})
                each['extract'] = newTestCaseBody['extract'].get('extract',{})
                each['validate'] = newTestCaseBody['validate'].get('validate',{})
                each['variables'] = newTestCaseBody['variables'].get('variables',{})
                break
            else:
                continue

        for each in self.body.get('tests',[]):
            del each['srcindex']
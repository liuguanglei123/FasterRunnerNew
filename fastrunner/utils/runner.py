#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
from django.core.exceptions import ObjectDoesNotExist
from fastrunner.utils.loader import parse_summary
import traceback
from fastrunner.utils.loader import save_summary
EXEC = sys.executable

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

class RunTestSuite(object):

    def __init__(self,*args,**kwargs):
        try:
            self.suiteQuerySet = models.TestSuite.objects.filter(project=kwargs['project'], relation__in=kwargs['relation'])
        except ObjectDoesNotExist:
            self.msg = 'ObjectDoesNotExist'

        self.__project = kwargs['project']
        self.__relation = kwargs['relation']
        self.__projectPath = kwargs['projectPath']
        self.__getAPIList__()
        self.__getAllAPIBody__()

    def __getAPIList__(self):
        self.APIList = []
        self.tests = []
        for each in self.suiteQuerySet:
            for eachTest in eval(each.body)['tests']:
                self.tests.append(eachTest)
        for each in self.tests:
            self.APIList.append(each['id'])

    def __getAllAPIBody__(self):
        self.allAPIBody = []
        for each in self.APIList:
            try:
                apiQueryset = models.API.objects.get(project=self.__project,id=each)
            except:
                continue

            self.allAPIBody.append(eval(apiQueryset.body))

    def serializeAPI(self):
        self.apiPath = os.path.join(self.__projectPath,'api')
        for each in self.allAPIBody:
            singleAPI = {
                'name':each.get('name',''),
                'variables':self.convertListToDict(each.get('variables',[]),'variables'),
                'request':{
                    'url':each.get('request',{}).get('url',''),
                    'method':each.get('request',{}).get('method',''),
                    'headers':each.get('request',{}).get('headers',''),
                    'params':each.get('request',{}).get('params',''),
                    'data':each.get('request',{}).get('data',''),
                    'json':each.get('request',{}).get('json','')
                },
                'extract':each.get('extract',[]),
                'validate':each.get('validate',[])
            }

            if(os.path.exists(os.path.join(self.apiPath, each.get('name')+'.yml'))):
                continue
            file = codecs.open(os.path.join(self.apiPath, each.get('name')+'.yml'),'a+','utf-8')

            file.write(yaml.dump(singleAPI,default_flow_style=False))
            file.flush()


    def convertListToDict(self,dictInList,type):
        if(type == 'variables'):
            if(len(dictInList) == 0):
                return ''
            tmp = {}
            for each in dictInList:
                for key,value in each.items():
                    tmp[key] = value
            return tmp

    def convertListToList(self,dict,type):
        if(type == 'extract'):
            if(len(dict) == 0):
                return ''
            tmp = []
            for each in dict:
                for key,value in each.items():
                    tmp.append( { key:value } )
            return tmp

    def serializeSingleStep(self,index):
        for suite in self.suiteQuerySet:
            self.allSuiteStep = []
            testStepstructure = {
                'test': {
                    'name': '',
                    'api': '',
                    'variables': '',
                    'validate': '',
                    'extract': ''
                }
            }
            self.SuiteBody = []
            self.suitePath = os.path.join(self.__projectPath, 'testcases')
            srcindex = 1
            for each in eval(suite.body)['tests']:
                if(index != srcindex):
                    srcindex = srcindex + 1
                    continue
                tmp = copy.deepcopy(testStepstructure)

                try:
                    self.singleAPIQuerySet = models.API.objects.get(id=each['id'])
                except ObjectDoesNotExist:
                    self.msg = 'ObjectDoesNotExist'

                tmp['test']['name'] = each['api']
                tmp['test']['api'] = 'api/' + self.singleAPIQuerySet.name + '.yml'
                tmp['test']['validate'] = each.get('validate', [])

                tmp['test']['variables'] = '' if len(each.get('variables', [])) == 0 else self.convertListToDict(
                    each.get('variables', []), 'variables')
                tmp['test']['extract'] = each.get('extract', [])

                if (len(tmp['test']['validate']) == 0):
                    del tmp['test']['validate']
                if (len(tmp['test']['variables']) == 0):
                    del tmp['test']['variables']
                if (len(tmp['test']['extract']) == 0):
                    del tmp['test']['extract']

                self.SuiteBody.append(copy.deepcopy(tmp))
                break
            if (os.path.exists(os.path.join(self.suitePath, suite.name + '.yml'))):
                return

            file = codecs.open(os.path.join(self.suitePath, suite.name + '.yml'), 'a+', 'utf-8')
            file.write(yaml.dump(self.SuiteBody, default_flow_style=False))
            file.flush()

    def serializeTestSuite(self):
        for eachSuite in self.suiteQuerySet:
            self.allSuiteStep = []
            testStepstructure = {
                'test': {
                    'name': '',
                    'api': '',
                    'variables': '',
                    'validate': '',
                    'extract': ''
                }
            }
            self.SuiteBody = []
            self.suitePath = os.path.join(self.__projectPath, 'testcases')
            for each in eval(eachSuite.body)['tests']:
                tmp = copy.deepcopy(testStepstructure)

                try:
                    self.singleAPIQuerySet = models.API.objects.get(id=each['id'])
                except ObjectDoesNotExist:
                    self.msg = 'ObjectDoesNotExist'

                tmp['test']['name'] = each['api']
                tmp['test']['api'] = 'api/' + self.singleAPIQuerySet.name + '.yml'
                tmp['test']['validate'] = each.get('validate',[])

                tmp['test']['variables'] = '' if len(each.get('variables',[]))==0 else self.convertListToDict(each.get('variables',[]),'variables')
                tmp['test']['extract'] = each.get('extract',[])

                if (len(tmp['test']['validate']) == 0):
                    del tmp['test']['validate']
                if (len(tmp['test']['variables']) == 0):
                    del tmp['test']['variables']
                if (len(tmp['test']['extract']) == 0):
                    del tmp['test']['extract']


                self.SuiteBody.append(copy.deepcopy(tmp))
            if(os.path.exists(os.path.join(self.suitePath,eachSuite.name + '.yml'))):
                return

            file = codecs.open(os.path.join(self.suitePath, eachSuite.name + '.yml'),'a+','utf-8')
            file.write(yaml.dump(self.SuiteBody, default_flow_style=False))
            file.flush()


    def runTestSuite(self):
        runner = HttpRunner(failfast=False)
        runner.run(self.suitePath,mapping=self.__mapping)
        self.summary = parse_summary(runner.summary)

    def runBackTestSuite(self, name):
        runner = HttpRunner(failfast=False)
        runner.run(self.suitePath, mapping=self.__mapping)
        save_summary(name, runner.summary, self.__project)

    def serializeDebugtalk(self):
        try:
            queryset = models.Debugtalk.objects.get(project__id=self.__project)
        except ObjectDoesNotExist:
            return

        self.debugtalk = queryset.code

        file = codecs.open(os.path.join(self.__projectPath, 'debugtalk.py'), 'a+','utf-8')
        file.write(self.debugtalk)
        file.flush()

    def generateMapping(self):
        try:
            queryset = models.Variables.objects.filter(project_id=self.__project)
        except ObjectDoesNotExist:
            self.__mapping=None
            return

        self.__mapping = {}
        for each in queryset:
            self.__mapping[each.key] = each.value


class RunAPI(object):

    def __init__(self,*args,**kwargs):
        self.__APIList = []
        self.__projectPath = kwargs['projectPath']

        if(kwargs['type'] == 'singleAPI'):
            try:
                api = models.API.objects.get(id=kwargs['id'],isdeleted=0)
            except ObjectDoesNotExist:
                self.msg = 'ObjectDoesNotExist'

            self.__APIList.append([api.name,eval(api.body)])
            self.__project = api.project_id
        elif(kwargs['type'] == 'APITree'):
            relationList = kwargs['relation']
            self.__project = kwargs['project']
            try:
                APIList = models.API.objects.filter(relation__in=relationList,project=self.__project,isdeleted=0)
            except ObjectDoesNotExist:
                self.msg = 'ObjectDoesNotExist'
            for each in APIList:
                self.__APIList.append([each.name,eval(each.body)])
        elif(kwargs['type'] == 'debugAPI'):
            self.__project = kwargs['project']
            self.__APIList.append([kwargs['name'],kwargs['APIBody']])


    def serializeAPI(self):
        if(len(self.__APIList) == 0):
            return

        self.apiPath = os.path.join(self.__projectPath,'api')
        for each in self.__APIList:
            file = codecs.open(os.path.join(self.apiPath,each[0]+'.yml'),'a+','utf-8')
            file.write(yaml.dump(each[1],default_flow_style=False))
            file.flush()
            file.close()

    def serializeDebugtalk(self):
        try:
            queryset = models.Debugtalk.objects.get(project__id=self.__project)
        except ObjectDoesNotExist:
            return

        self.debugtalk = queryset.code

        file = codecs.open(os.path.join(self.__projectPath, 'debugtalk.py'), 'a+','utf-8')
        file.write(self.debugtalk)
        file.flush()

    def generateMapping(self):
        try:
            queryset = models.Variables.objects.filter(project_id=self.__project)
        except ObjectDoesNotExist:
            self.__mapping=None
            return

        self.__mapping = {}
        for each in queryset:
            self.__mapping[each.key] = each.value

    def runAPI(self):
        runner = HttpRunner(failfast=False)
        runner.run(self.apiPath,mapping=self.__mapping)
        self.summary = parse_summary(runner.summary)

    def runBackAPI(self, name):
        runner = HttpRunner(failfast=False)
        runner.run(self.apiPath, mapping=self.__mapping)
        save_summary(name, runner.summary, self.__project)


class RunTestCase(object):

    def __init__(self,*args,**kwargs):
        try:
            self.caseQuerySet = models.TestCase.objects.filter(project=kwargs['project'], relation__in=kwargs['relation'])
        except ObjectDoesNotExist:
            self.msg = 'ObjectDoesNotExist'

        self.__project = kwargs['project']
        self.__relation = kwargs['relation']
        self.__projectPath = kwargs['projectPath']
        self.__getAPIList__()
        self.__getAllAPIBody__()

    def __getAPIList__(self):
        self.APIList = []
        self.tests = []
        for each in self.caseQuerySet:
            for eachTest in eval(each.body)['tests']:
                self.tests.append(eachTest)
        for each in self.tests:
            self.APIList.append(each['id'])

    def __getAllAPIBody__(self):
        self.allAPIBody = []
        for each in self.APIList:
            try:
                apiQueryset = models.API.objects.get(project=self.__project,id=each)
            except:
                continue

            self.allAPIBody.append(eval(apiQueryset.body))

    def serializeAPI(self):
        self.apiPath = os.path.join(self.__projectPath,'api')
        for each in self.allAPIBody:
            singleAPI = {
                'name':each.get('name',''),
                'variables':self.convertListToDict(each.get('variables',[]),'variables'),
                'request':{
                    'url':each.get('request',{}).get('url',''),
                    'method':each.get('request',{}).get('method',''),
                    'headers':each.get('request',{}).get('headers',''),
                    'params':each.get('request',{}).get('params',''),
                    'data':each.get('request',{}).get('data',''),
                    'json':each.get('request',{}).get('json','')
                },
                'extract':each.get('extract',[]),
                'validate':each.get('validate',[])
            }

            if(os.path.exists(os.path.join(self.apiPath, each.get('name')+'.yml'))):
                continue
            file = codecs.open(os.path.join(self.apiPath, each.get('name')+'.yml'),'a+','utf-8')

            file.write(yaml.dump(singleAPI,default_flow_style=False))
            file.flush()


    def convertListToDict(self,dictInList,type):
        if(type == 'variables'):
            if(len(dictInList) == 0):
                return ''
            tmp = {}
            for each in dictInList:
                for key,value in each.items():
                    tmp[key] = value
            return tmp

    def convertListToList(self,dict,type):
        if(type == 'extract'):
            if(len(dict) == 0):
                return ''
            tmp = []
            for each in dict:
                for key,value in each.items():
                    tmp.append( { key:value } )
            return tmp

    def serializeTestCase(self):
        for eachCase in self.caseQuerySet:
            self.allCaseStep = []
            testStepstructure = {
                'test': {
                    'name': '',
                    'api': '',
                    'variables': '',
                    'validate': '',
                    'extract': ''
                }
            }
            self.CaseBody = []
            self.casePath = os.path.join(self.__projectPath, 'testcases')
            for each in eval(eachCase.body)['tests']:
                tmp = copy.deepcopy(testStepstructure)

                try:
                    self.singleAPIQuerySet = models.API.objects.get(id=each['id'])
                except ObjectDoesNotExist:
                    self.msg = 'ObjectDoesNotExist'

                tmp['test']['name'] = each['api']
                tmp['test']['api'] = 'api/' + self.singleAPIQuerySet.name + '.yml'
                tmp['test']['validate'] = each.get('validate', [])

                tmp['test']['variables'] = '' if len(each.get('variables', [])) == 0 else self.convertListToDict(
                    each.get('variables', []), 'variables')
                tmp['test']['extract'] = each.get('extract', [])

                if (len(tmp['test']['validate']) == 0):
                    del tmp['test']['validate']
                if (len(tmp['test']['variables']) == 0):
                    del tmp['test']['variables']
                if (len(tmp['test']['extract']) == 0):
                    del tmp['test']['extract']

                self.CaseBody.append(copy.deepcopy(tmp))
            if (os.path.exists(os.path.join(self.casePath, eachCase.name + '.yml'))):
                return

            file = codecs.open(os.path.join(self.casePath, eachCase.name + '.yml'), 'a+', 'utf-8')
            file.write(yaml.dump(self.CaseBody, default_flow_style=False))
            file.flush()


    def runTestCase(self):
        runner = HttpRunner(failfast=False)
        runner.run(self.casePath,mapping=self.__mapping)
        self.summary = parse_summary(runner.summary)

    def runBackTestCase(self,name):
        runner = HttpRunner(failfast=False)
        runner.run(self.casePath, mapping=self.__mapping)
        save_summary(name, runner.summary, self.__project)
        '''self.summary = parse_summary(runner.summary)
        summary = debug_api(api, project, save=False, config=config)
        save_summary(name, summary, project)'''

    def serializeDebugtalk(self):
        try:
            queryset = models.Debugtalk.objects.get(project__id=self.__project)
        except ObjectDoesNotExist:
            return

        self.debugtalk = queryset.code

        file = codecs.open(os.path.join(self.__projectPath, 'debugtalk.py'), 'a+','utf-8')
        file.write(self.debugtalk)
        file.flush()

    def generateMapping(self):
        try:
            queryset = models.Variables.objects.filter(project_id=self.__project)
        except ObjectDoesNotExist:
            self.__mapping=None
            return

        self.__mapping = {}
        for each in queryset:
            self.__mapping[each.key] = each.value

    def serializeSingleStep(self,index):
        for step in self.caseQuerySet:
            self.allCaseStep = []
            testStepstructure = {
                'test': {
                    'name': '',
                    'api': '',
                    'variables': '',
                    'validate': '',
                    'extract': ''
                }
            }
            self.CaseBody = []
            self.casePath = os.path.join(self.__projectPath, 'testcases')
            srcindex = 1
            for each in eval(step.body)['tests']:
                if(index != srcindex):
                    srcindex = srcindex + 1
                    continue
                tmp = copy.deepcopy(testStepstructure)

                try:
                    self.singleAPIQuerySet = models.API.objects.get(id=each['id'])
                except ObjectDoesNotExist:
                    self.msg = 'ObjectDoesNotExist'

                tmp['test']['name'] = each['api']
                tmp['test']['api'] = 'api/' + self.singleAPIQuerySet.name + '.yml'
                tmp['test']['validate'] = each.get('validate', [])

                tmp['test']['variables'] = '' if len(each.get('variables', [])) == 0 else self.convertListToDict(
                    each.get('variables', []), 'variables')
                tmp['test']['extract'] = each.get('extract', [])

                if (len(tmp['test']['validate']) == 0):
                    del tmp['test']['validate']
                if (len(tmp['test']['variables']) == 0):
                    del tmp['test']['variables']
                if (len(tmp['test']['extract']) == 0):
                    del tmp['test']['extract']

                self.CaseBody.append(copy.deepcopy(tmp))
                break
            if (os.path.exists(os.path.join(self.casePath, step.name + '.yml'))):
                return

            file = codecs.open(os.path.join(self.casePath, step.name + '.yml'), 'a+', 'utf-8')
            file.write(yaml.dump(self.CaseBody, default_flow_style=False))
            file.flush()
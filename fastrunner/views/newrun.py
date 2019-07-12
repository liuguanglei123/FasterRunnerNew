from rest_framework.decorators import api_view
from fastrunner.utils import loader,newloader
from rest_framework.response import Response
from fastrunner.utils.parser import Format
from fastrunner import models
from django.conf import settings
import os,time,sys
from httprunner.utils import create_scaffold
from fastrunner.utils import runner
import traceback
from fastrunner.utils.newrunner import RunSingleApi,RunTree,RunSingleApiInStep,RunSingleApiInCase

"""运行方式
"""
import logging
logger = logging.getLogger('httprunner')


@api_view(['GET'])
def run_api_pk(request, **kwargs):
    """run api by pk
    """
    run_test_path = settings.RUN_TEST_PATH
    timedir = time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())
    projectPath = os.path.join(run_test_path, timedir)
    create_scaffold(projectPath)
    if ('debugtalk' in sys.modules.keys()):
        del sys.modules['debugtalk']

    debugApi = RunSingleApi(projectPath=projectPath, config=request.query_params['config'],
                            apiId=kwargs['pk'], type="singleapi")

    debugApi.serializeTestCase()
    debugApi.serializeTestSuite()
    debugApi.serializeDebugtalk()
    debugApi.generateMapping()
    debugApi.run()

    return Response(debugApi.summary)


@api_view(["POST"])
def run_testsuite(request):
    """debug testsuite
    {
        name: str,
        body: dict
    }
    """
    body = request.data["body"]
    project = request.data["project"]
    name = request.data["name"]

    testcase_list = []
    config = None

    for test in body:
        test = loader.load_test(test, project=project)
        if "base_url" in test["request"].keys():
            config = test
            continue

        testcase_list.append(test)

        summary = loader.debug_api(testcase_list, project, name=name, config=config)

    return Response(summary)


@api_view(["POST"])
def run_test(request):
    """debug single test
    {
        body: dict
    }
    """

    body = request.data["body"]
    summary = loader.debug_api(loader.load_test(body), request.data["project"])
    return Response(summary)


@api_view(["GET"])
def run_testsuite_pk(request, **kwargs):
    """run testsuite by pk
        {
            project: int,
            name: str
        }
    """
    pk = kwargs["pk"]

    test_list = models.CaseStep.objects. \
        filter(case__id=pk).order_by("step").values("body")

    project = request.query_params["project"]
    name = request.query_params["name"]

    testcase_list = []
    config = None

    for content in test_list:
        body = eval(content["body"])

        if "base_url" in body["request"].keys():
            config = eval(models.Config.objects.get(name=body["name"], project__id=project).body)
            continue

        testcase_list.append(body)

    summary = loader.debug_api(testcase_list, project, name=name, config=config)

    return Response(summary)


@api_view(['POST'])
def run_suite_tree(request):
    """run suite by tree
    {
        project: int
        relation: list
        name: str
        async: bool
    }
    """
    # order by id default
    project = request.data['project']
    relation = request.data["relation"]
    back_async = request.data["async"]
    report = request.data["name"]

    config = None
    testcase = []
    for relation_id in relation:
        suite = models.Case.objects.filter(project__id=project,
                                           relation=relation_id).order_by('id').values('id', 'name')

        for content in suite:
            test_list = models.CaseStep.objects. \
                filter(case__id=content["id"]).order_by("step").values("body")
            # [{scripts}, {scripts}]
            testcase_list = []

            for content in test_list:
                body = eval(content["body"])
                if "base_url" in body["request"].keys():
                    config = eval(models.Config.objects.get(name=body["name"], project__id=project).body)
                    continue
                testcase_list.append(body)
            # [[{scripts}, {scripts}], [{scripts}, {scripts}]]
            testcase.append(testcase_list)

    if back_async:
        loader.async_debug_suite(testcase, project, report, suite, config=config)
        summary = loader.TEST_NOT_EXISTS
        summary["msg"] = "用例运行中，请稍后查看报告"
    else:
        summary = loader.debug_suite(testcase, project, suite, config=config)

    return Response(summary)

@api_view(['POST'])
def run_suitestep(request):
    run_test_path = settings.RUN_TEST_PATH
    timedir = time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())
    projectPath = os.path.join(run_test_path, timedir)
    create_scaffold(projectPath)
    if ('debugtalk' in sys.modules.keys()):
        del sys.modules['debugtalk']
    suitesTree = RunTree(type="suiteTree", relation=request.data['relation'], project=request.data['project'],
                      projectPath=projectPath, config=request.data['config'], isAsync=request.data['async'])
    suitesTree.serializeApi()
    suitesTree.serializeTestCase()
    suitesTree.serializeTestSuite()
    suitesTree.serializeDebugtalk()
    suitesTree.generateMapping()
    #TODO：这里没有实现异步执行，需要修改
    suitesTree.run()
    return Response(suitesTree.summary)

@api_view(['POST'])
def run_suitesinglestep(request):
    run_test_path = settings.RUN_TEST_PATH
    timedir = time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())
    projectPath = os.path.join(run_test_path, timedir)
    create_scaffold(projectPath)
    if ('debugtalk' in sys.modules.keys()):
        del sys.modules['debugtalk']
    debugApi = RunSingleApiInStep(config=request.data['config'], project=request.data['project'],
                                  apiId=request.data['apiId'],
                                  index=request.data['index'], projectPath=projectPath,relation = request.data['relation'][0])
    debugApi.serializeApi()
    debugApi.serializeDebugtalk()
    debugApi.generateMapping()
    debugApi.serializeTestCase()
    debugApi.serializeTestSuite()
    debugApi.run()
    if ('debugtalk' in sys.modules.keys()):
        del sys.modules['debugtalk']
    return Response(debugApi.summary)

@api_view(['POST'])
def run_api_tree(request):
    run_test_path = settings.RUN_TEST_PATH
    timedir = time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())
    projectPath = os.path.join(run_test_path, timedir)
    create_scaffold(projectPath)
    if ('debugtalk' in sys.modules.keys()):
        del sys.modules['debugtalk']
    apiTree = RunTree(type="apiTree", relation=request.data['relation'],project=request.data['project'],
                     projectPath=projectPath,config=request.data['config'],isAsync=request.data['async'])

    apiTree.serializeTestCase()
    apiTree.serializeTestSuite()
    apiTree.serializeDebugtalk()
    apiTree.generateMapping()
    apiTree.run()
    return Response(apiTree.summary)


@api_view(['POST'])
def run_api(request):
    """ run api by body
    """
    api = Format(request.data)
    api.parse()

    run_test_path = settings.RUN_TEST_PATH
    timedir = time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())
    projectPath = os.path.join(run_test_path, timedir)
    if ('debugtalk' in sys.modules.keys()):
        del sys.modules['debugtalk']
    create_scaffold(projectPath)
    debugApi = RunSingleApi(project=api.project,projectPath=projectPath,config=request.data['config'],
                apiBody=api.testcase,type="debugapi")

    debugApi.serializeTestCase()
    debugApi.serializeTestSuite()
    debugApi.serializeDebugtalk()
    debugApi.generateMapping()
    debugApi.run()
    return Response(debugApi.summary)


@api_view(['POST'])
def run_casestep(request):
    run_test_path = settings.RUN_TEST_PATH
    timedir = time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())
    projectPath = os.path.join(run_test_path, timedir)
    create_scaffold(projectPath)
    if ('debugtalk' in sys.modules.keys()):
        del sys.modules['debugtalk']
    suitesTree = RunTree(type="caseTree", relation=request.data['relation'], project=request.data['project'],
                         projectPath=projectPath, config=request.data['config'], isAsync=request.data['async'])
    suitesTree.serializeApi()
    suitesTree.serializeTestCase()
    suitesTree.serializeTestSuite()
    suitesTree.serializeDebugtalk()
    suitesTree.generateMapping()
    # TODO：这里没有实现异步执行，需要修改
    suitesTree.run()
    return Response(suitesTree.summary)

@api_view(['POST'])
def run_casesinglestep(request):
    """run testsuite by tree
    {
        project: int
        relation: list
        name: str
        async: bool
    }
    """
    # order by id default
    run_test_path = settings.RUN_TEST_PATH
    timedir = time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())
    projectPath = os.path.join(run_test_path, timedir)
    create_scaffold(projectPath)
    if ('debugtalk' in sys.modules.keys()):
        del sys.modules['debugtalk']
    singleStep = ''
    if('apiId' in request.data.keys()):
        singleStep = RunSingleApiInCase(config=request.data['config'], project=request.data['project'],
                                    apiId=request.data['apiId'],
                                    index=request.data['index'], projectPath=projectPath,relation = request.data['relation'][0])
    elif('suiteId' in request.data.keys()):
        #TODO:这里的实现只是个临时方案，还要重写的
        singleStep = RunSingleApiInCase(config=request.data['config'], project=request.data['project'],
                                      suiteId=request.data['suiteId'],
                                      index=request.data['index'], projectPath=projectPath,
                                      relation=request.data['relation'][0])
    singleStep.serializeApi()
    singleStep.serializeDebugtalk()
    singleStep.generateMapping()
    singleStep.serializeTestCase()
    singleStep.serializeTestSuite()
    singleStep.run()
    return Response(singleStep.summary)

@api_view(['POST'])
def run_DebugSuiteStep(request):
    """ run suitestep by body
    """
    run_test_path = settings.RUN_TEST_PATH
    timedir = time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())
    projectPath = os.path.join(run_test_path, timedir)
    create_scaffold(projectPath)
    if ('debugtalk' in sys.modules.keys()):
        del sys.modules['debugtalk']
    debugApi = RunSingleApiInStep(config=request.data['config'],project=request.data['project'],apiId=request.data['apiId'],
                                  apiBody=request.data, projectPath=projectPath)
    debugApi.serializeApi()
    debugApi.serializeDebugtalk()
    debugApi.generateMapping()
    debugApi.serializeTestCase()
    debugApi.serializeTestSuite()
    debugApi.run()
    if ('debugtalk' in sys.modules.keys()):
        del sys.modules['debugtalk']
    return Response(debugApi.summary)


@api_view(['POST'])
def run_DebugCaseStep(request):
    """ run casestep by body
    """
    run_test_path = settings.RUN_TEST_PATH
    timedir = time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())
    projectPath = os.path.join(run_test_path, timedir)
    create_scaffold(projectPath)
    if ('debugtalk' in sys.modules.keys()):
        del sys.modules['debugtalk']
    debugApi = RunSingleApiInStep(config=request.data['config'],project=request.data['project'],apiId=request.data['apiId'],
                                  apiBody=request.data, projectPath=projectPath)
    debugApi.serializeApi()
    debugApi.serializeDebugtalk()
    debugApi.generateMapping()
    debugApi.serializeTestCase()
    debugApi.run()
    return Response(debugApi.summary)

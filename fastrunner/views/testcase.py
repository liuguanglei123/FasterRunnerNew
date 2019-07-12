from django.core.exceptions import ObjectDoesNotExist
from rest_framework.viewsets import GenericViewSet
from fastrunner import models, serializers
from rest_framework.response import Response
from fastrunner.utils import response
from fastrunner.utils.parser import Format, Parse,SuiteFormat,SuiteBodyFormat,TestSuiteFormat,testCaseFormat,caseFormat
from django.db import DataError
from django.http import HttpResponse
from httprunner.api import HttpRunner
from django.core.exceptions import ObjectDoesNotExist
from fastrunner.utils.loader import parse_summary
import json,copy
import traceback


class TestCaseTemplateView(GenericViewSet):
    """
    testcase操作视图
    """
    #apiId = serializers.ReadOnlyField(source='API.id')
    serializer_class = serializers.TestCaseSerializer
    queryset = models.TestCase.objects
    """使用默认分页器"""

    def list(self, request):
        """
        接口列表 {
            project: int, 当前选中的项目
            node: int  当前选中的步骤集节点
        }
        """

        returnvalue = {
            'id': '',
            'name': '',
            'maxindex': 0,
            'tests': [],
            'empty': True,
        }
        case = caseFormat(project=request.query_params["project"], relation=request.query_params["node"])
        if (hasattr(case, 'notExist') and case.getNotExist() == True):
            return HttpResponse(json.dumps(returnvalue), content_type='application/json')
        returnvalue['empty'] = False
        returnvalue['id'] = case.getId()
        returnvalue['name'] = case.getName()
        returnvalue['tests'] = case.getAllStep()

        return HttpResponse(json.dumps(returnvalue), content_type='application/json')

    def add(self, request):
        """
        新增一个接口
        """

        case = caseFormat(project=request.data["project"], relation=request.data["relation"])
        case.setName(request.data['name']);
        case.setTests(request.data['tests'])
        return HttpResponse(case.save())

    def update(self, request, **kwargs):
        """
        更新接口
        """
        case = caseFormat(id=kwargs['pk'])
        case.updateTests(name=request.data['name'], tests=request.data['tests'])
        return Response(case.save())

    def delete(self, request, **kwargs):
        #TODO:未实现的内容
        """
        删除一个接口 pk
        删除多个
        [{
            id:int
        }]
        """

        try:
            if kwargs.get('pk'):  # 单个删除
                models.API.objects.get(id=kwargs['pk']).delete()
            else:
                for content in request.data:
                    models.API.objects.get(id=content['id']).delete()

        except ObjectDoesNotExist:
            return Response(response.API_NOT_FOUND)

        return Response(response.API_DEL_SUCCESS)

    def getSingleStep(self, request, **kwargs):
        """
        查询单个api，返回body信息
        """
        case = caseFormat(project=request.query_params["project"], relation=request.query_params["node"])
        case.getSpecStep(request.query_params["index"])
        return Response(case.testcase)

    def updateSingleStep(self, request):
        """
        查询单个api，返回body信息
        """
        case = caseFormat(project=request.data["project"], relation=request.data["relation"])
        case.updateTestStep(int(request.data["srcindex"]), request.data)
        return Response(case.save())


from django.core.exceptions import ObjectDoesNotExist
from rest_framework.viewsets import GenericViewSet
from fastrunner import models, serializers
from rest_framework.response import Response
from fastrunner.utils import response
from fastrunner.utils.parser import Format, Parse,SuiteFormat,SuiteBodyFormat,TestSuiteFormat,suiteFormat
from django.db import DataError
from ..utils.parser import getApiFromSuite
from django.http import HttpResponse
from httprunner.api import HttpRunner
from django.core.exceptions import ObjectDoesNotExist
from fastrunner.utils.loader import parse_summary
import json,copy


class SuiteTemplateView(GenericViewSet):
    """
    SUITE操作视图
    """
    #apiId = serializers.ReadOnlyField(source='API.id')
    serializer_class = serializers.SuiteSerializer
    queryset = models.TestSuite.objects
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
        suite = suiteFormat(project=request.query_params["project"],relation=request.query_params["node"])
        if(hasattr(suite,'notExist') and suite.getNotExist() == True):
            return HttpResponse(json.dumps(returnvalue),content_type='application/json')
        returnvalue['empty'] = False
        returnvalue['id'] = suite.getId()
        returnvalue['name'] = suite.getName()
        returnvalue['tests'] = suite.getAllApi()

        return HttpResponse(json.dumps(returnvalue),content_type='application/json')

    def add(self, request):
        """
        新增一个接口
        """
        suite = suiteFormat(project=request.data["project"],relation=request.data["relation"])
        suite.setName(request.data['name']);
        suite.setTests(request.data['tests'])
        return HttpResponse(suite.save())

    def update(self, request, **kwargs):
        """
        更新接口
        """
        suite = suiteFormat(id=kwargs['pk'])
        suite.updateTests(name = request.data['name'],tests = request.data['tests'])
        return Response(suite.save())

    def delete(self, request, **kwargs):
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
        suite = suiteFormat(project=request.query_params["project"],relation=request.query_params["node"])
        suite.getSpecStep(request.query_params["index"])
        return Response(suite.testcase)

    def updateSingleStep(self, request):
        """
        查询单个api，返回body信息
        """
        suite = suiteFormat(project=request.data["project"],relation=request.data["relation"])
        suite.updateTestStep(int(request.data["srcindex"]),request.data)
        return Response(suite.save())
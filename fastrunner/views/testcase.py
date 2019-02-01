from django.core.exceptions import ObjectDoesNotExist
from rest_framework.viewsets import GenericViewSet
from fastrunner import models, serializers
from rest_framework.response import Response
from fastrunner.utils import response
from fastrunner.utils.parser import Format, Parse,SuiteFormat,SuiteBodyFormat,TestSuiteFormat,testCaseFormat
from django.db import DataError
from ..utils.parser import getApiFromSuite,getApiFromtestCase
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
        testCase = testCaseFormat(relation=request.query_params["node"],project=request.query_params["project"])
        try:
            queryset = self.get_queryset().get(project=request.query_params["project"], relation=request.query_params["node"])
        except ObjectDoesNotExist:
            return HttpResponse(json.dumps(''),content_type='application/json')

        testCase.getList(queryset)

        return HttpResponse(json.dumps(testCase.allStep),content_type='application/json')

    def add(self, request):
        """
        新增一个接口
        """
        case = testCaseFormat(name=request.data['name'],project=request.data['project'],
                              relation=request.data['relation'],optType="add")

        case.addTestCase(request.data['tests'])
        testBody = json.dumps({
            'name': request.data['name'],
            'def': request.data['name'],
            'tests': case.tests
        })
        testCase = {
            'name': request.data['name'],
            'body': testBody,
            'project': models.Project.objects.get(id=request.data['project']),
            'relation': request.data['relation']
        }

        try:
            models.TestCase.objects.create(**testCase)
        except:
            traceback.print_exc()
            return Response(response.DATA_TO_LONG)

        return HttpResponse("success")

    def update(self, request, **kwargs):
        """
        更新接口
        """

        testCase = testCaseFormat(name = request.data['name'],optType="update")
        pk = kwargs['pk']
        try:
            src_data = self.get_queryset().get(id=pk);
        except ObjectDoesNotExist:
            return HttpResponse('error')

        testCase.updateList(src_data,request.data['tests'])

        updateBody={
            'name':request.data['name'],
            'body':testCase.newbody
        }

        try:
            models.TestCase.objects.filter(id=pk).update(**updateBody)
        except ObjectDoesNotExist:
            return Response(response.API_NOT_FOUND)

        return Response(response.API_UPDATE_SUCCESS)

    def delete(self, request, **kwargs):
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

        relation = request.query_params["node"]
        project = request.query_params["project"]
        index = int(request.query_params['index'])
        testCase = testCaseFormat(relation=relation,project=project)
        try:
            queryset = self.get_queryset().get(project=project, relation=relation)
        except ObjectDoesNotExist:
            return Response({'success':False})

        testCase.getList(queryset)
        testCase.getSingleStep(index)
        testCase.parse_http()

        return Response(testCase.testcase)

    def updateSingleStep(self, request):
        """
        查询单个api，返回body信息
        """
        relation = request.data["relation"]
        project = request.data["project"]
        try:
            queryset = self.get_queryset().get(project=project, relation=relation)
        except ObjectDoesNotExist:
            return Response({'success':False})

        testCase = testCaseFormat(relation=relation,project=project)
        testCase.getList(queryset)
        testCase.updateStep(eval(request.data['tests']))

        new_body = json.dumps(testCase.allStep)
        update_body = {'body': new_body}

        try:
            models.TestSuite.objects.filter(project=project, relation=relation).update(**update_body)
        except ObjectDoesNotExist:
            return Response(response.API_NOT_FOUND)

        return Response(response.API_UPDATE_SUCCESS)
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.viewsets import GenericViewSet
from fastrunner import models, serializers
from rest_framework.response import Response
from fastrunner.utils import response
from fastrunner.utils.parser import Format, Parse,SuiteFormat,SuiteBodyFormat,TestSuiteFormat
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

        relation = request.query_params["node"]
        project = request.query_params["project"]
        returnvalue = {
            'id':'',
            'name': '',
            'maxindex': 0,
            'tests': [],
            'empty':True,
        }
        try:
            queryset = self.get_queryset().get(project=project, relation=relation)
        except ObjectDoesNotExist:
            return HttpResponse(json.dumps(returnvalue),content_type='application/json')

        returnvalue['empty'] = False
        returnvalue['id'] = queryset.id
        returnvalue['name'] = queryset.name
        containedApi = getApiFromSuite(queryset)
        #apiQueryset = models.API.objects.filter(project=project,id__in = containedApi)
        index = 0 #index是从1开始计算的，第一个案例的顺序值是1，第二个是2
        for each in containedApi:
            try:
                apiQueryset = models.API.objects.get(project=project,id=each)
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

        return HttpResponse(json.dumps(returnvalue),content_type='application/json')

    def add(self, request):
        """
        新增一个接口
        """

        name = request.data['name']
        project = models.Project.objects.get(id=request.data['project'])
        relation = request.data['relation']
        api = SuiteFormat(request.data['tests'])
        body = json.dumps({
            'name':name,
            'def': name,
            'tests': api.tests
        })
        suite = {
            'name': name,
            'body': body,
            'project': project,
            'relation': relation
        }

        try:
            models.TestSuite.objects.create(**suite)
        except DataError:
            return Response(response.DATA_TO_LONG)

        #return Response(response.API_ADD_SUCCESS)
        return HttpResponse("seccess")

    def update(self, request, **kwargs):
        """
        更新接口
        """
        pk = kwargs['pk']
        try:
            src_data = self.get_queryset().get(id=pk);
        except ObjectDoesNotExist:
            return HttpResponse('error')

        src_body = eval(src_data.body)
        src_tests = copy.deepcopy(src_body['tests'])
        for index,each in enumerate(src_tests):
            each['srcindex'] = index + 1

        new_suite = SuiteFormat(request.data['tests'],optType="update")

        tmp = []
        srcindex = 1
        for each_new in new_suite.tests:
            if(each_new.get('flag','') == 'add'):
                del each_new['srcindex']
                tmp.append(each_new)
                
                continue
            for each_src in src_tests:
                if(each_src.get('srcindex',-1) == each_new.get('srcindex',-2) and each_new['srcindex'] != 0 ):
                    del each_src['srcindex']
                    tmp.append(each_src)
                    break
        tmp_body = {
            'name':request.data['name'],
            'def':request.data['name'],
            'tests':tmp
        }
        tmp_body = json.dumps(tmp_body)
        update_body={
            'name':request.data['name'],
            'body':tmp_body
        }

        try:
            models.TestSuite.objects.filter(id=pk).update(**update_body)
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
        try:
            queryset = self.get_queryset().get(project=project, relation=relation)
        except ObjectDoesNotExist:
            return Response({'success':False})

        suite_body = TestSuiteFormat(queryset.body)
        suite_body.getAPIId(index)
        apiQueryset = models.API.objects.get(project=project, id=suite_body.specAPIid)
        suite_body.init_singleAPIBody(eval(apiQueryset.body))

        suite_body.parse_http()

        return Response(suite_body.testcase)

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

        suite_body = TestSuiteFormat(queryset.body)
        suite_body.updateStep(request.data)

        new_body = json.dumps(suite_body.body)
        update_body = {'body': new_body}

        try:
            models.TestSuite.objects.filter(project=project, relation=relation).update(**update_body)
        except ObjectDoesNotExist:
            return Response(response.API_NOT_FOUND)

        return Response(response.API_UPDATE_SUCCESS)